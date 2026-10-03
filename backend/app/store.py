from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable

from psycopg.types.json import Jsonb

from .db import Database
from .domain.models import DecisionRule, StoryNode, StoryPlan, node_to_json


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoryStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def init(self) -> None:
        self.database.migrate()

    def save_plan(
        self,
        plan: StoryPlan,
        nodes: Iterable[StoryNode],
        rules: Iterable[DecisionRule],
        plan_hash: str,
    ) -> None:
        node_list = list(nodes)
        rule_list = list(rules)
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO story_plans
                    (plan_id, version, title, ticker, status, seed, rules_version,
                     plan_hash, mainline_node_ids, max_lives, ending, routes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (plan_id, version) DO UPDATE SET
                    status = EXCLUDED.status,
                    plan_hash = EXCLUDED.plan_hash,
                    routes = EXCLUDED.routes
                """,
                (
                    plan.plan_id,
                    plan.version,
                    plan.title,
                    plan.ticker,
                    plan.status,
                    plan.seed,
                    plan.rules_version,
                    plan_hash,
                    Jsonb(list(plan.mainline_node_ids)),
                    plan.max_lives,
                    Jsonb(plan.ending),
                    Jsonb([route_to_json(route) for route in plan.routes]),
                ),
            )
            for node in node_list:
                connection.execute(
                    """
                    INSERT INTO story_nodes
                        (plan_id, plan_version, node_id, node_order, title, time_range,
                         location, research_summary, source_refs, visible_context,
                         chapter_guidance, evidence_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (plan_id, plan_version, node_id) DO UPDATE SET
                        title = EXCLUDED.title, research_summary = EXCLUDED.research_summary,
                        source_refs = EXCLUDED.source_refs, evidence_level = EXCLUDED.evidence_level
                    """,
                    (
                        plan.plan_id,
                        plan.version,
                        node.node_id,
                        node.order,
                        node.title,
                        node.time_range,
                        node.location,
                        node.research_summary,
                        Jsonb(list(node.source_refs)),
                        node.visible_context,
                        node.chapter_guidance,
                        node.evidence_level,
                    ),
                )
            for rule in rule_list:
                connection.execute(
                    """
                    INSERT INTO decision_rules
                        (plan_id, plan_version, rule_id, from_node_id, to_node_id,
                         success_threshold, memory_effect, fallback_rule)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (plan_id, plan_version, rule_id) DO UPDATE SET
                        success_threshold = EXCLUDED.success_threshold,
                        memory_effect = EXCLUDED.memory_effect
                    """,
                    (
                        plan.plan_id,
                        plan.version,
                        rule.rule_id,
                        rule.from_node_id,
                        rule.to_node_id,
                        rule.success_threshold,
                        rule.memory_effect,
                        rule.fallback_rule,
                    ),
                )
            for route in plan.routes:
                connection.execute(
                    """
                    INSERT INTO life_routes
                        (plan_id, plan_version, life_number, route_status, failure_node_id,
                         death_reason, gained_memory, inherited_memories, decision_results)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (plan_id, plan_version, life_number) DO UPDATE SET
                        route_status = EXCLUDED.route_status,
                        failure_node_id = EXCLUDED.failure_node_id,
                        death_reason = EXCLUDED.death_reason,
                        gained_memory = EXCLUDED.gained_memory,
                        inherited_memories = EXCLUDED.inherited_memories,
                        decision_results = EXCLUDED.decision_results
                    """,
                    (
                        plan.plan_id,
                        plan.version,
                        route.life_number,
                        route.route_status,
                        route.failure_node_id,
                        route.death_reason,
                        Jsonb(route.gained_memory) if route.gained_memory else None,
                        Jsonb(list(route.inherited_memories)),
                        Jsonb([decision_to_json(item) for item in route.decision_results]),
                    ),
                )
                for decision in route.decision_results:
                    connection.execute(
                        """
                        INSERT INTO decision_results
                            (decision_id, plan_id, plan_version, life_number,
                             from_node_id, to_node_id, input_snapshot, rules_version,
                             roll_value, threshold, result)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (decision_id) DO NOTHING
                        """,
                        (
                            decision.decision_id,
                            plan.plan_id,
                            plan.version,
                            decision.life_number,
                            decision.from_node_id,
                            decision.to_node_id,
                            Jsonb(decision.input_snapshot),
                            plan.rules_version,
                            decision.roll_value,
                            decision.threshold,
                            decision.result,
                        ),
                    )
            connection.execute(
                """
                INSERT INTO playback_state
                    (plan_id, plan_version, state, current_route_index, current_life_number)
                VALUES (%s, %s, %s, 0, 1)
                ON CONFLICT (plan_id, plan_version) DO NOTHING
                """,
                (plan.plan_id, plan.version, plan.status),
            )

    def lock_plan(self, plan_id: str, version: int, plan_hash: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE story_plans SET status = 'PLAN_LOCKED', plan_hash = %s, locked_at = now() WHERE plan_id = %s AND version = %s",
                (plan_hash, plan_id, version),
            )
            connection.execute(
                "UPDATE playback_state SET state = 'PLAN_LOCKED', updated_at = now() WHERE plan_id = %s AND plan_version = %s",
                (plan_id, version),
            )

    def current_plan(self) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT plan_id, version, title, ticker, status, seed, rules_version,
                       plan_hash, mainline_node_ids, max_lives, ending, routes
                FROM story_plans
                WHERE status <> 'COMPLETED'
                ORDER BY version DESC, created_at DESC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                row = connection.execute(
                    """
                    SELECT plan_id, version, title, ticker, status, seed, rules_version,
                           plan_hash, mainline_node_ids, max_lives, ending, routes
                    FROM story_plans ORDER BY version DESC, created_at DESC LIMIT 1
                    """
                ).fetchone()
            if not row:
                return None
            keys = [
                "plan_id", "version", "title", "ticker", "status", "seed",
                "rules_version", "plan_hash", "mainline_node_ids", "max_lives",
                "ending", "routes",
            ]
            return dict(zip(keys, row))

    def tree(self, plan_id: str, version: int) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT node_id, node_order, title, time_range, location,
                       research_summary, source_refs, visible_context,
                       chapter_guidance, evidence_level
                FROM story_nodes WHERE plan_id = %s AND plan_version = %s
                ORDER BY node_order
                """,
                (plan_id, version),
            ).fetchall()
            routes = connection.execute(
                """
                SELECT life_number, route_status, failure_node_id, death_reason, gained_memory
                FROM life_routes WHERE plan_id = %s AND plan_version = %s ORDER BY life_number
                """,
                (plan_id, version),
            ).fetchall()
        failures = [
            {
                "life_number": row[0],
                "status": row[1],
                "failure_node_id": row[2],
                "death_reason": row[3],
                "gained_memory": row[4],
            }
            for row in routes
            if row[2]
        ]
        result: list[dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "node_id": row[0],
                    "order": row[1],
                    "title": row[2],
                    "time_range": row[3],
                    "location": row[4],
                    "research_summary": row[5],
                    "source_refs": row[6],
                    "visible_context": row[7],
                    "chapter_guidance": row[8],
                    "evidence_level": row[9],
                    "failure_routes": [item for item in failures if item["failure_node_id"] == row[0]],
                }
            )
        return result

    def snapshot(self) -> dict[str, Any]:
        plan = self.current_plan()
        if not plan:
            return {"plan": None, "playback": None, "chapters": [], "latest_sequence": 0}
        with self.database.connection() as connection:
            playback = connection.execute(
                """
                SELECT state, current_route_index, current_chapter_id, current_node_id,
                       current_life_number, latest_sequence, next_run_at, last_error
                FROM playback_state WHERE plan_id = %s AND plan_version = %s
                """,
                (plan["plan_id"], plan["version"]),
            ).fetchone()
            chapters = connection.execute(
                """
                SELECT chapter_id, life_number, node_id, chapter_index, chapter_title,
                       generation_status, content, committed_offset, completed_at
                FROM chapters WHERE plan_id = %s AND plan_version = %s
                ORDER BY life_number, chapter_index
                """,
                (plan["plan_id"], plan["version"]),
            ).fetchall()
            latest = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM stream_events WHERE plan_id = %s AND plan_version = %s",
                (plan["plan_id"], plan["version"]),
            ).fetchone()[0]
        playback_payload = None
        if playback:
            playback_payload = {
                "state": playback[0],
                "current_route_index": playback[1],
                "current_chapter_id": playback[2],
                "current_node_id": playback[3],
                "current_life_number": playback[4],
                "latest_sequence": latest,
                "next_run_at": playback[6].isoformat() if playback[6] else None,
                "last_error": playback[7],
            }
        return {
            "plan": {
                "plan_id": plan["plan_id"],
                "version": plan["version"],
                "title": plan["title"],
                "ticker": plan["ticker"],
                "status": plan["status"],
                "seed": plan["seed"],
                "rules_version": plan["rules_version"],
                "plan_hash": plan["plan_hash"],
                "mainline_node_ids": plan["mainline_node_ids"],
                "ending": plan["ending"],
            },
            "playback": playback_payload,
            "chapters": [
                {
                    "chapter_id": row[0],
                    "life_number": row[1],
                    "node_id": row[2],
                    "chapter_index": row[3],
                    "chapter_title": row[4],
                    "generation_status": row[5],
                    "content": row[6],
                    "committed_offset": row[7],
                    "completed_at": row[8].isoformat() if row[8] else None,
                }
                for row in chapters
            ],
            "latest_sequence": latest,
        }

    def chapter(self, chapter_id: str) -> dict[str, Any] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT chapter_id, life_number, node_id, chapter_index, chapter_title,
                       generation_status, content, committed_offset, completed_at
                FROM chapters WHERE chapter_id = %s
                """,
                (chapter_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "chapter_id": row[0],
            "life_number": row[1],
            "node_id": row[2],
            "chapter_index": row[3],
            "chapter_title": row[4],
            "generation_status": row[5],
            "content": row[6],
            "committed_offset": row[7],
            "completed_at": row[8].isoformat() if row[8] else None,
        }

    def events_after(self, plan_id: str, version: int, after: int, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT event_id, sequence, chapter_id, event_type, payload, created_at
                FROM stream_events
                WHERE plan_id = %s AND plan_version = %s AND sequence > %s
                ORDER BY sequence LIMIT %s
                """,
                (plan_id, version, after, limit),
            ).fetchall()
        return [
            {
                "event_id": row[0],
                "plan_version": version,
                "sequence": row[1],
                "chapter_id": row[2],
                "event_type": row[3],
                "payload": row[4],
                "created_at": row[5].isoformat(),
            }
            for row in rows
        ]

    def append_event(
        self,
        *,
        plan_id: str,
        version: int,
        event_type: str,
        payload: dict[str, Any],
        chapter_id: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = event_id or str(uuid.uuid4())
        with self.database.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO stream_events (event_id, plan_id, plan_version, chapter_id, event_type, payload)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                RETURNING sequence, created_at
                """,
                (event_id, plan_id, version, chapter_id, event_type, Jsonb(payload)),
            ).fetchone()
            if row is None:
                existing = connection.execute(
                    "SELECT sequence, created_at, payload, event_type, chapter_id FROM stream_events WHERE event_id = %s",
                    (event_id,),
                ).fetchone()
                return {
                    "event_id": event_id,
                    "plan_version": version,
                    "sequence": existing[0],
                    "chapter_id": existing[4],
                    "event_type": existing[3],
                    "payload": existing[2],
                    "created_at": existing[1].isoformat(),
                }
            sequence, created_at = row
            connection.execute(
                "UPDATE playback_state SET latest_sequence = %s, updated_at = now() WHERE plan_id = %s AND plan_version = %s",
                (sequence, plan_id, version),
            )
            connection.execute("SELECT pg_notify('czlife_events', %s)", (f"{plan_id}:{version}:{sequence}",))
        return {
            "event_id": event_id,
            "plan_version": version,
            "sequence": sequence,
            "chapter_id": chapter_id,
            "event_type": event_type,
            "payload": payload,
            "created_at": created_at.isoformat(),
        }

    def upsert_chapter(self, chapter_id: str, plan_id: str, version: int, life: int, node_id: str, title: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO chapters (chapter_id, plan_id, plan_version, life_number, node_id, chapter_index, chapter_title, generation_status)
                VALUES (%s, %s, %s, %s, %s, 1, %s, 'generating')
                ON CONFLICT (chapter_id) DO NOTHING
                """,
                (chapter_id, plan_id, version, life, node_id, title),
            )

    def append_chapter_text(self, chapter_id: str, text: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE chapters SET content = content || %s, committed_offset = committed_offset + %s, generation_status = 'generating' WHERE chapter_id = %s",
                (text, len(text), chapter_id),
            )

    def append_chapter_delta(
        self,
        *,
        plan_id: str,
        version: int,
        chapter_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Persist a text offset and its event atomically for crash recovery."""
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT committed_offset FROM chapters WHERE chapter_id = %s FOR UPDATE",
                (chapter_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"chapter {chapter_id} does not exist")
            next_offset = int(row[0]) + len(text)
            event_id = f"{chapter_id}:text:{next_offset}"
            connection.execute(
                "UPDATE chapters SET content = content || %s, committed_offset = %s, generation_status = 'generating' WHERE chapter_id = %s",
                (text, next_offset, chapter_id),
            )
            event_row = connection.execute(
                """
                INSERT INTO stream_events (event_id, plan_id, plan_version, chapter_id, event_type, payload)
                VALUES (%s, %s, %s, %s, 'text_delta', %s)
                ON CONFLICT (event_id) DO UPDATE SET event_id = stream_events.event_id
                RETURNING sequence, created_at
                """,
                (event_id, plan_id, version, chapter_id, Jsonb({"chapter_id": chapter_id, "text": text, "offset": next_offset})),
            ).fetchone()
            sequence, created_at = event_row
            connection.execute(
                "UPDATE playback_state SET latest_sequence = %s, updated_at = now() WHERE plan_id = %s AND plan_version = %s",
                (sequence, plan_id, version),
            )
            connection.execute("SELECT pg_notify('czlife_events', %s)", (f"{plan_id}:{version}:{sequence}",))
        return {
            "event_id": event_id,
            "plan_version": version,
            "sequence": sequence,
            "chapter_id": chapter_id,
            "event_type": "text_delta",
            "payload": {"chapter_id": chapter_id, "text": text, "offset": next_offset},
            "created_at": created_at.isoformat(),
        }

    def complete_chapter(self, chapter_id: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE chapters SET generation_status = 'completed', completed_at = now() WHERE chapter_id = %s",
                (chapter_id,),
            )

    def update_playback(self, plan_id: str, version: int, **values: Any) -> None:
        allowed = {
            "state", "current_route_index", "current_chapter_id", "current_node_id",
            "current_life_number", "next_run_at", "last_error",
        }
        values = {key: value for key, value in values.items() if key in allowed}
        if not values:
            return
        columns = ", ".join(f"{key} = %({key})s" for key in values)
        params = {**values, "plan_id": plan_id, "plan_version": version}
        with self.database.connection() as connection:
            connection.execute(
                f"UPDATE playback_state SET {columns}, updated_at = now() WHERE plan_id = %(plan_id)s AND plan_version = %(plan_version)s",
                params,
            )


def decision_to_json(decision: Any) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "life_number": decision.life_number,
        "from_node_id": decision.from_node_id,
        "to_node_id": decision.to_node_id,
        "roll_value": decision.roll_value,
        "threshold": decision.threshold,
        "result": decision.result,
        "input_snapshot": decision.input_snapshot,
    }


def route_to_json(route: Any) -> dict[str, Any]:
    return {
        "life_number": route.life_number,
        "initial_traits": route.initial_traits,
        "initial_background": route.initial_background,
        "inherited_memories": list(route.inherited_memories),
        "decision_results": [decision_to_json(item) for item in route.decision_results],
        "failure_node_id": route.failure_node_id,
        "death_reason": route.death_reason,
        "gained_memory": route.gained_memory,
        "route_status": route.route_status,
    }
