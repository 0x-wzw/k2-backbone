from __future__ import annotations
"""
Swarm Orchestrator for K2-Backbone

Production-grade multi-agent orchestration with:
- Pre-deployment planning with dependency mapping
- Clear start/handoff contracts per agent
- Counter-monitoring loops (async execution tracking)
- Output vetting gates before handoff

Usage:
    from k2_backbone.orchestrator.swarm_orchestrator import SwarmOrchestrator
    
    orch = SwarmOrchestrator()
    plan = orch.plan(task_spec)           # Phase 1: Plan
    deployment = orch.deploy(plan)        # Phase 2: Deploy with monitoring
    results = orch.collect(deployment)     # Phase 3: Collect + vet outputs
"""

import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Execution states for swarm agents"""
    PENDING = "pending"
    PLANNED = "planned"      # Task assigned, waiting for dependencies
    STARTED = "started"      # Agent began execution
    RUNNING = "running"      # Agent actively processing
    COMPLETED = "completed"  # Agent finished, output produced
    VETTING = "vetting"      # Output under quality review
    APPROVED = "approved"    # Output passed vetting, ready for handoff
    REJECTED = "rejected"    # Output failed vetting, needs retry
    HANDOFF = "handoff"      # Output delivered to downstream
    FAILED = "failed"        # Agent error
    TIMEOUT = "timeout"      # Exceeded time limit


@dataclass
class AgentTask:
    """Individual task within the swarm"""
    task_id: str
    subtask_id: str
    title: str
    description: str
    agent_model: str
    input_spec: dict
    output_schema: dict
    dependencies: List[str] = field(default_factory=list)
    downstream: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    output: Optional[dict] = None
    vet_score: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def is_ready(self) -> bool:
        """Check if all dependencies are satisfied"""
        return self.status == AgentStatus.PLANNED
    
    @property
    def duration_ms(self) -> int:
        if self.start_time and self.end_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return int((end - start).total_seconds() * 1000)
        return 0


@dataclass
class HandoffContract:
    """Defines what an agent receives and what it must deliver"""
    receives: dict           # Input schema / context
    delivers: dict           # Output schema / deliverables
    validation_rules: List[str] = field(default_factory=list)
    timeout_seconds: int = 300
    
    def validate_output(self, output: dict) -> tuple[bool, List[str]]:
        """Validate output against contract. Returns (passed, errors)"""
        errors = []
        
        for rule in self.validation_rules:
            if rule == "non_empty":
                if not output or not output.get("result"):
                    errors.append("Output is empty")
            elif rule == "has_metrics":
                if "metrics" not in output:
                    errors.append("Missing metrics field")
            elif rule == "has_references":
                if "references" not in output or not output["references"]:
                    errors.append("Missing references")
            elif rule == "json_valid":
                try:
                    json.dumps(output.get("result", {}))
                except (TypeError, ValueError):
                    errors.append("Output is not valid JSON")
            elif rule.startswith("min_length:"):
                min_len = int(rule.split(":")[1])
                content = str(output.get("result", ""))
                if len(content) < min_len:
                    errors.append(f"Output too short ({len(content)} < {min_len})")
        
        return len(errors) == 0, errors


@dataclass
class MonitoringLoop:
    """Counter-monitoring: tracks agent execution without blocking"""
    loop_id: str
    task_id: str
    check_interval_seconds: int = 10
    max_checks: int = 30
    checks_performed: int = 0
    status_log: List[dict] = field(default_factory=list)
    
    def record_check(self, status: AgentStatus, metadata: dict = None):
        self.checks_performed += 1
        self.status_log.append({
            "check": self.checks_performed,
            "timestamp": datetime.now().isoformat(),
            "status": status.value,
            "metadata": metadata or {}
        })
    
    @property
    def is_expired(self) -> bool:
        return self.checks_performed >= self.max_checks


class SwarmOrchestrator:
    """
    Production swarm orchestrator with planning, monitoring, and vetting.
    
    Three-phase execution:
    1. PLAN: Map dependencies, define handoff contracts
    2. DEPLOY: Execute with counter-monitoring loops
    3. COLLECT: Vet outputs, manage handoffs
    """
    
    def __init__(
        self,
        max_workers: int = 5,
        vetting_callback: Optional[Callable] = None,
        output_dir: Optional[Path] = None,
    ):
        self.max_workers = max_workers
        self.vetting_callback = vetting_callback
        self.output_dir = output_dir or Path.home() / ".openclaw" / "workspace" / "k2-backbone" / "executions"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.agents: Dict[str, AgentTask] = {}
        self.monitoring_loops: Dict[str, MonitoringLoop] = {}
        self.execution_log: List[dict] = []
        
        self._executor: Optional[ThreadPoolExecutor] = None
    
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 1: PLAN
    # ═══════════════════════════════════════════════════════════════════
    
    def plan(self, task_spec: dict) -> dict:
        """
        Phase 1: Plan the swarm deployment.
        
        Creates:
        - Dependency graph (DAG)
        - Handoff contracts per agent
        - Monitoring loop configs
        - Execution timeline estimate
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        logger.info(f"Planning deployment: {plan_id}")
        
        subtasks = task_spec.get("subtasks", [])
        agents = {}
        handoff_contracts = {}
        
        for st in subtasks:
            task = AgentTask(
                task_id=task_spec["task_id"],
                subtask_id=st["id"],
                title=st["title"],
                description=st["description"],
                agent_model=st.get("assigned_model", "unknown"),
                input_spec={
                    "task_type": st.get("type", "unknown"),
                    "prompt": st.get("research_prompt", st["description"]),
                    "estimated_tokens": st.get("estimated_tokens", 4096),
                    "dependencies": st.get("dependencies", []),
                },
                output_schema={
                    "result": "any",
                    "metrics": "dict",
                    "references": "list",
                    "confidence": "float",
                },
                dependencies=st.get("dependencies", []),
                status=AgentStatus.PLANNED,
            )
            agents[st["id"]] = task
            
            # Create handoff contract
            contract = HandoffContract(
                receives={
                    "input": task.input_spec,
                    "context": "upstream outputs",
                },
                delivers={
                    "result": task.output_schema,
                    "format": "JSON",
                },
                validation_rules=[
                    "non_empty",
                    "json_valid",
                    "has_references",
                    "min_length:100",
                ],
                timeout_seconds=300,
            )
            handoff_contracts[st["id"]] = contract
        
        # Build downstream mapping
        for task_id, task in agents.items():
            for dep_id in task.dependencies:
                if dep_id in agents:
                    agents[dep_id].downstream.append(task_id)
        
        self.agents = agents
        
        plan = {
            "plan_id": plan_id,
            "task_id": task_spec["task_id"],
            "total_agents": len(agents),
            "agents": {k: self._agent_to_dict(v) for k, v in agents.items()},
            "handoff_contracts": {k: {
                "receives": v.receives,
                "delivers": v.delivers,
                "validation_rules": v.validation_rules,
                "timeout_seconds": v.timeout_seconds,
            } for k, v in handoff_contracts.items()},
            "dependency_graph": self._build_dependency_graph(agents),
            "estimated_timeline": self._estimate_timeline(agents),
            "status": "planned",
            "created_at": datetime.now().isoformat(),
        }
        
        # Save plan
        plan_path = self.output_dir / f"{plan_id}.json"
        with open(plan_path, "w") as f:
            json.dump(plan, f, indent=2)
        
        logger.info(f"Plan saved: {plan_path}")
        return plan
    
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 2: DEPLOY
    # ═══════════════════════════════════════════════════════════════════
    
    def deploy(self, plan: dict, execute_fn: Optional[Callable] = None) -> dict:
        """
        Phase 2: Deploy agents with counter-monitoring.
        
        Executes agents respecting dependencies while monitoring
        progress via non-blocking counter loops.
        """
        deployment_id = f"dep_{uuid.uuid4().hex[:8]}"
        logger.info(f"Deploying swarm: {deployment_id}")
        
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        completed = set()
        failed = set()
        futures = {}
        
        # Initialize monitoring loops for each agent
        for task_id in self.agents:
            loop = MonitoringLoop(
                loop_id=f"loop_{task_id}",
                task_id=task_id,
                check_interval_seconds=10,
                max_checks=30,
            )
            self.monitoring_loops[task_id] = loop
        
        # Execute respecting dependencies
        ready_queue = [
            task_id for task_id, task in self.agents.items()
            if not task.dependencies  # Root tasks (no deps)
        ]
        
        for task_id in ready_queue:
            self.agents[task_id].status = AgentStatus.STARTED
            self.agents[task_id].start_time = datetime.now().isoformat()
        
        # Submit root tasks
        for task_id in ready_queue:
            task = self.agents[task_id]
            future = self._executor.submit(
                self._execute_agent,
                task,
                execute_fn,
            )
            futures[future] = task_id
        
        # Monitor and cascade
        while futures:
            done_futures = []
            for future in list(futures.keys()):
                if future.done():
                    done_futures.append(future)
            
            for future in done_futures:
                task_id = futures.pop(future)
                try:
                    result = future.result(timeout=1)
                    self._handle_completion(task_id, result, completed, failed, futures, execute_fn)
                except Exception as e:
                    logger.error(f"Agent {task_id} failed: {e}")
                    self.agents[task_id].status = AgentStatus.FAILED
                    failed.add(task_id)
            
            time.sleep(0.1)  # Prevent tight loop
        
        self._executor.shutdown(wait=True)
        
        deployment = {
            "deployment_id": deployment_id,
            "plan_id": plan["plan_id"],
            "completed": list(completed),
            "failed": list(failed),
            "agents": {k: self._agent_to_dict(v) for k, v in self.agents.items()},
            "monitoring_logs": {
                k: v.status_log for k, v in self.monitoring_loops.items()
            },
            "status": "completed" if not failed else "partial",
            "ended_at": datetime.now().isoformat(),
        }
        
        # Save deployment
        dep_path = self.output_dir / f"{deployment_id}.json"
        with open(dep_path, "w") as f:
            json.dump(deployment, f, indent=2)
        
        logger.info(f"Deployment saved: {dep_path}")
        return deployment
    
    def _execute_agent(
        self,
        task: AgentTask,
        execute_fn: Optional[Callable] = None,
    ) -> dict:
        """Execute a single agent with monitoring"""
        task.status = AgentStatus.RUNNING
        loop = self.monitoring_loops.get(task.subtask_id)
        
        # Simulate or real execution
        if execute_fn:
            try:
                result = execute_fn(task)
            except Exception as e:
                task.status = AgentStatus.FAILED
                return {"error": str(e), "status": "failed"}
        else:
            # Simulated execution
            time.sleep(0.5)  # Simulate work
            result = {
                "result": f"Simulated output for {task.title}",
                "metrics": {"tokens_used": task.input_spec.get("estimated_tokens", 4096)},
                "references": ["https://www.muiglobal.com"],
                "confidence": 0.85,
            }
        
        task.output = result
        task.status = AgentStatus.COMPLETED
        task.end_time = datetime.now().isoformat()
        
        if loop:
            loop.record_check(AgentStatus.COMPLETED, {"duration_ms": task.duration_ms})
        
        return result
    
    def _handle_completion(
        self,
        task_id: str,
        result: dict,
        completed: Set[str],
        failed: Set[str],
        futures: Dict[Any, str],
        execute_fn: Optional[Callable],
    ):
        """Handle agent completion and trigger downstream"""
        task = self.agents[task_id]
        
        # Vet output
        passed, errors = self._vet_output(task, result)
        
        if passed:
            task.status = AgentStatus.APPROVED
            completed.add(task_id)
            logger.info(f"Agent {task_id} approved")
            
            # Trigger downstream tasks
            for downstream_id in task.downstream:
                downstream_task = self.agents[downstream_id]
                deps_satisfied = all(
                    d in completed for d in downstream_task.dependencies
                )
                
                if deps_satisfied and downstream_task.status == AgentStatus.PLANNED:
                    downstream_task.status = AgentStatus.STARTED
                    downstream_task.start_time = datetime.now().isoformat()
                    
                    # Inject upstream outputs as context
                    upstream_outputs = {
                        dep_id: self.agents[dep_id].output
                        for dep_id in downstream_task.dependencies
                    }
                    downstream_task.input_spec["upstream_outputs"] = upstream_outputs
                    
                    future = self._executor.submit(
                        self._execute_agent,
                        downstream_task,
                        execute_fn,
                    )
                    futures[future] = downstream_id
                    
                    logger.info(f"Triggered downstream: {downstream_id}")
        else:
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = AgentStatus.REJECTED
                logger.warning(f"Agent {task_id} rejected (retry {task.retry_count}/{task.max_retries}): {errors}")
                # Retry
                future = self._executor.submit(
                    self._execute_agent,
                    task,
                    execute_fn,
                )
                futures[future] = task_id
            else:
                task.status = AgentStatus.FAILED
                failed.add(task_id)
                logger.error(f"Agent {task_id} failed after {task.max_retries} retries")
    
    def _vet_output(self, task: AgentTask, output: dict) -> tuple[bool, List[str]]:
        """Vet agent output before handoff"""
        # Get the contract for this task
        contract = getattr(task, '_contract', None)
        if contract is None:
            # Create a default contract
            contract = HandoffContract(
                receives={"input": task.input_spec},
                delivers={"result": task.output_schema},
                validation_rules=[
                    "non_empty",
                    "json_valid",
                    "has_references",
                    "min_length:100",
                ],
                timeout_seconds=300,
            )
        
        passed, errors = contract.validate_output(output)
        
        if passed and self.vetting_callback:
            passed, cb_errors = self.vetting_callback(task, output)
            errors.extend(cb_errors)
        
        task.vet_score = 1.0 if passed else max(0.0, 1.0 - len(errors) * 0.2)
        return passed, errors
    
    # ═══════════════════════════════════════════════════════════════════
    # PHASE 3: COLLECT
    # ═══════════════════════════════════════════════════════════════════
    
    def collect(self, deployment: dict) -> dict:
        """
        Phase 3: Collect and vet all outputs.
        
        Returns aggregated results with quality scores.
        """
        logger.info("Collecting outputs...")
        
        approved_outputs = {}
        rejected_outputs = {}
        
        for task_id, agent_dict in deployment.get("agents", {}).items():
            task = self.agents.get(task_id)
            if not task:
                continue
            
            if task.status == AgentStatus.APPROVED:
                approved_outputs[task_id] = {
                    "output": task.output,
                    "vet_score": task.vet_score,
                    "duration_ms": task.duration_ms,
                    "model": task.agent_model,
                }
            elif task.status in (AgentStatus.REJECTED, AgentStatus.FAILED):
                rejected_outputs[task_id] = {
                    "status": task.status.value,
                    "retries": task.retry_count,
                    "error": task.output.get("error") if task.output else None,
                }
        
        collection = {
            "collection_id": f"col_{uuid.uuid4().hex[:8]}",
            "deployment_id": deployment["deployment_id"],
            "approved_count": len(approved_outputs),
            "rejected_count": len(rejected_outputs),
            "approval_rate": len(approved_outputs) / len(self.agents) if self.agents else 0,
            "approved_outputs": approved_outputs,
            "rejected_outputs": rejected_outputs,
            "collected_at": datetime.now().isoformat(),
        }
        
        # Save collection
        col_path = self.output_dir / f"{collection['collection_id']}.json"
        with open(col_path, "w") as f:
            json.dump(collection, f, indent=2)
        
        logger.info(f"Collection saved: {col_path}")
        return collection
    
    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════
    
    def _build_dependency_graph(self, agents: Dict[str, AgentTask]) -> dict:
        """Build DAG representation"""
        return {
            task_id: {
                "dependencies": task.dependencies,
                "downstream": task.downstream,
                "depth": self._calculate_depth(task_id, agents),
            }
            for task_id, task in agents.items()
        }
    
    def _calculate_depth(self, task_id: str, agents: Dict[str, AgentTask], memo: dict = None) -> int:
        if memo is None:
            memo = {}
        if task_id in memo:
            return memo[task_id]
        
        task = agents.get(task_id)
        if not task or not task.dependencies:
            memo[task_id] = 0
            return 0
        
        depth = max(
            self._calculate_depth(dep, agents, memo) + 1
            for dep in task.dependencies
        )
        memo[task_id] = depth
        return depth
    
    def _estimate_timeline(self, agents: Dict[str, AgentTask]) -> dict:
        """Estimate execution timeline based on DAG depth"""
        depths = {}
        for task_id in agents:
            depths[task_id] = self._calculate_depth(task_id, agents)
        
        max_depth = max(depths.values()) if depths else 0
        total_tasks = len(agents)
        
        # Estimate: max_depth sequential steps * ~30s per task
        estimated_seconds = (max_depth + 1) * 30
        
        return {
            "max_parallel_depth": max_depth + 1,
            "total_tasks": total_tasks,
            "estimated_seconds": estimated_seconds,
            "estimated_minutes": round(estimated_seconds / 60, 1),
        }
    
    def _agent_to_dict(self, task: AgentTask) -> dict:
        return {
            "task_id": task.task_id,
            "subtask_id": task.subtask_id,
            "title": task.title,
            "agent_model": task.agent_model,
            "status": task.status.value,
            "dependencies": task.dependencies,
            "downstream": task.downstream,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "duration_ms": task.duration_ms,
            "vet_score": task.vet_score,
            "retry_count": task.retry_count,
            "has_output": task.output is not None,
        }


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="K2-Backbone Swarm Orchestrator")
    parser.add_argument("--spec", type=Path, required=True, help="TaskSpec JSON")
    parser.add_argument("--output-dir", type=Path, help="Execution output directory")
    args = parser.parse_args()
    
    # Load spec
    with open(args.spec) as f:
        spec = json.load(f)
    
    # Initialize orchestrator
    orch = SwarmOrchestrator(output_dir=args.output_dir)
    
    # Phase 1: Plan
    print("📋 Phase 1: Planning...")
    plan = orch.plan(spec)
    print(f"   ✅ Plan created: {plan['plan_id']}")
    print(f"   📊 Agents: {plan['total_agents']}")
    print(f"   ⏱️  Estimated: {plan['estimated_timeline']['estimated_minutes']} min")
    
    # Phase 2: Deploy
    print("\n🚀 Phase 2: Deploying...")
    deployment = orch.deploy(plan)
    print(f"   ✅ Deployment: {deployment['deployment_id']}")
    print(f"   ✅ Completed: {len(deployment['completed'])}")
    print(f"   ❌ Failed: {len(deployment['failed'])}")
    
    # Phase 3: Collect
    print("\n📦 Phase 3: Collecting...")
    collection = orch.collect(deployment)
    print(f"   ✅ Approved: {collection['approved_count']}")
    print(f"   ❌ Rejected: {collection['rejected_count']}")
    print(f"   📈 Approval Rate: {collection['approval_rate']:.1%}")


if __name__ == "__main__":
    main()
