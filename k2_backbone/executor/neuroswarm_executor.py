from __future__ import annotations
"""
NeuroSwarm Executor Adapter for K2-Backbone

Runs routed TaskSpec subtasks through the dual-phase architecture:
Phase 1: GBrain validates plan (WHAT)
Phase 2: NecroSwarm executes (HOW)
"""

import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ExecutionPhase(str, Enum):
    PLAN = "plan"      # GBrain: validate WHAT
    EXECUTE = "execute"  # NecroSwarm: execute HOW
    VALIDATE = "validate"  # Post-execution: check success criteria


class SubtaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SubtaskResult:
    subtask_id: str
    status: SubtaskStatus
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: int = 0
    tokens_used: dict = field(default_factory=dict)
    model_used: str = ""

    def to_dict(self) -> dict:
        return {
            "subtask_id": self.subtask_id,
            "status": self.status.value,
            "output": self.output[:500] if len(self.output) > 500 else self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
        }


@dataclass
class ExecutionTrace:
    task_id: str
    phase: ExecutionPhase
    started_at: str
    completed_at: Optional[str] = None
    results: list[SubtaskResult] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "results": [r.to_dict() for r in self.results],
        }


class GBrainValidator:
    """
    Phase 1: Validate the plan before execution.
    Checks: dependency cycles, budget sanity, model availability.
    """

    def validate(self, routed_spec: dict) -> tuple[bool, list[str]]:
        """
        Returns: (is_valid, list_of_warnings)
        """
        warnings = []
        subtasks = routed_spec.get("subtasks", [])
        budget = routed_spec.get("budget", {}).get("max_usd", 10.0)
        routing_cost = routed_spec.get("routing", {}).get("total_estimated_cost_usd", 0)

        # Check 1: Dependency cycles
        ids = {s["id"] for s in subtasks}
        visited = set()
        rec_stack = set()

        def has_cycle(node_id: str, deps: list[str]) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for dep in deps:
                if dep not in ids:
                    warnings.append(f"Missing dependency: {dep}")
                    continue
                if dep not in visited:
                    dep_subtask = next((s for s in subtasks if s["id"] == dep), None)
                    if dep_subtask and has_cycle(dep, dep_subtask.get("dependencies", [])):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for s in subtasks:
            if has_cycle(s["id"], s.get("dependencies", [])):
                return False, ["Dependency cycle detected!"] + warnings

        # Check 2: Budget sanity
        if routing_cost > budget * 1.5:
            warnings.append(f"Estimated cost (${routing_cost:.2f}) exceeds budget (${budget:.2f}) by >50%")

        # Check 3: All subtasks have assigned models
        for s in subtasks:
            if "assigned_model" not in s:
                warnings.append(f"Subtask {s['id']} has no assigned model")

        # Check 4: Estimated tokens within model limits
        for s in subtasks:
            tokens = s.get("estimated_tokens", 0)
            if tokens > 200000:
                warnings.append(f"Subtask {s['id']} exceeds token limit ({tokens})")

        return len([w for w in warnings if "ERROR" in w.upper()]) == 0, warnings


class NecroSwarmExecutor:
    """
    Phase 2: Execute subtasks respecting dependencies.
    Parallelizes where dependencies allow.
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers

    def _topological_sort(self, subtasks: list[dict]) -> list[dict]:
        """Sort subtasks by dependency order."""
        ids = {s["id"]: s for s in subtasks}
        in_degree = {s["id"]: len(s.get("dependencies", [])) for s in subtasks}
        queue = [s for s in subtasks if in_degree[s["id"]] == 0]
        result = []

        while queue:
            # Sort by priority (lower estimated_tokens first = faster)
            queue.sort(key=lambda s: s.get("estimated_tokens", 999999))
            current = queue.pop(0)
            result.append(current)

            # Find subtasks that depend on current
            for s in subtasks:
                if current["id"] in s.get("dependencies", []):
                    in_degree[s["id"]] -= 1
                    if in_degree[s["id"]] == 0:
                        queue.append(s)

        if len(result) != len(subtasks):
            raise ValueError("Dependency cycle detected in subtasks")

        return result

    def _execute_subtask(self, subtask: dict) -> SubtaskResult:
        """
        Execute a single subtask.
        In production: this makes actual API calls.
        """
        import time
        start = time.time()

        # Mock execution — replace with actual model API call
        st_id = subtask["id"]
        model = subtask.get("assigned_model", "unknown")
        task_type = subtask.get("type", "unknown")
        tokens = subtask.get("estimated_tokens", 4096)

        # Simulate execution time based on token count
        import random
        exec_time = max(1.0, (tokens / 1000) * random.uniform(0.5, 2.0))
        time.sleep(min(exec_time, 0.1))  # Cap mock sleep

        # Simulate success/failure (95% success rate)
        success = random.random() > 0.05

        if success:
            return SubtaskResult(
                subtask_id=st_id,
                status=SubtaskStatus.COMPLETED,
                output=f"Completed {task_type} task using {model}. Output: [simulated]",
                execution_time_ms=int((time.time() - start) * 1000),
                tokens_used={"input": tokens // 2, "output": tokens // 2},
                model_used=model,
            )
        else:
            return SubtaskResult(
                subtask_id=st_id,
                status=SubtaskStatus.FAILED,
                error="Simulated execution failure",
                execution_time_ms=int((time.time() - start) * 1000),
                tokens_used={"input": tokens // 2, "output": 100},
                model_used=model,
            )

    def execute(self, routed_spec: dict) -> ExecutionTrace:
        """
        Execute all subtasks in dependency order.
        Parallelizes batches where possible.
        """
        task_id = routed_spec.get("task_id", "unknown")
        subtasks = routed_spec.get("subtasks", [])

        trace = ExecutionTrace(
            task_id=task_id,
            phase=ExecutionPhase.EXECUTE,
            started_at=datetime.now().isoformat(),
        )

        # Sort by dependencies
        sorted_subtasks = self._topological_sort(subtasks)

        # Execute in waves (all with same dependency depth run in parallel)
        completed_ids = set()
        remaining = list(sorted_subtasks)

        while remaining:
            # Find subtasks whose dependencies are all satisfied
            ready = [
                s for s in remaining
                if all(dep in completed_ids for dep in s.get("dependencies", []))
            ]

            if not ready:
                raise ValueError("Deadlock: no subtasks ready but remaining exist")

            # Execute ready batch in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {pool.submit(self._execute_subtask, s): s for s in ready}
                for future in futures:
                    result = future.result()
                    trace.results.append(result)
                    if result.status == SubtaskStatus.COMPLETED:
                        completed_ids.add(result.subtask_id)
                    elif result.status == SubtaskStatus.FAILED:
                        # Retry once with fallback model
                        subtask = futures[future]
                        fallback = next(
                            (s for s in subtasks if s["id"] == result.subtask_id),
                            None
                        )
                        if fallback:
                            fallback["assigned_model"] = "qwen"  # Cheapest fallback
                            retry_result = self._execute_subtask(fallback)
                            retry_result.subtask_id = result.subtask_id + "_retry"
                            trace.results.append(retry_result)
                            if retry_result.status == SubtaskStatus.COMPLETED:
                                completed_ids.add(result.subtask_id)

            # Remove executed from remaining
            for s in ready:
                remaining.remove(s)

        trace.completed_at = datetime.now().isoformat()
        trace.status = "completed" if all(
            r.status == SubtaskStatus.COMPLETED for r in trace.results
        ) else "partial_failure"

        return trace


class NeuroSwarmExecutor:
    """
    Dual-phase executor: GBrain validates, NecroSwarm executes.
    """

    def __init__(self, max_workers: int = 5):
        self.validator = GBrainValidator()
        self.executor = NecroSwarmExecutor(max_workers=max_workers)

    def run(self, routed_spec: dict) -> dict:
        """
        Full dual-phase execution.

        Returns: dict with validation, execution trace, and summary.
        """
        task_id = routed_spec.get("task_id", "unknown")

        # Phase 1: Validate
        is_valid, warnings = self.validator.validate(routed_spec)
        if not is_valid:
            return {
                "task_id": task_id,
                "status": "rejected",
                "phase": "validation",
                "errors": warnings,
            }

        # Phase 2: Execute
        trace = self.executor.execute(routed_spec)

        # Phase 3: Post-validation
        all_pass = all(r.status == SubtaskStatus.COMPLETED for r in trace.results)
        total_tokens = sum(
            r.tokens_used.get("input", 0) + r.tokens_used.get("output", 0)
            for r in trace.results
        )

        return {
            "task_id": task_id,
            "status": "completed" if all_pass else "partial_failure",
            "phase": "execution",
            "validation_warnings": warnings,
            "execution_trace": trace.to_dict(),
            "summary": {
                "total_subtasks": len(routed_spec.get("subtasks", [])),
                "completed": len([r for r in trace.results if r.status == SubtaskStatus.COMPLETED]),
                "failed": len([r for r in trace.results if r.status == SubtaskStatus.FAILED]),
                "total_tokens": total_tokens,
                "execution_time_ms": sum(r.execution_time_ms for r in trace.results),
            },
        }


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="NeuroSwarm Executor for K2-Backbone")
    parser.add_argument("--spec", type=Path, required=True, help="Routed TaskSpec JSON")
    parser.add_argument("--workers", type=int, default=5, help="Max parallel workers")
    parser.add_argument("--output", type=Path, default=Path("execution_result.json"))
    args = parser.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)

    executor = NeuroSwarmExecutor(max_workers=args.workers)
    result = executor.run(spec)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Execution complete: {result['status']}")
    print(f"   Subtasks: {result['summary']['total_subtasks']}")
    print(f"   Completed: {result['summary']['completed']}")
    print(f"   Failed: {result['summary']['failed']}")
    print(f"   Total tokens: {result['summary']['total_tokens']:,}")
    print(f"   Saved to: {args.output}")


if __name__ == "__main__":
    main()
