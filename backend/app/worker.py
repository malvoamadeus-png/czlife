from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import psycopg

from .config import get_settings
from .db import Database
from .domain.models import StoryNode
from .llm.client import ChapterInput, ChapterWriter
from .store import StoryStore

logger = logging.getLogger("czlife.worker")


def _node_from_row(row: dict) -> StoryNode:
    return StoryNode(
        node_id=row["node_id"],
        order=row["order"],
        title=row["title"],
        time_range=row["time_range"],
        location=row["location"],
        research_summary=row["research_summary"],
        source_refs=tuple(row.get("source_refs") or []),
        visible_context=row.get("visible_context") or "",
        chapter_guidance=row.get("chapter_guidance") or "",
        evidence_level=row.get("evidence_level") or "primary-official",
    )


class PlaybackWorker:
    def __init__(self, story_store: StoryStore) -> None:
        self.store = story_store
        self.settings = get_settings()
        self.writer = ChapterWriter(self.settings)
        self._lock_connection = psycopg.connect(self.store.database.url)

    async def run_once(self) -> bool:
        plan = self.store.current_plan()
        if not plan or plan["status"] not in {"PLAN_LOCKED", "GENERATING_CHAPTER", "DECISION_REVEAL"}:
            return False
        database = self.store.database
        if not database.advisory_lock(self._lock_connection, 918273):
            return False
        tree = self.store.tree(plan["plan_id"], plan["version"])
        snapshot = self.store.snapshot()
        playback = snapshot.get("playback") or {}
        if playback.get("state") in {"PAUSED", "COMPLETED"}:
            return False
        next_run_at = playback.get("next_run_at")
        if next_run_at:
            scheduled = datetime.fromisoformat(next_run_at)
            if scheduled > datetime.now(timezone.utc):
                return False
        route_index = int(playback.get("current_route_index") or 0)
        routes = plan.get("routes") or []
        if route_index >= len(routes):
            self.store.update_playback(plan["plan_id"], plan["version"], state="COMPLETED")
            self.store.append_event(
                plan_id=plan["plan_id"], version=plan["version"], event_type="story_completed",
                event_id=f"{plan['plan_id']}:{plan['version']}:completed",
                payload={"ending": plan["ending"]},
            )
            return True
        route = routes[route_index]
        decisions = route.get("decision_results") or []
        if not decisions:
            self.store.update_playback(
                plan["plan_id"], plan["version"], state="COMPLETED", current_route_index=route_index + 1
            )
            return True
        # A successful decision keeps the same life route. Count its already
        # persisted chapters to select the next frozen decision.
        decision_index = sum(
            1 for chapter in snapshot.get("chapters", [])
            if chapter.get("life_number") == route.get("life_number")
        )
        if decision_index >= len(decisions):
            self.store.update_playback(
                plan["plan_id"], plan["version"], state="COMPLETED", current_route_index=route_index + 1,
                current_node_id=None,
            )
            return True
        decision = decisions[min(decision_index, len(decisions) - 1)]
        node_row = next((item for item in tree if item["node_id"] == decision["from_node_id"]), None)
        if not node_row:
            self.store.update_playback(plan["plan_id"], plan["version"], state="PAUSED", last_error="node missing")
            return False
        node = _node_from_row(node_row)
        chapter_id = f"life-{route['life_number']}-{node.node_id}"
        self.store.upsert_chapter(chapter_id, plan["plan_id"], plan["version"], route["life_number"], node.node_id, node.title)
        self.store.update_playback(
            plan["plan_id"], plan["version"], state="GENERATING_CHAPTER",
            current_chapter_id=chapter_id, current_node_id=node.node_id,
            current_life_number=route["life_number"],
        )
        self.store.append_event(
            plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
            event_type="chapter_started", event_id=f"{chapter_id}:started",
            payload={"chapter_id": chapter_id, "node_id": node.node_id, "life_number": route["life_number"], "title": node.title},
        )
        committed = self.store.chapter(chapter_id) or {}
        if committed.get("generation_status") == "completed":
            self.store.append_event(
                plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
                event_type="decision_reveal", payload={"decision": decision},
                event_id=f"decision-reveal-{decision['decision_id']}",
            )
            self.store.update_playback(
                plan["plan_id"], plan["version"], state="GENERATING_CHAPTER",
                current_route_index=route_index + (1 if decision["result"] == "failure" else 0),
                current_node_id=None,
            )
            return True
        chapter_input = ChapterInput(
            chapter_title=node.title,
            node_title=node.title,
            time_range=node.time_range,
            location=node.location,
            research_summary=node.research_summary,
            visible_context=node.visible_context,
            chapter_guidance=node.chapter_guidance,
            life_number=route["life_number"],
            inherited_memories=tuple(route.get("inherited_memories") or []),
            committed_text=committed.get("content", ""),
        )
        buffer = ""
        try:
            async for delta in self.writer.stream_chapter(chapter_input):
                buffer += delta
                if len(buffer) >= 80:
                    await self._commit_delta(plan, chapter_id, buffer)
                    buffer = ""
            if buffer:
                await self._commit_delta(plan, chapter_id, buffer)
            self.store.complete_chapter(chapter_id)
            self.store.append_event(
                plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
                event_type="chapter_completed", event_id=f"{chapter_id}:completed", payload={"chapter_id": chapter_id},
            )
            self.store.append_event(
                plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
                event_type="decision_reveal", event_id=f"decision-reveal-{decision['decision_id']}", payload={"decision": decision},
            )
            if decision["result"] == "failure":
                self.store.append_event(
                    plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
                    event_type="death", event_id=f"{chapter_id}:death", payload={"life_number": route["life_number"], "reason": route.get("death_reason"), "memory": route.get("gained_memory")},
                )
                self.store.append_event(
                    plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
                    event_type="rebirth", event_id=f"{chapter_id}:rebirth", payload={"next_life": route["life_number"] + 1},
                )
            self.store.update_playback(
                plan["plan_id"], plan["version"], state="GENERATING_CHAPTER",
                current_route_index=route_index + (1 if decision["result"] == "failure" else 0),
                current_node_id=None,
                next_run_at=datetime.now(timezone.utc) + timedelta(seconds=self.settings.playback_interval_seconds),
            )
            return True
        except Exception as exc:
            logger.exception("chapter generation failed")
            self.store.update_playback(plan["plan_id"], plan["version"], state="PAUSED", last_error=str(exc)[:800])
            self.store.append_event(
                plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id,
                event_type="playback_paused", payload={"reason": str(exc)[:800]},
            )
            return False

    async def _commit_delta(self, plan: dict, chapter_id: str, text: str) -> None:
        self.store.append_chapter_delta(
            plan_id=plan["plan_id"], version=plan["version"], chapter_id=chapter_id, text=text
        )

    async def run_forever(self) -> None:
        while True:
            did_work = await self.run_once()
            await asyncio.sleep(self.settings.playback_interval_seconds if did_work else 3)


async def main() -> None:
    settings = get_settings()
    store = StoryStore(Database(settings))
    store.init()
    worker = PlaybackWorker(store)
    available = await worker.writer.selector.verify()
    logger.info("configured GPT models available: %s", ", ".join(available))
    await worker.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
