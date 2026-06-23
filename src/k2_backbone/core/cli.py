from __future__ import annotations
"""
End-to-end pipeline: Decompose → Route → Execute

Usage:
    python -m k2_backbone.cli "Your complex task here"
"""

import json
import os
from pathlib import Path
from typing import Optional

# Add frameworks to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "frameworks"))

from k2_backbone.decomposer.k2_decomposer import K2Decomposer, TaskSpec
from k2_backbone.router.necroswarm_router import NecroSwarmRouter, VoteMethod
from k2_backbone.executor.neuroswarm_executor import NeuroSwarmExecutor


class K2Backbone:
    """
    Unified interface: one call from task to result.
    """

    def __init__(
        self,
        ollama_key: Optional[str] = None,
        model: str = "deepseek-v4-flash",
        vote_method: VoteMethod = VoteMethod.BORDA,
        max_workers: int = 5,
    ):
        self.ollama_key = ollama_key or os.environ.get("OLLAMA_API_KEY")
        self.model = model
        self.vote_method = vote_method
        self.max_workers = max_workers

        self.decomposer = K2Decomposer(api_key=self.ollama_key, model=self.model)
        self.router = NecroSwarmRouter(vote_method=vote_method)
        self.executor = NeuroSwarmExecutor(max_workers=max_workers)

    def run(self, task: str, context: str = "") -> dict:
        """
        Full pipeline: task → TaskSpec → routed → executed.
        """
        print(f"🎯 Task: {task[:80]}...")

        # Step 1: Decompose
        print(f"\n📐 Step 1: Decomposing with {self.model}...")
        spec = self.decomposer.decompose(task, context=context)
        print(f"   → {len(spec.subtasks)} subtasks identified")

        # Step 2: Route
        print("\n🗳️  Step 2: Routing through 10-D Council...")
        spec_dict = spec.to_dict()
        routed = self.router.route(spec_dict)
        print(f"   → Budget: ${routed['routing']['total_estimated_cost_usd']}")
        print(f"   → Strategy: {routed['routing']['method']}")

        # Step 3: Execute
        print("\n⚙️  Step 3: Executing via NeuroSwarm...")
        result = self.executor.run(routed)
        print(f"   → Status: {result['status']}")
        print(f"   → Completed: {result['summary']['completed']}/{result['summary']['total_subtasks']}")

        # Step 4: Synthesis (optional)
        if result['status'] == 'completed':
            print("\n🧠 Step 4: Synthesizing final output...")
            synthesis = self.decomposer.synthesize(
                [{"subtask_id": r["subtask_id"], "output": r["output"]} for r in result["execution_trace"]["results"]],
                task
            )
            result["synthesis"] = synthesis
        else:
            result["synthesis"] = "Execution had failures. Review execution_trace for details."

        return result

    def save(self, result: dict, path: Path) -> None:
        """Save full result to JSON."""
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\n💾 Saved to {path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="K2-Backbone: Ollama Cloud Pipeline")
    parser.add_argument("task", nargs="+", help="Task description")
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--model", default="deepseek-v4-flash", help="Ollama Cloud model for decomposition")
    parser.add_argument("--method", choices=["borda", "cost_first", "quality_first"], default="borda")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("k2_result.json"))
    parser.add_argument("--save-spec", action="store_true", help="Also save intermediate TaskSpec")
    args = parser.parse_args()

    task = " ".join(args.task)
    ollama_key = os.environ.get("OLLAMA_API_KEY")

    if not ollama_key:
        print("❌ Set OLLAMA_API_KEY environment variable")
        return 1

    backbone = K2Backbone(
        ollama_key=ollama_key,
        model=args.model,
        vote_method=VoteMethod(args.method),
        max_workers=args.workers,
    )

    result = backbone.run(task, context=args.context)
    backbone.save(result, args.output)

    print("\n" + "=" * 50)
    print("Done!")
    print(f"Result: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
