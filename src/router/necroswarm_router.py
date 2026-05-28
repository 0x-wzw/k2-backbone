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
    "research":        ["qwen3.5-122b", "gemma4-31b", "deepseek-v3.2"],
    "code_generation": ["glm-5.1", "deepseek-v3.2", "qwen3-coder-next"],
    "code_review":     ["devstral-small-2", "glm-5.1", "gemma4-31b"],
    "testing":         ["qwen3.5-122b", "gemma4-31b", "devstral-small-2"],
    "documentation":   ["qwen3.5-122b", "gemma4-31b", "kimi-k2.6"],
    "analysis":        ["qwen3.5-122b", "deepseek-v3.2", "gemma4-31b"],
    "writing":         ["qwen3.5-122b", "gemma4-31b", "deepseek-v3.2"],
    "synthesis":       ["qwen3.5-122b", "kimi-k2.6", "deepseek-v3.2"],
    "optimization":    ["glm-5.1", "deepseek-v3.2", "qwen3.5-122b"],
    "data_processing": ["deepseek-v3.2", "nemotron-3-super", "gemma4-31b"],
    "visualization":   ["gemma4-31b", "kimi-k2.6", "qwen3.5-122b"],
    "integration":     ["kimi-k2.6", "nemotron-3-super", "deepseek-v3.2"],
}

# Cost per 1K tokens (output), approximate USD - Ollama Cloud
# These are per-1K-token rates (not per-token)
COST_PER_1K = {
    "glm-5.1":           5.00,    # T0 Premium - SWE SOTA ($5/1M = $0.005/1K)
    "qwen3.5-122b":      4.00,    # T0 Premium - Reasoning king
    "kimi-k2.6":         3.00,    # T1 - Agentic orchestration
    "deepseek-v3.2":     2.00,    # T1 - Balanced performer
    "gemma4-31b":        1.50,    # T1 - Multimodal
    "nemotron-3-super":  1.20,    # T2 - Multi-agent efficiency
    "devstral-small-2":  1.00,    # T2 - SWE specialist
    "glm-5":             1.80,    # T2 - Complex systems
    "deepseek-v4-pro":   2.50,    # T2 - Frontier reasoning
    "deepseek-v4-flash": 0.60,    # T3 - Budget long-context
    "gemini-3-flash":    0.50,    # T3 - Speed
    "qwen3-coder-next":  0.80,    # T3 - Coding workflows
    "minimax-m2.7":    1.00,    # T3 - Coding + agentic
    "nemotron-3-nano":   0.10,    # T4 - Ultra-cheap fallback
    "gemma4-e2b":        0.08,    # T4 - Edge
    "qwen3.5-0.8b":      0.05,    # T4 - Ultra-small
    "kimi":              3.00,    # Legacy compat
    "claude":            3.75,    # Legacy compat
    "deepseek":          0.50,    # Legacy compat
    "glm":               0.30,    # Legacy compat
    "qwen":              0.10,    # Legacy compat
}

# Capability scores (0-10) per task type - Ollama Cloud best-in-class
CAPABILITY_MATRIX = {
    "kimi-k2.6": {
        "research": 7, "code": 7, "analysis": 8, "writing": 7,
        "optimization": 7, "orchestration": 10, "integration": 9
    },
    "glm-5.1": {
        "research": 6, "code": 10, "analysis": 8, "writing": 6,
        "optimization": 9, "orchestration": 5, "integration": 5
    },
    "qwen3.5-122b": {
        "research": 10, "code": 9, "analysis": 10, "writing": 8,
        "optimization": 8, "orchestration": 6, "integration": 5
    },
    "deepseek-v3.2": {
        "research": 8, "code": 9, "analysis": 9, "writing": 7,
        "optimization": 8, "orchestration": 6, "integration": 6
    },
    "gemma4-31b": {
        "research": 8, "code": 8, "analysis": 8, "writing": 7,
        "optimization": 7, "orchestration": 5, "integration": 5
    },
    "nemotron-3-super": {
        "research": 6, "code": 5, "analysis": 7, "writing": 5,
        "optimization": 5, "orchestration": 8, "integration": 7
    },
    "devstral-small-2": {
        "research": 4, "code": 8, "analysis": 5, "writing": 4,
        "optimization": 4, "orchestration": 3, "integration": 3
    },
    "deepseek-v4-flash": {
        "research": 6, "code": 7, "analysis": 7, "writing": 5,
        "optimization": 6, "orchestration": 4, "integration": 4
    },
    "gemini-3-flash": {
        "research": 5, "code": 6, "analysis": 6, "writing": 5,
        "optimization": 5, "orchestration": 4, "integration": 4
    },
    "qwen3-coder-next": {
        "research": 4, "code": 9, "analysis": 5, "writing": 4,
        "optimization": 5, "orchestration": 3, "integration": 3
    },
    "minimax-m2.7": {
        "research": 5, "code": 7, "analysis": 5, "writing": 5,
        "optimization": 5, "orchestration": 5, "integration": 4
    },
    "nemotron-3-nano": {
        "research": 3, "code": 4, "analysis": 4, "writing": 3,
        "optimization": 3, "orchestration": 3, "integration": 3
    },
    # Legacy compatibility
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

        budget = task_spec.get("budget", {}).get("max_usd", 10.0)
        total_estimated = sum((s.get("estimated_tokens", 0) / 1000) * COST_PER_1K.get(s.get("assigned_model", ""), 1.0) for s in routed_spec.get("subtasks", []))
        
        # Budget enforcement: downgrade expensive tasks if over budget
        if total_estimated > budget and budget > 0:
            logger.warning(f"Budget exceeded: ${total_estimated:.2f} > ${budget:.2f}. Applying fallback.")
            for st in sorted(routed_spec["subtasks"], key=lambda x: COST_PER_1K.get(x.get("assigned_model", ""), 0), reverse=True):
                current_model = st.get("assigned_model", "")
                current_cost = (st.get("estimated_tokens", 0) / 1000) * COST_PER_1K.get(current_model, 0)
                task_type = st.get("type", "")
                candidates = self._get_candidates(task_type)
                for fallback in sorted(candidates, key=lambda m: COST_PER_1K.get(m, 999)):
                    if fallback == current_model:
                        continue
                    fallback_cost = (st.get("estimated_tokens", 0) / 1000) * COST_PER_1K.get(fallback, 0)
                    if fallback_cost < current_cost:
                        st["assigned_model"] = fallback
                        total_estimated -= (current_cost - fallback_cost)
                        break
                if total_estimated <= budget:
                    break
            
            routed_spec["routing"]["total_estimated_cost_usd"] = total_estimated
            routed_spec["routing"]["budget_enforced"] = True
            routed_spec["routing"]["original_cost"] = routed_spec["routing"].get("total_estimated_cost_usd", 0)

    # Update budget allocations
    for s in routed_spec["subtasks"]:
        tokens = s.get("estimated_tokens", 0)
        model = s.get("assigned_model", "")
        cost = (tokens / 1000) * COST_PER_1K.get(model, 1.0)
        s["budget_allocation"] = cost / budget if budget > 0 else 0
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
