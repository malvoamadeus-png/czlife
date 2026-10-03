from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


RouteStatus = Literal["dead", "completed"]
PlanStatus = Literal[
    "RESEARCH_READY",
    "PLANNING",
    "VALIDATING",
    "PLAN_LOCKED",
    "GENERATING_CHAPTER",
    "DECISION_REVEAL",
    "PAUSED",
    "COMPLETED",
]


@dataclass(frozen=True, slots=True)
class StoryNode:
    node_id: str
    order: int
    title: str
    time_range: str
    location: str
    research_summary: str
    source_refs: tuple[str, ...] = ()
    visible_context: str = ""
    chapter_guidance: str = ""
    evidence_level: str = "primary-official"


@dataclass(frozen=True, slots=True)
class DecisionRule:
    rule_id: str
    from_node_id: str
    to_node_id: str
    success_threshold: int
    memory_effect: int = 0
    fallback_rule: str = "death"


@dataclass(frozen=True, slots=True)
class DecisionResult:
    decision_id: str
    life_number: int
    from_node_id: str
    to_node_id: str
    roll_value: int
    threshold: int
    result: Literal["success", "failure"]
    input_snapshot: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LifeRoute:
    life_number: int
    initial_traits: dict[str, Any]
    initial_background: dict[str, Any]
    inherited_memories: tuple[dict[str, Any], ...]
    decision_results: tuple[DecisionResult, ...]
    failure_node_id: str | None
    death_reason: str | None
    gained_memory: dict[str, Any] | None
    route_status: RouteStatus


@dataclass(frozen=True, slots=True)
class StoryPlan:
    plan_id: str
    version: int
    title: str
    ticker: str
    status: PlanStatus
    seed: int
    rules_version: str
    mainline_node_ids: tuple[str, ...]
    max_lives: int
    ending: dict[str, Any]
    routes: tuple[LifeRoute, ...] = field(default_factory=tuple)


def node_to_json(node: StoryNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "order": node.order,
        "title": node.title,
        "time_range": node.time_range,
        "location": node.location,
        "research_summary": node.research_summary,
        "source_refs": list(node.source_refs),
        "visible_context": node.visible_context,
        "chapter_guidance": node.chapter_guidance,
        "evidence_level": node.evidence_level,
    }

