from __future__ import annotations

import hashlib
import json

from .models import StoryNode, StoryPlan


class PlanValidationError(ValueError):
    pass


def validate_plan(plan: StoryPlan, nodes: list[StoryNode]) -> str:
    node_ids = [node.node_id for node in sorted(nodes, key=lambda item: item.order)]
    if tuple(node_ids) != plan.mainline_node_ids:
        raise PlanValidationError("Mainline node order does not match the plan")
    if len(set(node_ids)) != len(node_ids):
        raise PlanValidationError("Mainline node IDs must be unique")
    if len(plan.routes) > plan.max_lives:
        raise PlanValidationError("Route exceeds max_lives")
    if plan.routes[-1].route_status != "completed":
        raise PlanValidationError("Final route must be completed")
    if sum(route.route_status == "dead" for route in plan.routes) < 2:
        raise PlanValidationError("MVP route must contain at least two dead lives")

    for route in plan.routes:
        seen_nodes: list[str] = []
        for decision in route.decision_results:
            if decision.from_node_id in seen_nodes:
                raise PlanValidationError("A route cannot decide from the same node twice")
            seen_nodes.append(decision.from_node_id)
            if decision.result == "failure":
                if not route.gained_memory or not route.death_reason:
                    raise PlanValidationError("A failed life needs death reason and memory")
                break

    canonical = {
        "plan_id": plan.plan_id,
        "version": plan.version,
        "seed": plan.seed,
        "rules_version": plan.rules_version,
        "nodes": list(plan.mainline_node_ids),
        "routes": [
            {
                "life": route.life_number,
                "status": route.route_status,
                "decisions": [
                    {
                        "id": decision.decision_id,
                        "roll": decision.roll_value,
                        "threshold": decision.threshold,
                        "result": decision.result,
                    }
                    for decision in route.decision_results
                ],
            }
            for route in plan.routes
        ],
    }
    return hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

