from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .config import Settings, get_settings
from .db import Database
from .domain.validator import PlanValidationError, validate_plan
from .seed import build_demo_plan, demo_nodes, demo_rules
from .store import StoryStore


settings = get_settings()
database = Database(settings) if settings.database_url else None
store = StoryStore(database) if database else None


@asynccontextmanager
async def lifespan(_: FastAPI):
    if store:
        store.init()
    yield


app = FastAPI(
    title="CZ Life Story API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.public_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Last-Event-ID", "X-Operator-Token"],
)


def get_store() -> StoryStore:
    if store is None:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return store


def require_operator(x_operator_token: str | None = Header(default=None)) -> None:
    if not settings.operator_token or x_operator_token != settings.operator_token:
        raise HTTPException(status_code=401, detail="operator token required")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "czlife-api"}


@app.get("/v1/story/snapshot")
def story_snapshot(story_store: StoryStore = Depends(get_store)) -> dict:
    return story_store.snapshot()


@app.get("/v1/story/tree")
def story_tree(story_store: StoryStore = Depends(get_store)) -> dict:
    plan = story_store.current_plan()
    if not plan:
        return {"plan": None, "nodes": []}
    return {
        "plan_id": plan["plan_id"],
        "version": plan["version"],
        "nodes": story_store.tree(plan["plan_id"], plan["version"]),
    }


@app.get("/v1/story/chapters")
def story_chapters(story_store: StoryStore = Depends(get_store)) -> dict:
    snapshot = story_store.snapshot()
    return {"chapters": snapshot["chapters"], "latest_sequence": snapshot["latest_sequence"]}


@app.get("/v1/story/chapters/{chapter_id}")
def story_chapter(chapter_id: str, story_store: StoryStore = Depends(get_store)) -> dict:
    chapter = story_store.chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="chapter not found")
    return chapter


def _sse_event(event: dict) -> str:
    return (
        f"id: {event['sequence']}\n"
        f"event: {event['event_type']}\n"
        f"data: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )


async def _event_stream(
    story_store: StoryStore,
    after: int,
    request: Request,
) -> AsyncIterator[str]:
    plan = story_store.current_plan()
    if not plan:
        yield ": no story plan\n\n"
        return
    plan_id = plan["plan_id"]
    version = plan["version"]
    cursor = max(0, after)
    heartbeat_at = asyncio.get_running_loop().time()
    while not await request.is_disconnected():
        events = story_store.events_after(plan_id, version, cursor, limit=100)
        if events:
            for event in events:
                cursor = max(cursor, int(event["sequence"]))
                yield _sse_event(event)
            continue
        now = asyncio.get_running_loop().time()
        if now - heartbeat_at >= 15:
            heartbeat_at = now
            yield ": heartbeat\n\n"
        await asyncio.sleep(0.75)


@app.get("/v1/story/stream")
async def story_stream(
    request: Request,
    after: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    story_store: StoryStore = Depends(get_store),
) -> StreamingResponse:
    cursor = after
    if last_event_id and last_event_id.isdigit():
        cursor = max(cursor, int(last_event_id))
    return StreamingResponse(
        _event_stream(story_store, cursor, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/internal/plan/seed", dependencies=[Depends(require_operator)])
def seed_plan(story_store: StoryStore = Depends(get_store)) -> dict:
    plan = build_demo_plan()
    try:
        plan_hash = validate_plan(plan, demo_nodes())
    except PlanValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    story_store.save_plan(plan, demo_nodes(), demo_rules(), plan_hash)
    return {"plan_id": plan.plan_id, "version": plan.version, "plan_hash": plan_hash, "status": plan.status}


@app.post("/internal/plan/lock", dependencies=[Depends(require_operator)])
def lock_plan(story_store: StoryStore = Depends(get_store)) -> dict:
    plan = build_demo_plan()
    plan_hash = validate_plan(plan, demo_nodes())
    story_store.lock_plan(plan.plan_id, plan.version, plan_hash)
    return {"status": "PLAN_LOCKED", "plan_hash": plan_hash}


@app.post("/internal/playback/{action}", dependencies=[Depends(require_operator)])
def playback_action(action: str, story_store: StoryStore = Depends(get_store)) -> dict:
    if action not in {"start", "pause", "resume"}:
        raise HTTPException(status_code=400, detail="action must be start, pause or resume")
    plan = story_store.current_plan()
    if not plan:
        raise HTTPException(status_code=404, detail="no story plan")
    state = "GENERATING_CHAPTER" if action in {"start", "resume"} else "PAUSED"
    story_store.update_playback(plan["plan_id"], plan["version"], state=state, last_error=None)
    return {"state": state}


@app.get("/internal/status", dependencies=[Depends(require_operator)])
def internal_status(story_store: StoryStore = Depends(get_store)) -> dict:
    return story_store.snapshot()

