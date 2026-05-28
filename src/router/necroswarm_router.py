from __future__ import annotations
"""
NecroSwarm Router Adapter for K2-Backbone

Maps TaskSpec subtasks to council members via weighted voting.
Core logic: Borda voting with cost-aware fallback.

Usage:
    python -m k2_backbone.router.necroswarm_router --spec task_spec.json
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# ── Constants ───────────────────────────────────────────────────────

COUNCIL_CONFIG = Path(__file__).parent.parent.parent / "frameworks" / "necroswarm" / "backend" / "app" / "config" / "council-members.json"

SUBTASK_TYPE_TO_SPECIALIZATION = {
    "research":        ["deepseek", "glm", "kimi"],
    "code_generation": ["claude", "kimi", "deepseek"],
    "code_review":     ["claude", "kimi", "qwen"],
    "testing":         ["qwen", "kimi", "deepseek"],
    "documentation":   ["claude", "glm", "kimi"],
    "analysis":        ["kimi", "deepseek", "glm"],
    "writing":         ["claude", "kimi", "glm"],
    "synthesis":       ["kimi", "claude", "deepseek"],
    "optimization":    ["kimi", "deepseek", "qwen"],
    "data_processing": ["deepseek", "qwen", "glm"],
    "visualization":   ["glm", "kimi", "claude"],
    "integration":     ["kimi", "claude", "qwen"],
}

# Cost per 1K tokens (output), approximate USD
COST_PER_1K = {
    "kimi":      3.00,   # K2.6
    "claude":    3.75,   # Opus 4
    "deepseek":  0.50,   # V3.2
    "glm":       0.30,   # GLM-5
    "qwen":      0.10,   # Qwen 2.5
}

# Capability scores (0-10) per task type
CAPABILITY_MATRIX = {
    "kimi":      {"research": 9, "code": 9, "analysis": 10, "writing": 8, "optimization": 9},
    "claude":    {"research": 7, "code": 10, "analysis": 8, "writing": 10, "optimization": 8},
    "deepseek":  {"research": 10, "code": 8, "analysis": 9, "writing": 7, "optimization": 8},
    "glm":       {"research": 7, "code": 6, "analysis": 7, "writing": 7, "optimization": 6},
    "qwen":      {"research": 5, "code": 6, "analysis": 5, "writing": 5, "optimization": 6},
}


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
        self.config_path = config_path or COUNCIL_CONFIG
        self.vote_method = vote_method
        self.cost_budget = cost_budget_usd
        self.members = self._load_members()

    def _load_members(self) -> list[CouncilMember]:
        """Load council members from NecroSwarm config."""
        if not self.config_path.exists():
            # Fallback to hardcoded if submodule not present
            return [
                CouncilMember("kimi", "Kimi K2.6", "kimi-k2.6", "T1", 3, 1.0),
                CouncilMember("claude", "Claude Opus", "claude-opus-4", "T1", 3, 1.0),
                CouncilMember("deepseek", "DeepSeek V3.2", "deepseek-v3.2", "T2", 2, 0.8),
                CouncilMember("glm", "GLM-5", "glm-5", "T2", 2, 0.8),
                CouncilMember("qwen", "Qwen 2.5", "qwen2.5", "T3", 1, 0.5),
            ]

        with open(self.config_path) as f:
            config = json.load(f)

        members = []
        for category in ["cognitive_leads", "research_synthesizers", "execution_specialists"]:
            for m in config["council_members"].get(category, []):
                members.append(CouncilMember.from_config(m))
        return members

    def _get_candidates(self, subtask_type: str) -> list[str]:
        """Get candidate members for a subtask type."""
        return SUBTASK_TYPE_TO_SPECIALIZATION.get(subtask_type, ["kimi", "claude", "deepseek"])

    def _score_borda(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        """
        Borda count: rank candidates, assign points by position.
        Lower rank = more points.
        """
        scores = {}
        subtask_type = subtask.get("type", "analysis")
        task_family = subtask_type.split("_")[0]  # e.g. "code_generation" → "code"

        # Score each candidate on multiple dimensions
        ranked = []
        for cid in candidates:
            cap = CAPABILITY_MATRIX.get(cid, {})
            capability = cap.get(task_family, cap.get("analysis", 5))
            cost = COST_PER_1K.get(cid, 1.0)
            member = next((m for m in self.members if m.id == cid), None)
            vote_power = member.vote_power if member else 1
            tier_weight = member.weight if member else 0.5

            # Composite score: capability * tier * 1/cost (normalized)
            cost_score = 1.0 / (cost + 0.01)
            composite = (capability * tier_weight * cost_score) / (vote_power ** 0.5)
            ranked.append((cid, composite))

        # Sort by composite score descending
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Borda points: first gets N points, second gets N-1, etc.
        n = len(ranked)
        for i, (cid, _) in enumerate(ranked):
            scores[cid] = n - i

        return scores

    def _score_cost_first(self, subtask: dict, candidates: list[str]) -> dict[str, float]:
        """Prioritize cheapest model that can handle the task."""
        scores = {}
        estimated_tokens = subtask.get("estimated_tokens", 4096)

        for cid in candidates:
            cost_1k = COST_PER_1K.get(cid, 1.0)
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
        """
        Run council vote for a subtask.

        Returns: (winner_id, full_scores, confidence, strategy)
        """
        candidates = self._get_candidates(subtask.get("type", "analysis"))

        # Select scoring method
        if self.vote_method == VoteMethod.COST_FIRST:
            scores = self._score_cost_first(subtask, candidates)
            strategy = "cost_first"
        elif self.vote_method == VoteMethod.QUALITY_FIRST:
            scores = self._score_quality_first(subtask, candidates)
            strategy = "quality_first"
        else:
            scores = self._score_borda(subtask, candidates)
            strategy = "borda_composite"

        # Normalize scores to probabilities
        total = sum(scores.values())
        if total == 0:
            total = 1
        probs = {k: v / total for k, v in scores.items()}

        # Winner
        winner = max(probs, key=probs.get)
        confidence = probs[winner]

        return winner, probs, confidence, strategy

    def route(self, task_spec: dict) -> dict:
        """
        Route all subtasks in a TaskSpec through the council.

        Returns: TaskSpec enriched with `assigned_model` on each subtask.
        """
        spec = dict(task_spec)  # Shallow copy
        subtasks = spec.get("subtasks", [])
        budget = spec.get("budget", {}).get("max_usd", 10.0)
        total_estimated = 0.0
        routing_log = []

        for subtask in subtasks:
            st_id = subtask["id"]
            estimated_tokens = subtask.get("estimated_tokens", 4096)

            # Run council vote
            winner, scores, confidence, strategy = self._vote(subtask)

            # Calculate estimated cost
            cost_1k = COST_PER_1K.get(winner, 1.0)
            estimated_cost = (estimated_tokens / 1000) * cost_1k
            total_estimated += estimated_cost

            # Budget check: if over budget, reroute to cheaper model
            if self.cost_budget and total_estimated > self.cost_budget:
                # Find cheapest candidate
                cheapest = min(scores.keys(), key=lambda c: COST_PER_1K.get(c, 999))
                if cheapest != winner:
                    winner = cheapest
                    estimated_cost = (estimated_tokens / 1000) * COST_PER_1K.get(winner, 1.0)
                    strategy += "_budget_fallback"

            # Map winner to model string
            member = next((m for m in self.members if m.id == winner), None)
            model_str = member.model if member else winner

            # Assign to subtask
            subtask["assigned_model"] = model_str
            subtask["budget_allocation"] = estimated_cost / budget if budget > 0 else 0

            decision = RoutingDecision(
                subtask_id=st_id,
                assigned_model=model_str,
                council_vote=scores,
                estimated_cost_usd=round(estimated_cost, 4),
                confidence=round(confidence, 4),
                strategy=strategy,
                reasoning=f"{strategy} vote: {winner} wins with {confidence:.1%} confidence",
            )
            routing_log.append(decision.to_dict())

        # Add routing metadata
        spec["routing"] = {
            "method": self.vote_method.value,
            "timestamp": datetime.now().isoformat(),
            "total_estimated_cost_usd": round(total_estimated, 4),
            "budget_utilization": total_estimated / budget if budget > 0 else 0,
            "decisions": routing_log,
        }

        return spec

    def get_audit_log(self) -> list[dict]:
        """Return last routing decisions for audit."""
        # In production: persist to append-only log
        return []


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="NecroSwarm Router for K2-Backbone")
    parser.add_argument("--spec", type=Path, required=True, help="TaskSpec JSON file")
    parser.add_argument("--method", choices=["borda", "cost_first", "quality_first"], default="borda")
    parser.add_argument("--budget", type=float, help="Cost budget in USD")
    parser.add_argument("--output", type=Path, default=Path("routed_spec.json"))
    args = parser.parse_args()

    # Load spec
    with open(args.spec) as f:
        spec = json.load(f)

    # Route
    router = NecroSwarmRouter(
        vote_method=VoteMethod(args.method),
        cost_budget_usd=args.budget,
    )
    routed = router.route(spec)

    # Save
    with open(args.output, "w") as f:
        json.dump(routed, f, indent=2, ensure_ascii=False)

    # Summary
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
