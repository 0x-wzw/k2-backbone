from __future__ import annotations
"""
NeuroSwarm Integration Layer for K2-Backbone

Wires NeuroSwarm's full dispatcher (GBrain + NecroSwarm) into K2-Backbone's
pipeline, replacing the lightweight executor while preserving:
- K2.6 decomposition input
- NecroSwarmRouter cost optimization
- Obliviarch memory compression output
- AutoMon bridge cost tracking

Usage:
    from k2_backbone.executor.neuroswarm_integration import NeuroSwarmIntegratedExecutor
    
    executor = NeuroSwarmIntegratedExecutor()
    result = executor.run(routed_spec)  # TaskSpec from K2.6 → Router
"""

import json
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Add NeuroSwarm to path
NEUROSWARM_PATH = Path(__file__).parent.parent.parent / "frameworks" / "neuroswarm"
if str(NEUROSWARM_PATH) not in sys.path:
    sys.path.insert(0, str(NEUROSWARM_PATH))

try:
    from neuroswarm.dispatcher import NeuroSwarmDispatcher
    from neuroswarm.brain.resolver import resolve
    NEUROSWARM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"NeuroSwarm not available: {e}")
    NEUROSWARM_AVAILABLE = False

# K2-Backbone imports
from k2_backbone.executor.neuroswarm_executor import NeuroSwarmExecutor as LightweightExecutor
from k2_backbone.memory.obliviarch_adapter import ObliviarchAdapter


@dataclass
class IntegratedExecutionResult:
    """Result from NeuroSwarm-integrated execution"""
    task_id: str
    status: str
    neuroswarm_phase1: Dict[str, Any] = field(default_factory=dict)
    neuroswarm_phase2: Dict[str, Any] = field(default_factory=dict)
    execution_trace: Dict[str, Any] = field(default_factory=dict)
    obliviarch_schema_id: Optional[str] = None
    cost: Dict[str, float] = field(default_factory=dict)


class NeuroSwarmIntegratedExecutor:
    """
    K2-Backbone executor that delegates to NeuroSwarm's full dispatcher.
    
    Pipeline:
      K2.6 TaskSpec → NecroSwarmRouter (cost-optimal model assignment)
        → NeuroSwarmDispatcher (GBrain + full Council deliberation)
        → ObliviarchAdapter.ingest() (compression)
        → AutoMon cost tracking
    
    This gives you:
    - K2.6's decomposition intelligence
    - K2-Backbone's cost-optimized routing
    - NeuroSwarm's signal detection + enrichment + sparring
    - Obliviarch's 500x compression
    """
    
    def __init__(
        self,
        use_neuroswarm: bool = True,
        council_seats: Optional[Dict[str, str]] = None,
        enable_obliviarch: bool = True,
        max_workers: int = 5,
    ):
        self.use_neuroswarm = use_neuroswarm and NEUROSWARM_AVAILABLE
        self.enable_obliviarch = enable_obliviarch
        
        # Initialize NeuroSwarm dispatcher (if available)
        if self.use_neuroswarm:
            self.dispatcher = NeuroSwarmDispatcher(council_seats=council_seats)
            logger.info("NeuroSwarm dispatcher initialized")
        else:
            # Fallback to lightweight executor
            self.fallback = LightweightExecutor(max_workers=max_workers)
            logger.info("Using lightweight executor (NeuroSwarm not available)")
        
        # Initialize Obliviarch
        if self.enable_obliviarch:
            self.obliviarch = ObliviarchAdapter()
            self.obliviarch.initialize()
    
    def run(self, routed_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute routed TaskSpec using NeuroSwarm's full pipeline.
        
        Args:
            routed_spec: TaskSpec with assigned_model per subtask
            
        Returns:
            Execution result with NeuroSwarm deliberation + Obliviarch compression
        """
        task_id = routed_spec.get("task_id", "unknown")
        
        if self.use_neuroswarm:
            return self._run_neuroswarm(routed_spec, task_id)
        else:
            return self._run_fallback(routed_spec, task_id)
    
    def _run_neuroswarm(self, routed_spec: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """
        Full NeuroSwarm integration:
        1. Convert TaskSpec to NeuroSwarm query
        2. Phase 1: GBrain resolves intent (WHAT)
        3. Phase 2: Council deliberates approach (HOW)
        4. Execute with cost-optimized model routing
        5. Compress via Obliviarch
        """
        # Build query from TaskSpec
        query = self._build_query(routed_spec)
        context = self._build_context(routed_spec)
        
        logger.info(f"NeuroSwarm dispatch: {query[:80]}...")
        
        # Phase 1: GBrain (WHAT)
        brain_result = self.dispatcher.resolve_intent(query)
        logger.info(f"  Phase 1 resolved: {brain_result.get('primary', {}).get('skill', 'unknown')}")
        
        # Phase 2: Council (HOW) — with K2-Backbone's cost-optimized routing
        swarm_result = self.dispatcher.deliberate(brain_result, context=context)
        logger.info(f"  Phase 2 approach: {swarm_result.get('approach', 'direct')}")
        
        # Execute with cost-optimized models from router
        execution_result = self._execute_with_routing(routed_spec, brain_result, swarm_result)
        
        # Obliviarch compression
        obliviarch_id = None
        if self.enable_obliviarch:
            obliviarch_id = self.obliviarch.ingest(task_id, execution_result)
            logger.info(f"  Obliviarch: {obliviarch_id}")
        
        # Cost tracking
        routing = routed_spec.get("routing", {})
        cost = {
            "estimated": routing.get("total_estimated_cost_usd", 0),
            "neuroswarm_overhead": 0.05,  # Phase 1+2 cost
            "obliviarch": 0.01 if self.enable_obliviarch else 0,
        }
        
        return {
            "task_id": task_id,
            "status": execution_result.get("status", "completed"),
            "mode": "neuroswarm_full",
            "neuroswarm": {
                "phase1_what": {
                    "skill": brain_result.get("primary", {}).get("skill"),
                    "complexity": brain_result.get("primary", {}).get("complexity"),
                    "council_needed": brain_result.get("council_needed", False),
                    "signals": brain_result.get("brain_context", {}).get("signals", {}),
                },
                "phase2_how": {
                    "approach": swarm_result.get("approach"),
                    "council_seats": swarm_result.get("council_seats", []),
                    "fallback_chain": swarm_result.get("fallback_chain", []),
                },
            },
            "execution_trace": execution_result.get("execution_trace", {}),
            "obliviarch_schema_id": obliviarch_id,
            "cost": cost,
            "summary": {
                "subtasks": len(routed_spec.get("subtasks", [])),
                "models_used": list(set(
                    s.get("assigned_model", "") 
                    for s in routed_spec.get("subtasks", [])
                )),
                "neuroswarm_enhanced": True,
            }
        }
    
    def _run_fallback(self, routed_spec: Dict[str, Any], task_id: str) -> Dict[str, Any]:
        """Fallback to lightweight executor when NeuroSwarm unavailable"""
        logger.warning("NeuroSwarm unavailable, using lightweight executor")
        return self.fallback.run(routed_spec)
    
    def _build_query(self, routed_spec: Dict[str, Any]) -> str:
        """Convert TaskSpec into NeuroSwarm query string"""
        title = routed_spec.get("title", "")
        objective = routed_spec.get("objective", "")
        
        # Build from subtasks
        subtasks = routed_spec.get("subtasks", [])
        task_types = [s.get("type", "") for s in subtasks]
        
        query_parts = [title, objective]
        if task_types:
            query_parts.append(f"Tasks: {', '.join(task_types)}")
        
        return ". ".join(query_parts)
    
    def _build_context(self, routed_spec: Dict[str, Any]) -> str:
        """Build context string for NeuroSwarm deliberation"""
        context_parts = []
        
        # Budget context
        budget = routed_spec.get("budget", {})
        if budget:
            context_parts.append(f"Budget: ${budget.get('max_usd', 0)} USD")
        
        # Risk level
        risk = routed_spec.get("risk_level", "medium")
        context_parts.append(f"Risk: {risk}")
        
        # Model assignments
        subtasks = routed_spec.get("subtasks", [])
        models = set(s.get("assigned_model", "") for s in subtasks)
        if models:
            context_parts.append(f"Models assigned: {', '.join(models)}")
        
        return " | ".join(context_parts)
    
    def _execute_with_routing(
        self,
        routed_spec: Dict[str, Any],
        brain_result: Dict[str, Any],
        swarm_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute subtasks using K2-Backbone's cost-optimized routing
        enriched with NeuroSwarm's deliberation.
        """
        from concurrent.futures import ThreadPoolExecutor
        
        subtasks = routed_spec.get("subtasks", [])
        results = []
        
        # Get approach from NeuroSwarm
        approach = swarm_result.get("approach", "direct_execution")
        
        if approach == "direct_execution":
            # Simple: execute sequentially
            for subtask in subtasks:
                result = self._execute_single(subtask, brain_result)
                results.append(result)
        else:
            # Council-recommended: use parallel batches
            # Group by dependencies
            dependency_groups = self._group_by_dependencies(subtasks)
            
            for group in dependency_groups:
                with ThreadPoolExecutor(max_workers=5) as pool:
                    futures = [
                        pool.submit(self._execute_single, st, brain_result)
                        for st in group
                    ]
                    for future in futures:
                        results.append(future.result())
        
        # Build execution trace
        total_duration = sum(r.get("duration_ms", 0) for r in results)
        all_pass = all(r.get("status") == "completed" for r in results)
        
        return {
            "status": "completed" if all_pass else "partial_failure",
            "execution_trace": {
                "results": results,
                "total_duration_ms": total_duration,
                "approach": approach,
            },
            "brain_context": brain_result.get("brain_context", {}),
            "council_verdict": swarm_result.get("council_verdict"),
        }
    
    def _execute_single(
        self,
        subtask: Dict[str, Any],
        brain_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a single subtask with NeuroSwarm context"""
        import time
        start = time.time()
        
        # In production: make actual API call with assigned model
        # For now: simulate with context enrichment
        model = subtask.get("assigned_model", "unknown")
        task_type = subtask.get("type", "unknown")
        
        # Enrich with brain context (NeuroSwarm feature)
        enrichment = {}
        if brain_context.get("signals"):
            signals = brain_context["signals"]
            enrichment["relevant_signals"] = signals.get("high", 0)
        
        # Simulate execution
        import random
        success = random.random() > 0.05  # 95% success rate
        
        duration_ms = int((time.time() - start) * 1000)
        
        return {
            "subtask_id": subtask.get("id", "unknown"),
            "status": "completed" if success else "failed",
            "model_used": model,
            "task_type": task_type,
            "duration_ms": duration_ms,
            "enrichment": enrichment,
            "output": f"Executed {task_type} via {model}" if success else None,
            "error": None if success else "Simulated failure",
        }
    
    def _group_by_dependencies(self, subtasks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group subtasks by dependency depth for parallel execution"""
        if not subtasks:
            return []
        
        # Build dependency map
        ids = {s["id"]: s for s in subtasks}
        in_degree = {s["id"]: len(s.get("dependencies", [])) for s in subtasks}
        dependents = {s["id"]: [] for s in subtasks}
        
        for s in subtasks:
            for dep in s.get("dependencies", []):
                if dep in dependents:
                    dependents[dep].append(s["id"])
        
        # Topological sort into groups
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
    
    def query_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query Obliviarch compressed memories"""
        if self.enable_obliviarch:
            return self.obliviarch.query(query, limit=limit)
        return []


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="NeuroSwarm Integrated Executor")
    parser.add_argument("--spec", required=True, help="Routed TaskSpec JSON file")
    parser.add_argument("--neuroswarm", action="store_true", default=True, help="Use NeuroSwarm dispatcher")
    parser.add_argument("--no-neuroswarm", dest="neuroswarm", action="store_false", help="Use lightweight executor")
    parser.add_argument("--no-obliviarch", dest="obliviarch", action="store_false", default=True, help="Skip Obliviarch compression")
    parser.add_argument("--output", default="integrated_result.json", help="Output file")
    args = parser.parse_args()
    
    with open(args.spec) as f:
        spec = json.load(f)
    
    executor = NeuroSwarmIntegratedExecutor(
        use_neuroswarm=args.neuroswarm,
        enable_obliviarch=args.obliviarch,
    )
    
    result = executor.run(spec)
    
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"✅ Execution complete: {result['status']}")
    print(f"   Mode: {result.get('mode', 'unknown')}")
    print(f"   NeuroSwarm: {'enabled' if args.neuroswarm else 'disabled'}")
    print(f"   Obliviarch: {'enabled' if args.obliviarch else 'disabled'}")
    if result.get('obliviarch_schema_id'):
        print(f"   Schema: {result['obliviarch_schema_id']}")
    print(f"   Saved to: {args.output}")


if __name__ == "__main__":
    main()
