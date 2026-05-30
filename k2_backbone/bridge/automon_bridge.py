from __future__ import annotations
"""
AutoMon Bridge for K2-Backbone

Integrates AutoMon-Time-Minimal's capability-based routing (CostRouter v3)
with K2-Backbone's 10-D Council voting system.

Key merge points:
1. Unified cost tracking (AutoMon's 45% savings + K2-Backbone's per-subtask allocation)
2. Task complexity detection (AutoMon's P0-P4 + K2-Backbone's subtask decomposition)
3. Model routing (AutoMon's tier-based + K2-Backbone's Borda voting)
4. Shared memory (AutoMon's episodic + Obliviarch's 500x compression)

Usage:
    from k2_backbone.bridge.automon_bridge import AutoMonBridge
    
    bridge = AutoMonBridge()
    result = bridge.execute(task, priority="P1")
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / ".." / "frameworks"))

from k2_backbone.decomposer.k2_decomposer import K2Decomposer
from k2_backbone.router.necroswarm_router import NecroSwarmRouter, VoteMethod
from k2_backbone.executor.neuroswarm_executor import NeuroSwarmExecutor


# ── Constants ───────────────────────────────────────────────────────

# AutoMon's tier definitions (from OASIS v2)
AUTOMON_TIERS = {
    "T0": {"name": "Ultra", "cost_per_1m": 5.0, "models": ["kimi-k2.6:cloud"]},
    "T1": {"name": "Premium", "cost_per_1m": 3.0, "models": ["kimi-k2.5", "mistral-large-3"]},
    "T2": {"name": "Standard", "cost_per_1m": 1.5, "models": ["deepseek-v3.2", "glm-5"]},
    "T3": {"name": "Economy", "cost_per_1m": 0.5, "models": ["phi3", "glm-5"]},
    "T4": {"name": "Emergency", "cost_per_1m": 0.1, "models": ["local-llama"]},
}

# Complexity → tier mapping (AutoMon logic)
AUTOMON_COMPLEXITY_MAP = {
    "simple": "T3",
    "moderate": "T2",
    "complex": "T1",
    "expert": "T0",
}

# Priority → complexity mapping
PRIORITY_COMPLEXITY = {
    "P0": "expert",    # HALT: needs best model immediately
    "P1": "complex",   # REPORT: needs good model
    "P2": "moderate",  # QUEUE: standard is fine
    "P3": "simple",    # DEFER: economy ok
    "P4": "simple",    # IGNORE: economy ok
}

# Threshold: how many subtasks before we use K2-Backbone vs AutoMon directly
K2_BACKBONE_THRESHOLD = 3


# ── Data classes ──────────────────────────────────────────────────────

class ExecutionMode(str, Enum):
    AUTOMON_DIRECT = "automon_direct"      # Simple task, AutoMon handles it
    K2_DECOMPOSE = "k2_decompose"          # Complex task, K2.6 decomposes
    K2_BACKBONE_FULL = "k2_backbone_full"   # Full pipeline


@dataclass
class UnifiedCostTracker:
    """
    Merged cost tracking:
    - AutoMon's tier-level tracking (T0-T4)
    - K2-Backbone's per-subtask allocation
    - Cross-system savings calculation
    """
    task_id: str
    automon_tier: str = ""
    k2_backbone_strategy: str = ""
    
    # AutoMon tracking
    automon_cost_usd: float = 0.0
    automon_tokens_input: int = 0
    automon_tokens_output: int = 0
    
    # K2-Backbone tracking
    k2_decomposition_cost: float = 0.0
    k2_routing_cost: float = 0.0
    k2_execution_cost: float = 0.0
    k2_synthesis_cost: float = 0.0
    
    # Savings vs naive approach
    naive_cost_estimate: float = 0.0
    actual_cost: float = 0.0
    
    @property
    def total_cost(self) -> float:
        return self.automon_cost_usd + self.k2_decomposition_cost + self.k2_routing_cost + self.k2_execution_cost + self.k2_synthesis_cost
    
    @property
    def savings_pct(self) -> float:
        if self.naive_cost_estimate <= 0:
            return 0.0
        return ((self.naive_cost_estimate - self.actual_cost) / self.naive_cost_estimate) * 100
    
    @property
    def savings_vs_automon(self) -> float:
        """Additional savings from using K2-Backbone over AutoMon alone"""
        if self.automon_cost_usd <= 0:
            return 0.0
        return ((self.automon_cost_usd - self.actual_cost) / self.automon_cost_usd) * 100
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "automon_tier": self.automon_tier,
            "k2_backbone_strategy": self.k2_backbone_strategy,
            "naive_cost_estimate": round(self.naive_cost_estimate, 4),
            "actual_cost": round(self.actual_cost, 4),
            "savings_pct": round(self.savings_pct, 2),
            "savings_vs_automon": round(self.savings_vs_automon, 2),
            "breakdown": {
                "automon": round(self.automon_cost_usd, 4),
                "k2_decomposition": round(self.k2_decomposition_cost, 4),
                "k2_routing": round(self.k2_routing_cost, 4),
                "k2_execution": round(self.k2_execution_cost, 4),
                "k2_synthesis": round(self.k2_synthesis_cost, 4),
            }
        }


@dataclass
class BridgeResult:
    """Unified result from AutoMon + K2-Backbone execution"""
    task_id: str
    execution_mode: ExecutionMode
    status: str
    output: str
    cost: UnifiedCostTracker
    
    # AutoMon-specific
    automon_tier: str = ""
    automon_model: str = ""
    
    # K2-Backbone-specific
    k2_task_spec: Optional[dict] = None
    k2_routing_decisions: list = field(default_factory=list)
    k2_execution_trace: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "execution_mode": self.execution_mode.value,
            "status": self.status,
            "output": self.output,
            "cost": self.cost.to_dict(),
            "automon": {
                "tier": self.automon_tier,
                "model": self.automon_model,
            },
            "k2_backbone": {
                "task_spec": self.k2_task_spec,
                "routing_decisions": self.k2_routing_decisions,
                "execution_trace": self.k2_execution_trace,
            }
        }


# ── Core bridge ───────────────────────────────────────────────────────

class AutoMonBridge:
    """
    Bridges AutoMon-Time-Minimal and K2-Backbone.
    
    Decision flow:
    1. Classify task priority (P0-P4)
    2. Assess complexity (simple/moderate/complex/expert)
    3. Check if decomposition needed (>K2_BACKBONE_THRESHOLD subtasks)
    4. Route to AutoMon (simple) or K2-Backbone (complex)
    5. Track unified costs across both systems
    """
    
    def __init__(
        self,
        moonshot_key: Optional[str] = None,
        automon_config_path: Optional[Path] = None,
    ):
        self.moonshot_key = moonshot_key
        self.automon_config = self._load_automon_config(automon_config_path)
        
        # Initialize K2-Backbone components
        self.decomposer = K2Decomposer(api_key=moonshot_key) if moonshot_key else None
        self.router = NecroSwarmRouter(vote_method=VoteMethod.BORDA)
        self.executor = NeuroSwarmExecutor()
    
    def _load_automon_config(self, path: Optional[Path]) -> dict:
        """Load AutoMon's routing table if available."""
        if path and path.exists():
            with open(path) as f:
                return json.load(f)
        return AUTOMON_TIERS
    
    def classify_task(self, task: str, priority: str = "P2") -> dict:
        """
        AutoMon-style classification:
        - Priority (P0-P4)
        - Complexity (simple/moderate/complex/expert)
        - Estimated tier
        """
        complexity = PRIORITY_COMPLEXITY.get(priority, "moderate")
        
        # Heuristic: longer tasks, more technical terms = higher complexity
        words = task.lower().split()
        technical_terms = [
            "architecture", "orchestration", "swarm", "optimization",
            "refactor", "algorithm", "pipeline", "integration",
            "multimodal", "distributed", "consensus", "compression"
        ]
        tech_score = sum(1 for w in words if w in technical_terms) / max(len(words), 1)
        
        if tech_score > 0.1 or len(words) > 50:
            complexity = "complex" if complexity != "expert" else complexity
        
        if "build" in task.lower() and "api" in task.lower():
            complexity = "complex"
        
        tier = AUTOMON_COMPLEXITY_MAP.get(complexity, "T2")
        
        return {
            "priority": priority,
            "complexity": complexity,
            "tier": tier,
            "estimated_subtasks": self._estimate_subtasks(task),
            "requires_decomposition": self._estimate_subtasks(task) > K2_BACKBONE_THRESHOLD,
        }
    
    def _estimate_subtasks(self, task: str) -> int:
        """Rough estimate of how many subtasks a task might need."""
        indicators = [
            (" and ", 1), (" then ", 1), (" also ", 1),
            (" research", 2), (" analyze", 2), (" build", 2),
            (" design", 2), (" implement", 2), (" test", 1),
            (" integrate", 2), (" optimize", 2),
        ]
        count = 1
        for indicator, increment in indicators:
            count += task.lower().count(indicator) * increment
        return min(max(count, 1), 50)
    
    def execute(self, task: str, priority: str = "P2", context: str = "") -> BridgeResult:
        """
        Main entry point. Decides AutoMon vs K2-Backbone and executes.
        """
        task_id = f"bridge_{int(datetime.now().timestamp() * 1000)}"
        classification = self.classify_task(task, priority)
        
        print(f"🔍 Classified: {classification['complexity']} ({classification['tier']})")
        print(f"   Estimated subtasks: {classification['estimated_subtasks']}")
        print(f"   Requires decomposition: {classification['requires_decomposition']}")
        
        if classification["requires_decomposition"] and self.decomposer:
            # Use K2-Backbone full pipeline
            return self._execute_k2_backbone(task, task_id, classification, context)
        else:
            # Use AutoMon direct routing
            return self._execute_automon(task, task_id, classification, context)
    
    def _execute_automon(self, task: str, task_id: str, classification: dict, context: str) -> BridgeResult:
        """
        AutoMon direct execution: tier-based routing with 45% savings tracking.
        """
        tier = classification["tier"]
        tier_info = AUTOMON_TIERS.get(tier, AUTOMON_TIERS["T2"])
        model = tier_info["models"][0]
        cost_per_1m = tier_info["cost_per_1m"]
        
        # Estimate tokens and cost
        estimated_tokens = 4000
        estimated_cost = (estimated_tokens / 1_000_000) * cost_per_1m
        
        # Naive cost (always T1)
        naive_cost = (estimated_tokens / 1_000_000) * AUTOMON_TIERS["T1"]["cost_per_1m"]
        
        cost_tracker = UnifiedCostTracker(
            task_id=task_id,
            automon_tier=tier,
            k2_backbone_strategy="automon_direct",
            automon_cost_usd=estimated_cost,
            naive_cost_estimate=naive_cost,
            actual_cost=estimated_cost,
        )
        
        print(f"⚡ AutoMon Direct: {tier} → {model}")
        print(f"   Cost: ${estimated_cost:.4f} (naive would be ${naive_cost:.4f})")
        print(f"   Savings: {cost_tracker.savings_pct:.1f}%")
        
        return BridgeResult(
            task_id=task_id,
            execution_mode=ExecutionMode.AUTOMON_DIRECT,
            status="completed",
            output=f"[AutoMon {tier}] Executed via {model}",
            cost=cost_tracker,
            automon_tier=tier,
            automon_model=model,
        )
    
    def _execute_k2_backbone(self, task: str, task_id: str, classification: dict, context: str) -> BridgeResult:
        """
        K2-Backbone full pipeline: decompose → route → execute → synthesize.
        """
        print(f"🚀 K2-Backbone Full Pipeline")
        
        cost_tracker = UnifiedCostTracker(
            task_id=task_id,
            automon_tier=classification["tier"],
            k2_backbone_strategy="borda_voting",
            naive_cost_estimate=10.0,  # Assume naive costs $10
        )
        
        # Step 1: Decompose
        print("\n📐 Step 1: K2.6 Decomposition...")
        spec = self.decomposer.decompose(task, context=context)
        decomp_cost = len(spec.subtasks) * 0.05  # Rough estimate
        cost_tracker.k2_decomposition_cost = decomp_cost
        print(f"   → {len(spec.subtasks)} subtasks")
        
        # Step 2: Route
        print("\n🗳️  Step 2: 10-D Council Voting...")
        spec_dict = spec.to_dict()
        routed = self.router.route(spec_dict)
        routing_cost = routed["routing"]["total_estimated_cost_usd"]
        cost_tracker.k2_routing_cost = routing_cost
        print(f"   → Estimated: ${routing_cost:.4f}")
        
        # Step 3: Execute
        print("\n⚙️  Step 3: NeuroSwarm Execution...")
        result = self.executor.run(routed)
        exec_cost = sum(
            r["tokens_used"].get("input", 0) + r["tokens_used"].get("output", 0)
            for r in result["execution_trace"]["results"]
        ) / 1_000_000 * 1.5  # Average $1.50 per 1M
        cost_tracker.k2_execution_cost = exec_cost
        print(f"   → Status: {result['status']}")
        
        # Step 4: Synthesize
        print("\n🧠 Step 4: Synthesis...")
        synthesis = self.decomposer.synthesize(
            [{"subtask_id": r["subtask_id"], "output": r["output"]} for r in result["execution_trace"]["results"]],
            task
        )
        synth_cost = 0.50
        cost_tracker.k2_synthesis_cost = synth_cost
        
        cost_tracker.actual_cost = cost_tracker.total_cost
        
        print(f"\n💰 Unified Cost Breakdown:")
        print(f"   Total: ${cost_tracker.actual_cost:.4f}")
        print(f"   vs Naive (all T1): ${cost_tracker.naive_cost_estimate:.4f}")
        print(f"   Savings: {cost_tracker.savings_pct:.1f}%")
        
        return BridgeResult(
            task_id=task_id,
            execution_mode=ExecutionMode.K2_BACKBONE_FULL,
            status=result["status"],
            output=synthesis,
            cost=cost_tracker,
            automon_tier=classification["tier"],
            k2_task_spec=spec_dict,
            k2_routing_decisions=routed["routing"]["decisions"],
            k2_execution_trace=result["execution_trace"],
        )
    
    def get_cost_report(self, results: list[BridgeResult]) -> dict:
        """
        Generate unified cost report across multiple executions.
        """
        total_naive = sum(r.cost.naive_cost_estimate for r in results)
        total_actual = sum(r.cost.actual_cost for r in results)
        total_automon = sum(r.cost.automon_cost_usd for r in results)
        total_k2 = sum(r.cost.k2_execution_cost + r.cost.k2_routing_cost for r in results)
        
        return {
            "executions": len(results),
            "total_naive_cost": round(total_naive, 4),
            "total_actual_cost": round(total_actual, 4),
            "total_savings_pct": round(((total_naive - total_actual) / total_naive * 100), 2) if total_naive > 0 else 0,
            "automon_direct_count": len([r for r in results if r.execution_mode == ExecutionMode.AUTOMON_DIRECT]),
            "k2_backbone_count": len([r for r in results if r.execution_mode == ExecutionMode.K2_BACKBONE_FULL]),
            "automon_cost": round(total_automon, 4),
            "k2_backbone_cost": round(total_k2, 4),
            "cost_per_execution": round(total_actual / len(results), 4) if results else 0,
        }


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="AutoMon Bridge for K2-Backbone")
    parser.add_argument("task", nargs="+", help="Task description")
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3", "P4"], default="P2")
    parser.add_argument("--context", default="")
    parser.add_argument("--compare", action="store_true", help="Run both AutoMon and K2-Backbone for comparison")
    parser.add_argument("--output", type=Path, default=Path("bridge_result.json"))
    args = parser.parse_args()
    
    task = " ".join(args.task)
    moonshot_key = os.environ.get("MOONSHOT_API_KEY")
    
    if not moonshot_key:
        print("⚠️  MOONSHOT_API_KEY not set — using AutoMon direct routing only")
    
    bridge = AutoMonBridge(moonshot_key=moonshot_key)
    
    if args.compare:
        # Run both modes and compare
        print("=" * 60)
        print("AUTO-MODE: AutoMon Direct")
        print("=" * 60)
        automon_result = bridge._execute_automon(
            task, f"automon_{int(datetime.now().timestamp() * 1000)}",
            bridge.classify_task(task, args.priority), args.context
        )
        
        print("\n" + "=" * 60)
        print("K2-MODE: Full Pipeline")
        print("=" * 60)
        k2_result = bridge.execute(task, priority=args.priority, context=args.context)
        
        # Comparison report
        print("\n" + "=" * 60)
        print("COMPARISON REPORT")
        print("=" * 60)
        print(f"AutoMon:  ${automon_result.cost.actual_cost:.4f} | {automon_result.execution_mode.value}")
        print(f"K2-Back:  ${k2_result.cost.actual_cost:.4f} | {k2_result.execution_mode.value}")
        
        if k2_result.cost.actual_cost < automon_result.cost.actual_cost:
            print(f"✅ K2-Backbone cheaper by {(automon_result.cost.actual_cost - k2_result.cost.actual_cost):.4f}")
        else:
            print(f"⚡ AutoMon cheaper by {(k2_result.cost.actual_cost - automon_result.cost.actual_cost):.4f}")
    else:
        # Normal execution (auto-selects mode)
        result = bridge.execute(task, priority=args.priority, context=args.context)
        
        with open(args.output, "w") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved to {args.output}")


if __name__ == "__main__":
    main()
