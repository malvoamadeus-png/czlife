from __future__ import annotations

import hashlib
import random
from typing import Any

from .models import DecisionResult, DecisionRule, LifeRoute, StoryNode, StoryPlan


def _decision_id(plan_id: str, version: int, life: int, node_id: str) -> str:
    value = f"{plan_id}:{version}:{life}:{node_id}"
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def build_route_plan(
    *,
    plan_id: str,
    version: int,
    title: str,
    ticker: str,
    nodes: list[StoryNode],
    rules: list[DecisionRule],
    seed: int,
    max_lives: int,
    initial_traits: dict[str, Any] | None = None,
    initial_background: dict[str, Any] | None = None,
) -> StoryPlan:
    """Calculate every life once. This function has no I/O and is deterministic."""
    if not nodes:
        raise ValueError("At least one story node is required")
    ordered_nodes = sorted(nodes, key=lambda item: item.order)
    rules_by_from = {rule.from_node_id: rule for rule in rules}
    rng = random.Random(seed)
    memories: list[dict[str, Any]] = []
    routes: list[LifeRoute] = []
    first_traits = initial_traits or {"curiosity": 60, "risk": 55, "focus": 60}
    first_background = initial_background or {"capital": 35, "network": 20, "technical": 70}

    for life_number in range(1, max_lives + 1):
        decisions: list[DecisionResult] = []
        current_memories = tuple(memories)
        modifiers = sum(int(memory.get("bonus", 0)) for memory in current_memories)
        failed_node: str | None = None
        death_reason: str | None = None
        gained_memory: dict[str, Any] | None = None
        route_status = "completed"

        for index, node in enumerate(ordered_nodes[:-1]):
            rule = rules_by_from.get(node.node_id)
            if rule is None:
                raise ValueError(f"Missing decision rule for {node.node_id}")
            roll = rng.randint(1, 100)
            threshold = min(99, max(1, rule.success_threshold + modifiers))
            passed = roll <= threshold
            result = "success" if passed else "failure"
            decision = DecisionResult(
                decision_id=_decision_id(plan_id, version, life_number, node.node_id),
                life_number=life_number,
                from_node_id=node.node_id,
                to_node_id=rule.to_node_id,
                roll_value=roll,
                threshold=threshold,
                result=result,
                input_snapshot={
                    "traits": dict(first_traits),
                    "background": dict(first_background),
                    "memories": list(current_memories),
                    "memory_bonus": modifiers,
                    "node_index": index,
                },
            )
            decisions.append(decision)
            if not passed:
                route_status = "dead"
                failed_node = node.node_id
                death_reason = f"在“{node.title}”之后错过了进入下一节点的机会。"
                gained_memory = {
                    "memory_id": f"memory-{life_number}-{node.node_id}",
                    "title": f"第{life_number}世的教训",
                    "effect": rule.memory_effect,
                    "bonus": rule.memory_effect,
                    "source_node_id": node.node_id,
                }
                memories.append(gained_memory)
                break

        routes.append(
            LifeRoute(
                life_number=life_number,
                initial_traits=dict(first_traits),
                initial_background=dict(first_background),
                inherited_memories=current_memories,
                decision_results=tuple(decisions),
                failure_node_id=failed_node,
                death_reason=death_reason,
                gained_memory=gained_memory,
                route_status=route_status,  # type: ignore[arg-type]
            )
        )
        if route_status == "completed":
            break

    if routes[-1].route_status != "completed":
        raise ValueError("Route did not reach a completed life within max_lives")

    return StoryPlan(
        plan_id=plan_id,
        version=version,
        title=title,
        ticker=ticker,
        status="PLANNING",
        seed=seed,
        rules_version="route-v1",
        mainline_node_ids=tuple(node.node_id for node in ordered_nodes),
        max_lives=max_lives,
        ending={"type": "fictional", "title": "首富结局", "visible": True},
        routes=tuple(routes),
    )

