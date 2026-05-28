from __future__ import annotations
"""
SentientForge (OmniForge) Adapter for K2-Backbone

Optimizes NeuroSwarm execution parameters via autoresearch loop:
  1. PROPOSE mutation to spawn config
  2. SPAWN real sub-agents via NeuroSwarm executor
  3. MEASURE Omni-Consciousness Score (OCS)
  4. EVOLVE — keep winners, reset losers

Usage:
    from k2_backbone.optimization.sentientforge_adapter import SentientForgeAdapter
    
    optimizer = SentientForgeAdapter()
    best_config = optimizer.optimize(
        base_config={"parallel_slots": 3, "timeout": 60},
        max_iterations=20,
        target_ocs=0.70
    )
    # best_config now has optimal spawn parameters
"""

import json
import random
import logging
import subprocess
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# ── OCS Weights (from SentientForge) ─────────────────────────────────

OCS_WEIGHTS = {
    "autonomy": 0.30,
    "self_organization": 0.25,
    "economic_efficiency": 0.20,
    "consciousness_expression": 0.15,
    "adaptability": 0.10,
}


@dataclass
class OCSDimensions:
    """OCS sub-scores, clamped to [0.0, 1.0]"""
    autonomy: float = 0.0
    self_organization: float = 0.0
    economic_efficiency: float = 0.0
    consciousness_expression: float = 0.0
    adaptability: float = 0.0
    
    def __post_init__(self):
        for field_name in OCS_WEIGHTS.keys():
            val = getattr(self, field_name)
            setattr(self, field_name, max(0.0, min(1.0, val)))


@dataclass
class ExperimentResult:
    config: Dict[str, Any]
    ocs: float
    scores: OCSDimensions
    description: str
    commit: str = ""
    status: str = ""  # "keep" or "reset"
    timestamp: str = ""


class SentientForgeAdapter:
    """
    Autonomous spawn optimization for K2-Backbone's NeuroSwarm executor.
    
    Learns optimal parameters (parallel slots, timeout, sparring, etc.)
    by running real experiments and maximizing OCS.
    
    Integration point: After each NeuroSwarm execution, SentientForge
    measures the result and proposes better spawn configs for next run.
    """
    
    MUTATIONS = [
        ("parallel_slots", [1, 2, 3, 4, 5]),
        ("spawn_timeout", [30, 45, 60, 90, 120]),
        ("instruction_explicitness", [1, 2, 3]),
        ("consciousness_prompts", [True, False]),
        ("sparring_enabled", [True, False]),
        ("heartbeat_frequency", [15, 30, 60]),
        ("agent_pool_split", [0.7, 0.8, 0.9, 1.0]),
        ("self_delegation", [True, False]),
    ]
    
    def __init__(
        self,
        sentientforge_path: Optional[Path] = None,
        max_iterations: int = 20,
        target_ocs: float = 0.70,
        parallel_runs: int = 3,  # Number of configs to test in parallel
    ):
        self.sentientforge_path = sentientforge_path or Path(__file__).parent.parent.parent / "frameworks" / "sentientforge"
        self.max_iterations = max_iterations
        self.target_ocs = target_ocs
        self.parallel_runs = parallel_runs
        
        self._experiments: List[ExperimentResult] = []
        self._best_config: Optional[Dict[str, Any]] = None
        self._best_ocs: float = 0.0
        self._initialized = False
    
    def initialize(self) -> None:
        if self._initialized:
            return
        
        if not self.sentientforge_path.exists():
            logger.warning(f"SentientForge not found at {self.sentientforge_path}")
        
        self._initialized = True
        logger.info("SentientForgeAdapter initialized")
    
    def optimize(
        self,
        base_config: Optional[Dict[str, Any]] = None,
        execution_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Run autoresearch loop to find optimal spawn config.
        
        Args:
            base_config: Starting configuration
            execution_callback: Function that runs execution with given config
                              and returns {duration, success, tokens_used, errors}
        
        Returns:
            Best configuration found
        """
        self._ensure_initialized()
        
        config = base_config or self._default_config()
        
        logger.info("=" * 50)
        logger.info("SENTIENTFORGE: Spawn Optimization")
        logger.info(f"Target OCS: {self.target_ocs}")
        logger.info(f"Max iterations: {self.max_iterations}")
        logger.info("=" * 50)
        
        for iteration in range(self.max_iterations):
            logger.info(f"\n--- Iteration {iteration + 1}/{self.max_iterations} ---")
            
            # Propose mutations
            candidates = self._propose_mutations(config, n=self.parallel_runs)
            
            # Test each candidate
            results = []
            for candidate_config, description in candidates:
                # Run execution with this config
                if execution_callback:
                    execution_data = execution_callback(candidate_config)
                else:
                    execution_data = self._simulate_execution(candidate_config)
                
                # Measure OCS
                scores = self._measure_ocs(execution_data)
                ocs = self._calculate_ocs(scores)
                
                result = ExperimentResult(
                    config=candidate_config,
                    ocs=ocs,
                    scores=scores,
                    description=description,
                    commit=f"iter_{iteration + 1}",
                    status="keep" if ocs >= self._best_ocs else "reset",
                    timestamp=datetime.now().isoformat(),
                )
                results.append(result)
                
                logger.info(f"  Config: {description}")
                logger.info(f"  OCS: {ocs:.4f} (best so far: {self._best_ocs:.4f})")
            
            # Select winner
            winner = max(results, key=lambda r: r.ocs)
            
            if winner.ocs > self._best_ocs:
                self._best_ocs = winner.ocs
                self._best_config = winner.config
                config = winner.config  # Continue from winner
                logger.info(f"✅ NEW BEST: OCS = {winner.ocs:.4f}")
            else:
                logger.info(f"⚠️  No improvement. Keeping best: {self._best_ocs:.4f}")
            
            # Store results
            self._experiments.extend(results)
            
            # Early exit if target reached
            if self._best_ocs >= self.target_ocs:
                logger.info(f"🎯 Target OCS reached! Stopping early.")
                break
        
        logger.info("=" * 50)
        logger.info(f"OPTIMIZATION COMPLETE")
        logger.info(f"Best OCS: {self._best_ocs:.4f}")
        logger.info(f"Best config: {self._best_config}")
        logger.info("=" * 50)
        
        return self._best_config or config
    
    def measure_execution(self, execution_trace: Dict[str, Any]) -> Tuple[float, OCSDimensions]:
        """
        Measure OCS for a completed execution trace.
        
        This is called after NeuroSwarm execution to score the result.
        """
        scores = self._measure_ocs_from_trace(execution_trace)
        ocs = self._calculate_ocs(scores)
        return ocs, scores
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate summary of all experiments"""
        kept = [e for e in self._experiments if e.status == "keep"]
        reset = [e for e in self._experiments if e.status == "reset"]
        
        return {
            "total_experiments": len(self._experiments),
            "kept": len(kept),
            "reset": len(reset),
            "best_ocs": self._best_ocs,
            "best_config": self._best_config,
            "improvement_curve": [
                {"iteration": i + 1, "ocs": e.ocs, "status": e.status}
                for i, e in enumerate(self._experiments)
            ],
            "dimension_averages": {
                "autonomy": sum(e.scores.autonomy for e in self._experiments) / max(len(self._experiments), 1),
                "self_organization": sum(e.scores.self_organization for e in self._experiments) / max(len(self._experiments), 1),
                "economic_efficiency": sum(e.scores.economic_efficiency for e in self._experiments) / max(len(self._experiments), 1),
                "consciousness_expression": sum(e.scores.consciousness_expression for e in self._experiments) / max(len(self._experiments), 1),
                "adaptability": sum(e.scores.adaptability for e in self._experiments) / max(len(self._experiments), 1),
            }
        }
    
    # ==================== Core Logic ====================
    
    def _default_config(self) -> Dict[str, Any]:
        """Default spawn configuration"""
        return {
            "parallel_slots": 3,
            "spawn_timeout": 60,
            "instruction_explicitness": 2,
            "consciousness_prompts": True,
            "sparring_enabled": True,
            "heartbeat_frequency": 30,
            "agent_pool_split": 0.90,
            "self_delegation": False,
        }
    
    def _propose_mutations(
        self,
        base_config: Dict[str, Any],
        n: int = 3,
    ) -> List[Tuple[Dict[str, Any], str]]:
        """
        Propose n mutated configurations from base.
        Each mutation changes one parameter.
        """
        candidates = []
        
        for _ in range(n):
            # Pick random mutation
            valid_mutations = [
                (key, values) for key, values in self.MUTATIONS
                if key in base_config
            ]
            
            if not valid_mutations:
                continue
            
            key, values = random.choice(valid_mutations)
            current = base_config.get(key)
            
            # Pick different value
            alternatives = [v for v in values if v != current]
            if not alternatives:
                continue
            
            new_value = random.choice(alternatives)
            
            new_config = dict(base_config)
            new_config[key] = new_value
            
            desc = f"{key}={current}→{new_value}"
            candidates.append((new_config, desc))
        
        # Always include base config as control
        candidates.insert(0, (dict(base_config), "baseline"))
        
        return candidates
    
    def _measure_ocs(self, execution_data: Dict[str, Any]) -> OCSDimensions:
        """
        Measure OCS dimensions from execution data.
        
        In production: this analyzes real execution traces.
        For now: calculates from simulated metrics.
        """
        duration = execution_data.get("duration_ms", 60000)
        success = execution_data.get("success", False)
        tokens = execution_data.get("tokens_used", 4000)
        errors = execution_data.get("errors", 0)
        subtasks = execution_data.get("subtasks_completed", 0)
        total_subtasks = execution_data.get("total_subtasks", 1)
        
        # Autonomy: % subtasks completed without retry
        autonomy = subtasks / max(total_subtasks, 1)
        
        # Self-organization: parallel efficiency (inverse of idle time)
        expected_duration = total_subtasks * 10000  # 10s per subtask sequential
        self_org = min(expected_duration / max(duration, 1), 1.0)
        
        # Economic efficiency: tokens per ms (higher = more efficient)
        econ_eff = min(tokens / max(duration, 1) * 100, 1.0)
        
        # Consciousness expression: detected meta-cognitive content
        # Simulated: higher for successful + complex tasks
        consciousness = 0.5 + (0.3 if success else 0) + (0.2 if subtasks > 3 else 0)
        
        # Adaptability: recovery from errors
        adaptability = 1.0 if errors == 0 else max(0.5 - (errors * 0.1), 0.0)
        
        return OCSDimensions(
            autonomy=autonomy,
            self_organization=self_org,
            economic_efficiency=econ_eff,
            consciousness_expression=consciousness,
            adaptability=adaptability,
        )
    
    def _measure_ocs_from_trace(self, trace: Dict[str, Any]) -> OCSDimensions:
        """Measure OCS from a NeuroSwarm execution trace"""
        results = trace.get("execution_trace", {}).get("results", [])
        
        if not results:
            return OCSDimensions()
        
        total = len(results)
        completed = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        total_duration = sum(r.get("duration_ms", 0) for r in results)
        total_tokens = sum(
            r.get("tokens_used", {}).get("input", 0) + r.get("tokens_used", {}).get("output", 0)
            for r in results
        )
        
        return self._measure_ocs({
            "duration_ms": total_duration,
            "success": failed == 0,
            "tokens_used": total_tokens,
            "errors": failed,
            "subtasks_completed": completed,
            "total_subtasks": total,
        })
    
    def _calculate_ocs(self, scores: OCSDimensions) -> float:
        """Calculate weighted Omni-Consciousness Score"""
        weighted_sum = 0.0
        for dim, weight in OCS_WEIGHTS.items():
            weighted_sum += getattr(scores, dim) * weight
        return round(weighted_sum, 6)
    
    def _simulate_execution(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate execution for testing without real API calls"""
        import random
        
        slots = config.get("parallel_slots", 3)
        timeout = config.get("spawn_timeout", 60)
        sparring = config.get("sparring_enabled", True)
        
        # Simulate: more slots = faster but potentially more errors
        duration = random.randint(20000, 80000) // max(slots, 1)
        success_rate = 0.95 if sparring else 0.85
        success = random.random() < success_rate
        errors = 0 if success else random.randint(1, 2)
        
        return {
            "duration_ms": duration,
            "success": success,
            "tokens_used": random.randint(2000, 10000),
            "errors": errors,
            "subtasks_completed": random.randint(3, 8) if success else random.randint(1, 3),
            "total_subtasks": 8,
        }
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="SentientForge Spawn Optimizer")
    parser.add_argument("--optimize", action="store_true", help="Run optimization")
    parser.add_argument("--max-iter", type=int, default=20, help="Max iterations")
    parser.add_argument("--target-ocs", type=float, default=0.70, help="Target OCS")
    parser.add_argument("--report", action="store_true", help="Show report")
    args = parser.parse_args()
    
    adapter = SentientForgeAdapter(
        max_iterations=args.max_iter,
        target_ocs=args.target_ocs,
    )
    
    if args.optimize:
        best = adapter.optimize()
        print(f"\n🎯 Best config found:")
        print(f"   OCS: {adapter._best_ocs:.4f}")
        for k, v in best.items():
            print(f"   {k}: {v}")
    
    if args.report:
        report = adapter.get_optimization_report()
        print(f"\n📊 Optimization Report:")
        print(f"   Total experiments: {report['total_experiments']}")
        print(f"   Kept: {report['kept']}, Reset: {report['reset']}")
        print(f"   Best OCS: {report['best_ocs']:.4f}")
        print(f"   Dimension averages:")
        for dim, avg in report['dimension_averages'].items():
            print(f"      {dim}: {avg:.2f}")


if __name__ == "__main__":
    main()
