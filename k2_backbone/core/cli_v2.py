"""
K2-Backbone CLI v2: NeuroSwarm-Integrated Pipeline

Usage:
    # Full pipeline with NeuroSwarm execution
    k2v2 run "Build a REST API" --neuroswarm
    
    # Lightweight execution (no NeuroSwarm)
    k2v2 run "Build a REST API" --no-neuroswarm
    
    # With Obliviarch compression
    k2v2 run "Build a REST API" --obliviarch
"""

import json
from typing import Optional
import os
import sys
from pathlib import Path

from k2_backbone.decomposer.k2_decomposer import K2Decomposer
from k2_backbone.router.necroswarm_router import NecroSwarmRouter, VoteMethod
from k2_backbone.executor.neuroswarm_integration import NeuroSwarmIntegratedExecutor


class K2BackboneV2:
    """
    K2-Backbone v2: NeuroSwarm-Integrated Pipeline
    
    Pipeline:
      Ollama Cloud TaskSpec → NecroSwarmRouter (cost-optimized)
        → NeuroSwarmIntegratedExecutor (GBrain + Council)
        → ObliviarchAdapter (compression)
    """
    
    def __init__(
        self,
        ollama_key: Optional[str] = None,
        model: str = "deepseek-v4-flash",
        use_neuroswarm: bool = True,
        enable_obliviarch: bool = True,
    ):
        self.ollama_key = ollama_key or os.environ.get("OLLAMA_API_KEY")
        self.model = model
        self.use_neuroswarm = use_neuroswarm
        self.enable_obliviarch = enable_obliviarch
        
        self.decomposer = K2Decomposer(api_key=self.ollama_key, model=self.model)
        self.router = NecroSwarmRouter()
        self.executor = NeuroSwarmIntegratedExecutor(
            use_neuroswarm=use_neuroswarm,
            enable_obliviarch=enable_obliviarch,
        )
    
    def run(self, task: str, context: str = "") -> dict:
        """Full pipeline: decompose → route → execute (NeuroSwarm) → compress"""
        print(f"🎯 Task: {task[:80]}...")
        
        # Step 1: Decompose
        print(f"\n📐 Step 1: Decomposition ({self.model})...")
        spec = self.decomposer.decompose(task, context=context)
        print(f"   → {len(spec.subtasks)} subtasks")
        
        # Step 2: Route
        print("\n🗳️  Step 2: 10-D Council Voting...")
        spec_dict = spec.to_dict()
        routed = self.router.route(spec_dict)
        print(f"   → Budget: ${routed['routing']['total_estimated_cost_usd']}")
        
        # Step 3: Execute (NeuroSwarm-enhanced)
        mode = "NeuroSwarm" if self.use_neuroswarm else "Lightweight"
        print(f"\n⚙️  Step 3: Executing via {mode}...")
        result = self.executor.run(routed)
        print(f"   → Status: {result['status']}")
        
        # Step 4: Synthesis
        if result['status'] == 'completed':
            print("\n🧠 Step 4: Synthesizing...")
            synthesis = self.decomposer.synthesize(
                [{"subtask_id": r.get("subtask_id", ""), "output": r.get("output", "")} 
                 for r in result.get("execution_trace", {}).get("results", [])],
                task
            )
            result["synthesis"] = synthesis
        
        return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="K2-Backbone v2: NeuroSwarm-Integrated")
    parser.add_argument("task", nargs="+", help="Task description")
    parser.add_argument("--context", default="")
    parser.add_argument("--model", default="deepseek-v4-flash", help="Ollama Cloud model for decomposition")
    parser.add_argument("--neuroswarm", action="store_true", default=True, dest="neuroswarm")
    parser.add_argument("--no-neuroswarm", action="store_false", dest="neuroswarm")
    parser.add_argument("--obliviarch", action="store_true", default=True, dest="obliviarch")
    parser.add_argument("--no-obliviarch", action="store_false", dest="obliviarch")
    parser.add_argument("--output", type=Path, default=Path("k2v2_result.json"))
    args = parser.parse_args()
    
    task = " ".join(args.task)
    ollama_key = os.environ.get("OLLAMA_API_KEY")
    
    if not ollama_key:
        print("❌ Set OLLAMA_API_KEY")
        return 1
    
    backbone = K2BackboneV2(
        ollama_key=ollama_key,
        model=args.model,
        use_neuroswarm=args.neuroswarm,
        enable_obliviarch=args.obliviarch,
    )
    
    result = backbone.run(task, context=args.context)
    
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n💾 Saved to {args.output}")
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Status: {result['status']}")
    print(f"Mode: {result.get('mode', 'unknown')}")
    if result.get('neuroswarm'):
        ns = result['neuroswarm']
        print(f"NeuroSwarm Skill: {ns['phase1_what']['skill']}")
        print(f"Complexity: {ns['phase1_what']['complexity']}")
        print(f"Approach: {ns['phase2_how']['approach']}")
    if result.get('obliviarch_schema_id'):
        print(f"Obliviarch Schema: {result['obliviarch_schema_id']}")
    print(f"Cost: ${result.get('cost', {}).get('estimated', 0):.4f}")
    
    return 0


if __name__ == "__main__":
    from typing import Optional
    raise SystemExit(main())
