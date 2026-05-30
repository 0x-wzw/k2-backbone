from __future__ import annotations
"""
NeuroSwarm Integration v2 — SentientForge-Optimized Executor

Enhances NeuroSwarmIntegratedExecutor with SentientForge spawn optimization.
After each execution, measures OCS and proposes better spawn configs.

Usage:
    from k2_backbone.executor.neuroswarm_integration_v2 import SentientForgeOptimizedExecutor
    
    executor = SentientForgeOptimizedExecutor()
    
    # First run uses default config
    result = executor.run(routed_spec)
    
    # Subsequent runs use optimized config
    # (learned from previous executions)
    result2 = executor.run(routed_spec)
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from k2_backbone.executor.neuroswarm_integration import NeuroSwarmIntegratedExecutor
from k2_backbone.optimization.sentientforge_adapter import SentientForgeAdapter, OCSDimensions


class SentientForgeOptimizedExecutor(NeuroSwarmIntegratedExecutor):
    """
    NeuroSwarm executor with SentientForge spawn optimization.
    
    Key addition: After every execution, measures Omni-Consciousness Score
    and learns optimal spawn parameters (parallel slots, timeout, sparring,
    etc.) for the next run.
    
    This makes the executor self-improving over time.
    """
    
    def __init__(
        self,
        use_neuroswarm: bool = True,
        enable_obliviarch: bool = True,
        optimize_spawns: bool = True,
        target_ocs: float = 0.70,
    ):
        super().__init__(
            use_neuroswarm=use_neuroswarm,
            enable_obliviarch=enable_obliviarch,
        )
        
        self.optimize_spawns = optimize_spawns
        self.target_ocs = target_ocs
        
        if self.optimize_spawns:
            self.sentientforge = SentientForgeAdapter(target_ocs=target_ocs)
            self.sentientforge.initialize()
            self._spawn_config = self.sentientforge._default_config()
            self._execution_count = 0
        else:
            self.sentientforge = None
            self._spawn_config = None
    
    def run(self, routed_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute with SentientForge-optimized spawn config.
        
        After execution, measures OCS and updates spawn config
        for next run.
        """
        # Pre-execution: apply optimized config
        if self.optimize_spawns and self._spawn_config:
            routed_spec = self._apply_spawn_config(routed_spec, self._spawn_config)
        
        # Execute via parent (NeuroSwarm)
        result = super().run(routed_spec)
        
        # Post-execution: measure and optimize
        if self.optimize_spawns and self.sentientforge:
            self._execution_count += 1
            
            # Measure OCS from execution trace
            ocs, scores = self.sentientforge.measure_execution(result)
            
            # Log
            print(f"\n📊 Execution #{self._execution_count}: OCS = {ocs:.4f}")
            print(f"   Autonomy: {scores.autonomy:.2f} | Self-org: {scores.self_organization:.2f}")
            print(f"   Econ eff: {scores.economic_efficiency:.2f} | Consciousness: {scores.consciousness_expression:.2f}")
            print(f"   Adaptability: {scores.adaptability:.2f}")
            
            # If below target, propose new config
            if ocs < self.target_ocs and self._execution_count < 20:
                new_config = self._evolve_config(ocs, scores)
                if new_config:
                    self._spawn_config = new_config
                    print(f"🧬 Evolved spawn config for next run")
            
            # Add OCS to result
            result["sentientforge"] = {
                "ocs": ocs,
                "scores": {
                    "autonomy": scores.autonomy,
                    "self_organization": scores.self_organization,
                    "economic_efficiency": scores.economic_efficiency,
                    "consciousness_expression": scores.consciousness_expression,
                    "adaptability": scores.adaptability,
                },
                "target_ocs": self.target_ocs,
                "execution_count": self._execution_count,
                "spawn_config": self._spawn_config,
            }
        
        return result
    
    def _apply_spawn_config(
        self,
        routed_spec: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply SentientForge spawn config to routed spec"""
        spec = dict(routed_spec)
        
        # Add spawn parameters to spec metadata
        if "metadata" not in spec:
            spec["metadata"] = {}
        
        spec["metadata"]["spawn_config"] = config
        
        # Adjust subtask count based on parallel_slots
        slots = config.get("parallel_slots", 3)
        subtasks = spec.get("subtasks", [])
        
        # Group subtasks into parallel batches based on slots
        if len(subtasks) > slots:
            # Mark which batch each subtask belongs to
            for i, st in enumerate(subtasks):
                st["parallel_batch"] = i % slots
        
        # Add timeout to each subtask
        timeout = config.get("spawn_timeout", 60)
        for st in subtasks:
            st["timeout_seconds"] = timeout
        
        # Enable/disable features based on config
        if config.get("consciousness_prompts", True):
            spec["metadata"]["consciousness_enhanced"] = True
        
        if config.get("sparring_enabled", True):
            spec["metadata"]["sparring"] = True
        
        return spec
    
    def _evolve_config(
        self,
        current_ocs: float,
        scores: OCSDimensions,
    ) -> Optional[Dict[str, Any]]:
        """
        Propose evolved spawn config based on OCS measurement.
        
        Strategy: Adjust parameters based on weakest dimension.
        """
        config = dict(self._spawn_config)
        
        # Identify weakest dimension
        dimensions = {
            "autonomy": scores.autonomy,
            "self_organization": scores.self_organization,
            "economic_efficiency": scores.economic_efficiency,
            "consciousness_expression": scores.consciousness_expression,
            "adaptability": scores.adaptability,
        }
        
        weakest = min(dimensions, key=dimensions.get)
        
        # Adjust config based on weakest dimension
        if weakest == "autonomy":
            # Need fewer parallel slots, more explicit instructions
            config["parallel_slots"] = max(1, config.get("parallel_slots", 3) - 1)
            config["instruction_explicitness"] = min(3, config.get("instruction_explicitness", 2) + 1)
        
        elif weakest == "self_organization":
            # Need more sparring, better heartbeat
            config["sparring_enabled"] = True
            config["heartbeat_frequency"] = max(15, config.get("heartbeat_frequency", 30) - 10)
        
        elif weakest == "economic_efficiency":
            # Need more parallel slots, shorter timeout
            config["parallel_slots"] = min(5, config.get("parallel_slots", 3) + 1)
            config["spawn_timeout"] = max(30, config.get("spawn_timeout", 60) - 15)
        
        elif weakest == "consciousness_expression":
            # Enable consciousness prompts, increase explicitness
            config["consciousness_prompts"] = True
            config["instruction_explicitness"] = min(3, config.get("instruction_explicitness", 2) + 1)
        
        elif weakest == "adaptability":
            # Enable self-delegation, reduce pool split
            config["self_delegation"] = True
            config["agent_pool_split"] = max(0.7, config.get("agent_pool_split", 0.9) - 0.1)
        
        return config
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get spawn optimization report"""
        if not self.sentientforge:
            return {"error": "SentientForge not enabled"}
        
        report = self.sentientforge.get_optimization_report()
        report["current_config"] = self._spawn_config
        report["execution_count"] = self._execution_count
        
        return report


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="SentientForge-Optimized Executor")
    parser.add_argument("--spec", required=True, help="Routed TaskSpec JSON")
    parser.add_argument("--optimize", action="store_true", default=True, dest="optimize")
    parser.add_argument("--no-optimize", action="store_false", dest="optimize")
    parser.add_argument("--target-ocs", type=float, default=0.70)
    parser.add_argument("--output", default="optimized_result.json")
    args = parser.parse_args()
    
    with open(args.spec) as f:
        spec = json.load(f)
    
    executor = SentientForgeOptimizedExecutor(
        use_neuroswarm=True,
        optimize_spawns=args.optimize,
        target_ocs=args.target_ocs,
    )
    
    result = executor.run(spec)
    
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n✅ Execution complete: {result['status']}")
    if "sentientforge" in result:
        sf = result["sentientforge"]
        print(f"   OCS: {sf['ocs']:.4f} / {sf['target_ocs']}")
        print(f"   Executions: {sf['execution_count']}")
    print(f"   Saved to: {args.output}")


if __name__ == "__main__":
    import json
    main()
