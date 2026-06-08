"""
NecroSwarm Router Adapter for K2-Backbone — Single Source of Truth via model-routing-table

Maps TaskSpec subtasks to council members via weighted voting.
Core logic: Borda voting with cost-aware fallback.

Updated 2026-06-08: model definitions imported from model-routing-table.
All model changes go in model_routing_table/table.py — this file reads from there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from model_routing_table import (
    DIMENSION_MAP,
    DIMENSION_FALLBACK,
    DIMENSION_DESCRIPTIONS,
)
from model_routing_table.table import (
    MODEL_COST_USD,
    CAPABILITY_MATRIX,
    SUBTASK_TYPE_TO_SPECIALIZATION,
)


# ── Data classes ──────────────────────────────────────────────────────

class VoteMethod(str, Enum):
    BORDA = "borda"
    WEIGHTED = "weighted"
    COST_FIRST = "cost_first"
    QUALITY_FIRST = "quality_first"


@dataclass
class CouncilMember:
    id: str
    name: str
    model: str
    tier: str
    vote_power: int
    weight: float
    specialties: list[str] = field(default_factory=list)


@dataclass
class RoutingDecision:
    subtask_id: str
    assigned_model: str
    council_vote: dict
    estimated_cost_usd: float
    confidence: float
    strategy: str
    reasoning: str

    def to_dict(self) -> dict:
        return {
            "subtask_id": self.subtask_id,
            "assigned_model": self.assigned_model,
            "council_vote": self.council_vote,
            "estimated_cost_usd": self.estimated_cost_usd,
            "confidence": self.confidence,
            "strategy": self.strategy,
            "reasoning": self.reasoning,
        }


# ── Core router ───────────────────────────────────────────────────────

class NecroSwarmRouter:
    """
    Routes TaskSpec subtasks to council members using configurable voting strategies.
    """

    def __init__(
        self,
        vote_method: VoteMethod = VoteMethod.BORDA,
        cost_budget_usd: Optional[float] = None,
    ):
        self.vote_method = vote_method
        self.cost_budget = cost_budget_usd
        self.members = self._load_members()

    def _load_members(self) -> list[CouncilMember]:
        """Build council members from the model routing table."""
        members = []
        for dim, model_id in DIMENSION_MAP.items():
            desc = DIMENSION_DESCRIPTIONS.get(dim, "")
            tier = "T1"
            vote_power = 2
            weight = 0.8
            if dim in ("D1_synthesis", "D10_think"):
                tier = "T0"
                vote_power = 3
                weight = 1.0
            elif dim == "D7_general":
                tier = "T2"
                vote_power = 1
                weight = 0.6
            members.append(CouncilMember(
                id=model_id,
                name=model_id.split(":")[0],
                model=model_id,
                tier=tier,
                vote_power=vote_power,
                weight=weight,
                specialties=[desc],
            ))
        return members

    def _get_candidates(self, subtask_type: str) -> list[str]:
        candidates = SUBTASK_TYPE_TO_SPECIALIZATION.get(subtask_type, [])
        if not candidates:
            candidates = list(DIMENSION_MAP.values())
        return candidates

    def _score_borda(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        scores = {}
        subtask_type = subtask.get("type", "analysis")
        task_family = subtask_type.split("_")[0]

        ranked = []
        for cid in candidates:
            cap = CAPABILITY_MATRIX.get(cid, {})
            capability = cap.get(task_family, cap.get("analysis", 5))
            cost = MODEL_COST_USD.get(cid, 1.0)
            member = next((m for m in self.members if m.id == cid), None)
            vote_power = member.vote_power if member else 1
            tier_weight = member.weight if member else 0.5
            cost_score = 1.0 / (cost + 0.01)
            composite = (capability * tier_weight * cost_score) / (vote_power ** 0.5)
            ranked.append((cid, composite))

        ranked.sort(key=lambda x: x[1], reverse=True)
        n = len(ranked)
        for i, (cid, _) in enumerate(ranked):
            scores[cid] = n - i
        return scores

    def _score_cost_first(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        estimated_tokens = subtask.get("estimated_tokens", 4096)
        scores = {}
        for cid in candidates:
            cost_1k = MODEL_COST_USD.get(cid, 1.0)
            scores[cid] = 1.0 / ((estimated_tokens / 1000) * cost_1k + 0.001)
        return scores

    def _score_quality_first(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        subtask_type = subtask.get("type", "analysis")
        task_family = subtask_type.split("_")[0]
        scores = {}
        for cid in candidates:
            cap = CAPABILITY_MATRIX.get(cid, {})
            scores[cid] = cap.get(task_family, cap.get("analysis", 5))
        return scores

    def _vote(self, subtask: dict) -> tuple[str, dict, float, str]:
        candidates = self._get_candidates(subtask.get("type", "analysis"))

        if self.vote_method == VoteMethod.COST_FIRST:
            scores = self._score_cost_first(subtask, candidates)
            strategy = "cost_first"
        elif self.vote_method == VoteMethod.QUALITY_FIRST:
            scores = self._score_quality_first(subtask, candidates)
            strategy = "quality_first"
        else:
            scores = self._score_borda(subtask, candidates)
            strategy = "borda_composite"

        total = sum(scores.values())
        probs = {k: v / total for k, v in scores.items()} if total > 0 else {k: 1/len(scores) for k in scores}
        winner = max(probs, key=probs.get)
        return winner, probs, probs[winner], strategy

    def route(self, task_spec: dict) -> dict:
        spec = dict(task_spec)
        subtasks = spec.get("subtasks", [])
        budget = spec.get("budget", {}).get("max_usd", 10.0)
        total_estimated = 0.0
        routing_log = []

        for subtask in subtasks:
            st_id = subtask["id"]
            estimated_tokens = subtask.get("estimated_tokens", 4096)
            winner, scores, confidence, strategy = self._vote(subtask)

            cost_1k = MODEL_COST_USD.get(winner, 1.0)
            estimated_cost = (estimated_tokens / 1000) * cost_1k
            total_estimated += estimated_cost

            if self.cost_budget and total_estimated > self.cost_budget:
                cheapest = min(scores.keys(), key=lambda c: MODEL_COST_USD.get(c, 999))
                if cheapest != winner:
                    winner = cheapest
                    estimated_cost = (estimated_tokens / 1000) * MODEL_COST_USD.get(winner, 1.0)
                    strategy += "_budget_fallback"

            subtask["assigned_model"] = winner
            subtask["budget_allocation"] = estimated_cost / budget if budget > 0 else 0

            routing_log.append(RoutingDecision(
                subtask_id=st_id,
                assigned_model=winner,
                council_vote=scores,
                estimated_cost_usd=round(estimated_cost, 4),
                confidence=round(confidence, 4),
                strategy=strategy,
                reasoning=f"{strategy} vote: {winner} wins with {confidence:.1%} confidence",
            ).to_dict())

        if total_estimated > budget and budget > 0:
            for st in sorted(subtasks, key=lambda x: MODEL_COST_USD.get(x.get("assigned_model", ""), 0), reverse=True):
                current_model = st.get("assigned_model", "")
                current_cost = (st.get("estimated_tokens", 0) / 1000) * MODEL_COST_USD.get(current_model, 0)
                for fallback in sorted(self._get_candidates(st.get("type", "")), key=lambda m: MODEL_COST_USD.get(m, 999)):
                    if fallback == current_model:
                        continue
                    fallback_cost = (st.get("estimated_tokens", 0) / 1000) * MODEL_COST_USD.get(fallback, 0)
                    if fallback_cost < current_cost:
                        st["assigned_model"] = fallback
                        total_estimated -= (current_cost - fallback_cost)
                        break
                if total_estimated <= budget:
                    break

        for s in subtasks:
            tokens = s.get("estimated_tokens", 0)
            cost = (tokens / 1000) * MODEL_COST_USD.get(s.get("assigned_model", ""), 1.0)
            s["budget_allocation"] = cost / budget if budget > 0 else 0

        spec["routing"] = {
            "method": self.vote_method.value,
            "timestamp": datetime.now().isoformat(),
            "total_estimated_cost_usd": round(total_estimated, 4),
            "budget_utilization": total_estimated / budget if budget > 0 else 0,
            "decisions": routing_log,
        }

        return spec

    def get_audit_log(self) -> list[dict]:
        return []


def main():
    import argparse

    parser = argparse.ArgumentParser(description="NecroSwarm Router for K2-Backbone")
    parser.add_argument("--spec", type=Path, required=True, help="TaskSpec JSON file")
    parser.add_argument("--method", choices=["borda", "cost_first", "quality_first"], default="borda")
    parser.add_argument("--budget", type=float, help="Cost budget in USD")
    parser.add_argument("--output", type=Path, default=Path("routed_spec.json"))
    args = parser.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)

    router = NecroSwarmRouter(
        vote_method=VoteMethod(args.method),
        cost_budget_usd=args.budget,
    )
    routed = router.route(spec)

    with open(args.output, "w") as f:
        json.dump(routed, f, indent=2, ensure_ascii=False)

    print(f"Routed {len(routed['subtasks'])} subtasks | method={args.method} | cost=${routed['routing']['total_estimated_cost_usd']}")
    for d in routed["routing"]["decisions"][:5]:
        print(f"  {d['subtask_id']} -> {d['assigned_model']} (${d['estimated_cost_usd']}) [{d['strategy']}]")


if __name__ == "__main__":
    main()