"""
OpenClaw Subagent Dispatcher — Bridges 10-D Council Routing to Subagent Spawns

Reads a routed TaskSpec (with assigned_model per subtask) and spawns
OpenClaw subagents with the correct model override.

Usage:
    from k2_backbone.executor.openclaw_dispatcher import OpenClawSubagentDispatcher
    
    dispatcher = OpenClawSubagentDispatcher()
    result = dispatcher.dispatch(routed_spec)
    
This is the bridge between:
  - model-routing-table (10-D Council, cost optimization)
  - OpenClaw sessions_spawn (model parameter for per-subagent routing)
"""

import json
import os
import sys
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Import the 10-D routing table for model lookups
from model_routing_table.table import (
    DIMENSION_MAP,
    DIMENSION_FALLBACK,
    MODEL_COST_USD,
    CAPABILITY_MATRIX,
    TASK_ROUTING,
)


@dataclass
class SubagentSpawn:
    """Represents a subagent to be spawned with model routing"""
    subtask_id: str
    title: str
    description: str
    task_type: str
    assigned_model: str
    dependencies: list[str]
    estimated_tokens: int
    success_criteria: str
    spawn_id: Optional[str] = None
    status: str = "pending"
    error: Optional[str] = None


@dataclass
class DispatchResult:
    """Result from dispatching subtasks to subagents"""
    task_id: str
    status: str
    total_subtasks: int
    completed: int
    failed: int
    spawns: list[dict]
    model_usage: dict  # model_name -> count
    total_cost_usd: float
    duration_ms: int
    errors: list[str]


class OpenClawSubagentDispatcher:
    """
    Dispatches routed subtasks to OpenClaw subagents with model overrides.
    
    The 10-D Council (via NecroSwarmRouter) assigns the optimal model per
    subtask. This dispatcher reads those assignments and spawns subagents
    with the correct model parameter.
    
    Model ref format: ollama/<model>:cloud
    Example: ollama/glm-5.2:cloud, ollama/qwen3.5:122b:cloud
    """
    
    def __init__(
        self,
        default_model: str = "ollama/deepseek-v4-flash:cloud",
        max_concurrent: int = 4,
        spawn_timeout_seconds: int = 300,
    ):
        self.default_model = default_model
        self.max_concurrent = max_concurrent
        self.spawn_timeout_seconds = spawn_timeout_seconds
    
    def dispatch(self, routed_spec: dict) -> dict:
        """
        Dispatch all subtasks in a routed TaskSpec to OpenClaw subagents.
        
        Args:
            routed_spec: TaskSpec with assigned_model per subtask
                         (output of NecroSwarmRouter.route())
        
        Returns:
            DispatchResult with spawn status and model usage stats
        """
        start = time.time()
        task_id = routed_spec.get("task_id", "unknown")
        subtasks = routed_spec.get("subtasks", [])
        
        logger.info(f"Dispatching {len(subtasks)} subtasks for {task_id}")
        
        # Phase 1: Resolve model assignments
        spawns = self._resolve_spawns(subtasks)
        
        # Phase 2: Group by dependency depth
        groups = self._group_by_dependencies(spawns)
        
        # Phase 3: Execute groups sequentially, spawns within group in parallel
        completed = 0
        failed = 0
        errors = []
        all_results = []
        
        for group_idx, group in enumerate(groups):
            logger.info(f"  Group {group_idx + 1}/{len(groups)}: {len(group)} subtasks")
            
            for spawn in group:
                result = self._spawn_subagent(spawn)
                all_results.append(result)
                
                if result.get("status") == "completed":
                    completed += 1
                else:
                    failed += 1
                    if result.get("error"):
                        errors.append(result["error"])
        
        # Phase 4: Calculate stats
        duration_ms = int((time.time() - start) * 1000)
        model_usage = self._count_model_usage(spawns)
        total_cost = self._calculate_total_cost(spawns)
        
        return {
            "task_id": task_id,
            "status": "completed" if failed == 0 else "partial_failure",
            "total_subtasks": len(subtasks),
            "completed": completed,
            "failed": failed,
            "spawns": all_results,
            "model_usage": model_usage,
            "total_cost_usd": round(total_cost, 4),
            "duration_ms": duration_ms,
            "errors": errors,
            "dispatcher": "openclaw_subagent",
            "timestamp": datetime.now().isoformat(),
        }
    
    def _resolve_spawns(self, subtasks: list[dict]) -> list[SubagentSpawn]:
        """Build spawn list with model assignments, resolving fallbacks"""
        spawns = []
        
        for st in subtasks:
            model = st.get("assigned_model", "")
            
            # If no model assigned, use default
            if not model:
                model = self.default_model
            
            # Ensure model has ollama/ prefix for OpenClaw
            if not model.startswith("ollama/"):
                model = f"ollama/{model}"
            
            spawns.append(SubagentSpawn(
                subtask_id=st.get("id", "unknown"),
                title=st.get("title", ""),
                description=st.get("description", ""),
                task_type=st.get("type", "general"),
                assigned_model=model,
                dependencies=st.get("dependencies", []),
                estimated_tokens=st.get("estimated_tokens", 4096),
                success_criteria=st.get("success_criteria", ""),
            ))
        
        return spawns
    
    def _spawn_subagent(self, spawn: SubagentSpawn) -> dict:
        """
        Prepare a subagent spawn intent with model override.
        
        Returns a structured spawn intent that the orchestrator
        executes via sessions_spawn(task=..., model=...).
        """
        # Build the task prompt for this subtask
        task_prompt = self._build_subtask_prompt(spawn)
        
        return {
            "subtask_id": spawn.subtask_id,
            "title": spawn.title,
            "assigned_model": spawn.assigned_model,
            "task_type": spawn.task_type,
            "status": "ready",
            "prompt": task_prompt,
            "estimated_cost_usd": self._estimate_subtask_cost(spawn),
            "error": None,
        }
    
    def _build_subtask_prompt(self, spawn: SubagentSpawn) -> str:
        """Build the task prompt for a subagent"""
        parts = [
            f"## Task: {spawn.title}",
            f"",
            f"{spawn.description}",
            f"",
            f"**Success criteria:** {spawn.success_criteria}",
            f"**Type:** {spawn.task_type}",
        ]
        
        if spawn.dependencies:
            parts.append(f"**Depends on:** {', '.join(spawn.dependencies)}")
        
        parts.append("")
        parts.append("Complete this task and report your results.")
        
        return "\n".join(parts)
    
    def _group_by_dependencies(self, spawns: list[SubagentSpawn]) -> list[list[SubagentSpawn]]:
        """Group spawns by dependency depth for sequential group execution"""
        if not spawns:
            return []
        
        ids = {s.subtask_id: s for s in spawns}
        in_degree = {s.subtask_id: len(s.dependencies) for s in spawns}
        dependents = {s.subtask_id: [] for s in spawns}
        
        for s in spawns:
            for dep in s.dependencies:
                if dep in dependents:
                    dependents[dep].append(s.subtask_id)
        
        groups = []
        ready = [sid for sid, deg in in_degree.items() if deg == 0]
        completed = set()
        
        while ready:
            group = [ids[sid] for sid in ready]
            groups.append(group)
            
            next_ready = []
            for sid in ready:
                completed.add(sid)
                for dep_id in dependents[sid]:
                    in_degree[dep_id] -= 1
                    if in_degree[dep_id] == 0:
                        next_ready.append(dep_id)
            
            ready = next_ready
        
        return groups
    
    def _count_model_usage(self, spawns: list[SubagentSpawn]) -> dict:
        """Count how many times each model is used"""
        usage = {}
        for s in spawns:
            model = s.assigned_model
            usage[model] = usage.get(model, 0) + 1
        return usage
    
    def _calculate_total_cost(self, spawns: list[SubagentSpawn]) -> float:
        """Calculate total estimated cost for all spawns"""
        total = 0.0
        for s in spawns:
            total += self._estimate_subtask_cost(s)
        return total
    
    def _estimate_subtask_cost(self, spawn: SubagentSpawn) -> float:
        """Estimate cost for a single subtask"""
        # Extract model name from ollama/<model>:cloud format
        model_name = spawn.assigned_model.replace("ollama/", "")
        cost_per_1k = MODEL_COST_USD.get(model_name, 0.60)
        return (spawn.estimated_tokens / 1000) * cost_per_1k
    
    def get_routing_plan(self, routed_spec: dict) -> dict:
        """
        Generate a human-readable routing plan from a routed spec.
        Useful for previewing before dispatch.
        """
        subtasks = routed_spec.get("subtasks", [])
        spawns = self._resolve_spawns(subtasks)
        
        plan = {
            "task_id": routed_spec.get("task_id", "unknown"),
            "title": routed_spec.get("title", ""),
            "total_subtasks": len(spawns),
            "total_cost_usd": self._calculate_total_cost(spawns),
            "model_usage": self._count_model_usage(spawns),
            "groups": [],
        }
        
        groups = self._group_by_dependencies(spawns)
        for i, group in enumerate(groups):
            group_info = {
                "group": i + 1,
                "subtasks": [
                    {
                        "id": s.subtask_id,
                        "title": s.title,
                        "model": s.assigned_model,
                        "type": s.task_type,
                        "cost": self._estimate_subtask_cost(s),
                    }
                    for s in group
                ],
            }
            plan["groups"].append(group_info)
        
        return plan


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenClaw Subagent Dispatcher")
    parser.add_argument("--spec", type=Path, required=True, help="Routed TaskSpec JSON")
    parser.add_argument("--plan", action="store_true", help="Show routing plan only (no dispatch)")
    parser.add_argument("--output", type=Path, default=Path("dispatch_result.json"))
    args = parser.parse_args()
    
    with open(args.spec) as f:
        spec = json.load(f)
    
    dispatcher = OpenClawSubagentDispatcher()
    
    if args.plan:
        plan = dispatcher.get_routing_plan(spec)
        print(f"\n{'='*60}")
        print(f"ROUTING PLAN: {plan['title']}")
        print(f"{'='*60}")
        print(f"Total subtasks: {plan['total_subtasks']}")
        print(f"Total cost: ${plan['total_cost_usd']:.4f}")
        print(f"\nModel usage:")
        for model, count in sorted(plan['model_usage'].items(), key=lambda x: -x[1]):
            print(f"  {model}: {count}x")
        print(f"\nExecution groups:")
        for group in plan['groups']:
            print(f"\n  Group {group['group']} (parallel):")
            for st in group['subtasks']:
                print(f"    {st['id']}: {st['title'][:50]}")
                print(f"      → {st['model']} (${st['cost']:.4f})")
    else:
        result = dispatcher.dispatch(spec)
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"✅ Dispatch complete: {result['status']}")
        print(f"   Completed: {result['completed']}/{result['total_subtasks']}")
        print(f"   Models used: {len(result['model_usage'])}")
        print(f"   Total cost: ${result['total_cost_usd']:.4f}")
        print(f"   Duration: {result['duration_ms']}ms")
        print(f"   Saved to: {args.output}")


if __name__ == "__main__":
    main()
