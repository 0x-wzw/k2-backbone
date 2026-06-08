"""NecroSwarm Router Adapter for K2-Backbone — Single Source of Truth via dimension_map.py

Maps TaskSpec subtasks to council members via weighted voting.
Core logic: Borda voting with cost-aware fallback.

Updated 2026-06-08: model definitions imported from neuroswarm/swarm/dimension_map.py.
All model changes go in dimension_map.py — this file reads from there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import sys
_neuroswarm_path = Path(__file__).parent.parent.parent / "frameworks" / "neuroswarm"
if str(_neuroswarm_path) not in sys.path:
    sys.path.insert(0, str(_neuroswarm_path))

from neuroswarm.swarm.dimension_map import (
    DIMENSION_MAP,
    DIMENSION_FALLBACK,
    DIMENSION_DESCRIPTIONS,
)


# ── Single source of truth: derived from dimension_map ──────────────

# Map every model appearing in DIMENSION_MAP + DIMENSION_FALLBACK → cost
# Approximate cost per 1K output tokens (USD)
MODEL_COST_USD = {
    "kimi-k2.6:cloud":         3.00,
    "qwen3.5:122b:cloud":      4.00,
    "glm-5.1:cloud":           5.00,
    "qwen3-vl:235b:cloud":     4.00,
    "qwen3.5:397b:cloud":      6.00,
    "gemma4:26b:cloud":        1.50,
    "deepseek-v4-flash:cloud": 0.60,
    "nemotron-3-ultra:cloud":  1.20,
    "minimax-m3:cloud":        2.50,
    "deepseek-v4-pro:cloud":   2.50,
    # Fallback references
    "gemma4:12b:cloud":        0.40,
    "qwen3.5:9b:cloud":        0.20,
    "nemotron-3-nano:cloud":   0.10,
}

# Capability scores (0-10) per task family — micro-tuned per dimension_map model
CAPABILITY_MATRIX = {
    "kimi-k2.6:cloud": {
        "research": 7, "code": 7, "analysis": 8, "writing": 7,
        "optimization": 7, "orchestration": 10, "integration": 9,
    },
    "qwen3.5:122b:cloud": {
        "research": 10, "code": 9, "analysis": 10, "writing": 8,
        "optimization": 8, "orchestration": 6, "integration": 5,
    },
    "glm-5.1:cloud": {
        "research": 6, "code": 10, "analysis": 8, "writing": 6,
        "optimization": 9, "orchestration": 5, "integration": 5,
    },
    "qwen3-vl:235b:cloud": {
        "research": 4, "code": 5, "analysis": 5, "writing": 4,
        "optimization": 3, "orchestration": 3, "integration": 3,
    },
    "qwen3.5:397b:cloud": {
        "research": 10, "code": 8, "analysis": 10, "writing": 9,
        "optimization": 9, "orchestration": 7, "integration": 6,
    },
    "gemma4:26b:cloud": {
        "research": 8, "code": 8, "analysis": 8, "writing": 7,
        "optimization": 7, "orchestration": 5, "integration": 5,
    },
    "deepseek-v4-flash:cloud": {
        "research": 6, "code": 7, "analysis": 7, "writing": 5,
        "optimization": 6, "orchestration": 4, "integration": 4,
    },
    "nemotron-3-ultra:cloud": {
        "research": 6, "code": 5, "analysis": 7, "writing": 5,
        "optimization": 5, "orchestration": 8, "integration": 7,
    },
    "minimax-m3:cloud": {
        "research": 9, "code": 8, "analysis": 7, "writing": 8,
        "optimization": 7, "orchestration": 6, "integration": 6,
    },
    "deepseek-v4-pro:cloud": {
        "research": 9, "code": 8, "analysis": 9, "writing": 7,
        "optimization": 8, "orchestration": 6, "integration": 5,
    },
    # Fallback fallbacks
    "gemma4:12b:cloud":  {"research": 5, "code": 6, "analysis": 6, "writing": 4, "optimization": 5, "orchestration": 3, "integration": 3},
    "qwen3.5:9b:cloud":  {"research": 5, "code": 5, "analysis": 6, "writing": 4, "optimization": 4, "orchestration": 3, "integration": 3},
    "nemotron-3-nano:cloud": {"research": 3, "code": 4, "analysis": 4, "writing": 3, "optimization": 3, "orchestration": 3, "integration": 3},
}

# Build SUBTASK_TYPE_TO_SPECIALIZATION from dimension_map
# Each dimension description maps to subtask types
_DIM_TO_TASK = {
    "D1_synthesis":    ["synthesis", "integration"],
    "D2_deep_reason":  ["research", "analysis"],
    "D3_code":         ["code_generation", "code_review", "testing", "optimization"],
    "D4_vision":       ["visualization"],
    "D5_strategy":     ["planning", "architecture", "writing"],
    "D6_analysis":     ["analysis", "data_processing"],
    "D7_general":      ["documentation", "writing"],
    "D8_verification": ["code_review", "testing"],
    "D9_research":     ["research", "synthesis"],
    "D10_think":       ["planning", "architecture"],
}

SUBTASK_TYPE_TO_SPECIALIZATION: dict[str, list[str]] = {}
for _dim, _tasks in _DIM_TO_TASK.items():
    _model = DIMENSION_MAP.get(_dim)
    if _model:
        for _t in _tasks:
            if _t not in SUBTASK_TYPE_TO_SPECIALIZATION:
                _fallbacks = DIMENSION_FALLBACK.get(_dim, [])
                SUBTASK_TYPE_TO_SPECIALIZATION[_t] = [_model] + _fallbacks


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

    @classmethod
    def from_config(cls, d: dict) -> CouncilMember:
        return cls(
            id=d["id"],
            name=d["name"],
            model=d["model"],
            tier=d["tier"],
            vote_power=d["vote_power"],
            weight=d["weight"],
            specialties=d.get("specialties", []),
        )


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
        config_path: Optional[Path] = None,
        vote_method: VoteMethod = VoteMethod.BORDA,
        cost_budget_usd: Optional[float] = None,
    ):
        self.config_path = config_path or Path(
            __file__).parent.parent.parent / "frameworks" / "necroswarm" / "backend" / "app" / "config" / "council-members.json"
        self.vote_method = vote_method
        self.cost_budget = cost_budget_usd
        self.members = self._load_members()

    def _load_members(self) -> list[CouncilMember]:
        """Load council members from dimension_map (single source of truth)."""
        # Build members from DIMENSION_MAP
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
        """Get candidate members for a subtask type."""
        candidates = SUBTASK_TYPE_TO_SPECIALIZATION.get(subtask_type, [])
        if not candidates:
            # Fallback: use all dimension map models
            candidates = list(DIMENSION_MAP.values())
        return candidates

    def _score_borda(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        """Borda count: rank candidates by composite capability/cost/tier score."""
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
        """Prioritize cheapest model."""
        estimated_tokens = subtask.get("estimated_tokens", 4096)
        scores = {}
        for cid in candidates:
            cost_1k = MODEL_COST_USD.get(cid, 1.0)
            estimated_cost = (estimated_tokens / 1000) * cost_1k
            scores[cid] = 1.0 / (estimated_cost + 0.001)
        return scores

    def _score_quality_first(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        """Prioritize highest capability regardless of cost."""
        scores = {}
        subtask_type = subtask.get("type", "analysis")
        task_family = subtask_type.split("_")[0]
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
        if total == 0:
            total = 1
        probs = {k: v / total for k, v in scores.items()}

        winner = max(probs, key=probs.get)
        confidence = probs[winner]
        return winner, probs, confidence, strategy

    def route(self, task_spec: dict) -> dict:
        """Route all subtasks through the council. Returns TaskSpec enriched with assigned_model."""
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

            decision = RoutingDecision(
                subtask_id=st_id,
                assigned_model=winner,
                council_vote=scores,
                estimated_cost_usd=round(estimated_cost, 4),
                confidence=round(confidence, 4),
                strategy=strategy,
                reasoning=f"{strategy} vote: {winner} wins with {confidence:.1%} confidence",
            )
            routing_log.append(decision.to_dict())

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

    print(f"✅ Routed {len(routed['subtasks'])} subtasks")
    print(f"   Method: {args.method}")
    print(f"   Estimated cost: ${routed['routing']['total_estimated_cost_usd']}")
    print(f"   Budget utilization: {routed['routing']['budget_utilization']:.1%}")
    print(f"   Saved to: {args.output}")
    print()
    for d in routed["routing"]["decisions"][:5]:
        print(f"   {d['subtask_id']} → {d['assigned_model']} (${d['estimated_cost_usd']}) [{d['strategy']}]")


if __name__ == "__main__":
    main()