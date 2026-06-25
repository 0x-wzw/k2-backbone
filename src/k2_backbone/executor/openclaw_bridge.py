"""
OpenClaw Bridge — K2 Pipeline → Subagent Spawn Intents

This is the integration layer between K2-Backbone's Python pipeline and
OpenClaw's subagent spawning capability.

Flow:
  1. K2 pipeline runs (decompose → route) in Python
  2. This bridge outputs spawn intents as JSON
  3. The OpenClaw orchestrator reads the intents and calls sessions_spawn
  4. Results are collected and fed back into the pipeline

Usage (Python):
    from k2_backbone.executor.openclaw_bridge import OpenClawBridge
    
    bridge = OpenClawBridge()
    intents = bridge.prepare_spawns(routed_spec)
    # intents is a list of dicts, each ready for sessions_spawn

Usage (CLI):
    python -m k2_backbone.executor.openclaw_bridge \\
        --spec /tmp/routed.json \\
        --output /tmp/spawn_intents.json
"""

import json
import sys
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from k2_backbone.executor.openclaw_dispatcher import OpenClawSubagentDispatcher


class OpenClawBridge:
    """
    Bridge between K2-Backbone pipeline and OpenClaw subagent spawning.
    
    Takes a routed TaskSpec and produces structured spawn intents that
    the OpenClaw orchestrator can execute via sessions_spawn.
    """
    
    def __init__(
        self,
        default_model: str = "ollama/deepseek-v4-flash:cloud",
        max_concurrent: int = 4,
    ):
        self.dispatcher = OpenClawSubagentDispatcher(
            default_model=default_model,
            max_concurrent=max_concurrent,
        )
    
    def prepare_spawns(self, routed_spec: dict) -> list[dict]:
        """
        Convert a routed TaskSpec into spawn intents for OpenClaw.
        
        Each spawn intent is a dict with:
          - subtask_id: unique identifier
          - title: short description
          - prompt: full task prompt for the subagent
          - model: model override (ollama/<model>:cloud)
          - task_type: type of subtask
          - dependencies: list of subtask_ids this depends on
          - estimated_cost_usd: cost estimate
          - group: execution group (parallel within group, sequential across groups)
        
        Returns:
            List of spawn intents, ordered by dependency group
        """
        subtasks = routed_spec.get("subtasks", [])
        spawns = self.dispatcher._resolve_spawns(subtasks)
        groups = self.dispatcher._group_by_dependencies(spawns)
        
        intents = []
        for group_idx, group in enumerate(groups):
            for spawn in group:
                intent = self.dispatcher._spawn_subagent(spawn)
                intent["group"] = group_idx + 1
                intent["dependencies"] = spawn.dependencies
                intents.append(intent)
        
        return intents
    
    def prepare_plan(self, routed_spec: dict) -> dict:
        """Get a human-readable execution plan"""
        return self.dispatcher.get_routing_plan(routed_spec)
    
    def run_pipeline(
        self,
        task: str,
        context: str = "",
        model: str = "deepseek-v4-flash",
        output_dir: Optional[Path] = None,
    ) -> dict:
        """
        Run the full K2 pipeline and return spawn intents.
        
        This is the main entry point for the orchestrator.
        
        Args:
            task: Task description
            context: Optional context
            model: Model for decomposition
            output_dir: Optional directory to save intermediate files
        
        Returns:
            Dict with pipeline results and spawn intents
        """
        from k2_backbone.decomposer.k2_decomposer import K2Decomposer
        from k2_backbone.router.necroswarm_router import NecroSwarmRouter
        
        ollama_key = os.environ.get("OLLAMA_API_KEY")
        if not ollama_key:
            raise ValueError("OLLAMA_API_KEY not set")
        
        # Step 1: Decompose
        decomposer = K2Decomposer(api_key=ollama_key, model=model)
        spec = decomposer.decompose(task, context=context)
        
        # Step 2: Route
        router = NecroSwarmRouter()
        spec_dict = spec.to_dict()
        routed = router.route(spec_dict)
        
        # Step 3: Prepare spawn intents
        intents = self.prepare_spawns(routed)
        plan = self.prepare_plan(routed)
        
        result = {
            "task": task,
            "task_id": routed.get("task_id", "unknown"),
            "total_subtasks": len(intents),
            "total_cost_usd": plan["total_cost_usd"],
            "model_usage": plan["model_usage"],
            "groups": plan["groups"],
            "spawn_intents": intents,
            "timestamp": datetime.now().isoformat(),
        }
        
        # Save intermediate files if requested
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_dir / "task_spec.json", "w") as f:
                json.dump(spec_dict, f, indent=2, default=str)
            with open(output_dir / "routed_spec.json", "w") as f:
                json.dump(routed, f, indent=2, default=str)
            with open(output_dir / "spawn_intents.json", "w") as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"  Saved to {output_dir}/")
        
        return result


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw Bridge — K2 → Subagent Spawn Intents")
    sub = parser.add_subparsers(dest="command", required=True)
    
    # plan: show routing plan only
    plan_p = sub.add_parser("plan", help="Show routing plan from a routed spec")
    plan_p.add_argument("--spec", type=Path, required=True, help="Routed TaskSpec JSON")
    
    # prepare: convert routed spec to spawn intents
    prep_p = sub.add_parser("prepare", help="Convert routed spec to spawn intents")
    prep_p.add_argument("--spec", type=Path, required=True, help="Routed TaskSpec JSON")
    prep_p.add_argument("--output", type=Path, default=Path("spawn_intents.json"))
    
    # run: full pipeline
    run_p = sub.add_parser("run", help="Run full pipeline: decompose → route → spawn intents")
    run_p.add_argument("task", nargs="+", help="Task description")
    run_p.add_argument("--context", default="")
    run_p.add_argument("--model", default="deepseek-v4-flash")
    run_p.add_argument("--output-dir", type=Path, default=Path("k2_output"))
    
    args = parser.parse_args()
    bridge = OpenClawBridge()
    
    if args.command == "plan":
        with open(args.spec) as f:
            spec = json.load(f)
        plan = bridge.prepare_plan(spec)
        print(json.dumps(plan, indent=2))
    
    elif args.command == "prepare":
        with open(args.spec) as f:
            spec = json.load(f)
        intents = bridge.prepare_spawns(spec)
        with open(args.output, "w") as f:
            json.dump(intents, f, indent=2, default=str)
        print(f"✅ {len(intents)} spawn intents saved to {args.output}")
    
    elif args.command == "run":
        task = " ".join(args.task)
        result = bridge.run_pipeline(
            task=task,
            context=args.context,
            model=args.model,
            output_dir=args.output_dir,
        )
        print(f"\n{'='*60}")
        print(f"PIPELINE COMPLETE")
        print(f"{'='*60}")
        print(f"Task: {result['task'][:80]}")
        print(f"Subtask count: {result['total_subtasks']}")
        print(f"Total cost: ${result['total_cost_usd']:.4f}")
        print(f"Models used: {len(result['model_usage'])}")
        for model, count in sorted(result['model_usage'].items(), key=lambda x: -x[1]):
            print(f"  {model}: {count}x")
        print(f"\nSpawn intents ready for execution.")
        print(f"  → {args.output_dir / 'spawn_intents.json'}")


if __name__ == "__main__":
    main()
