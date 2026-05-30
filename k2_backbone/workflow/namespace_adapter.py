from __future__ import annotations
"""
Namespace Adapter for K2-Backbone

Workflow orchestration with deterministic execution order,
parallel batching, and retry logic.

Ported from Nexys: unified_platform/adapters/namespace_adapter.py
Simplified for K2-Backbone's pipeline architecture.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

logger = logging.getLogger(__name__)


class StepType(Enum):
    """Types of workflow steps"""
    SEQUENTIAL = auto()
    PARALLEL = auto()
    CONDITIONAL = auto()
    WAIT = auto()


class StepState(str, Enum):
    """Step execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    step_id: str
    agent_type: str = "default"
    task_description: str = ""
    depends_on: List[str] = field(default_factory=list)
    output_key: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    timeout_seconds: int = 300


@dataclass
class StepExecution:
    """Execution state for a single step"""
    step_id: str
    state: StepState = StepState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output: Any = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class WorkflowDef:
    """Workflow definition"""
    name: str
    steps: List[WorkflowStep]
    description: str = ""


@dataclass
class WorkflowExecution:
    """Running workflow instance"""
    execution_id: str
    workflow_id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


class NamespaceAdapter:
    """
    Workflow Orchestration Engine for K2-Backbone.
    
    Manages multi-agent workflows with:
    - Sequential execution
    - Parallel execution with join semantics
    - Conditional branching
    - Retry logic with exponential backoff
    
    Usage:
        adapter = NamespaceAdapter()
        
        workflow = WorkflowDef(
            name="DataPipeline",
            steps=[
                WorkflowStep(step_id="extract", agent_type="decomposer", task_description="Extract data"),
                WorkflowStep(step_id="transform", agent_type="router", task_description="Transform data", depends_on=["extract"]),
                WorkflowStep(step_id="load", agent_type="executor", task_description="Load results", depends_on=["transform"]),
            ]
        )
        
        execution = adapter.execute_workflow(workflow, {"source": "k2_decomposer"})
    """
    
    def __init__(
        self,
        max_concurrent_steps: int = 10,
        default_timeout: int = 300,
        enable_retry: bool = True,
    ):
        self.max_concurrent = max_concurrent_steps
        self.default_timeout = default_timeout
        self.enable_retry = enable_retry
        
        self._workflows: Dict[str, WorkflowDef] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        self._step_executions: Dict[str, Dict[str, StepExecution]] = {}
        self._step_handlers: Dict[str, Callable] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize workflow engine"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("NamespaceAdapter initialized")
    
    def register_step_handler(self, agent_type: str, handler: Callable) -> None:
        """Register a handler for an agent type"""
        self._step_handlers[agent_type] = handler
        logger.info(f"Registered handler for {agent_type}")
    
    def create_workflow(self, definition: WorkflowDef) -> str:
        """Register a workflow definition"""
        workflow_id = f"wf_{definition.name.lower()}_{hash(definition.name) % 10000}"
        self._validate_workflow(definition)
        self._workflows[workflow_id] = definition
        logger.info(f"Created workflow: {definition.name} ({workflow_id})")
        return workflow_id
    
    def _validate_workflow(self, definition: WorkflowDef) -> None:
        """Validate workflow structure"""
        step_ids = {s.step_id for s in definition.steps}
        
        for step in definition.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    raise ValueError(f"Step {step.step_id} depends on unknown step {dep}")
        
        # Check for cycles
        visited = set()
        def has_cycle(step_id: str, path: set) -> bool:
            if step_id in path:
                return True
            if step_id in visited:
                return False
            path.add(step_id)
            step = next((s for s in definition.steps if s.step_id == step_id), None)
            if step:
                for dep in step.depends_on:
                    if has_cycle(dep, path):
                        return True
            path.remove(step_id)
            visited.add(step_id)
            return False
        
        for step in definition.steps:
            if has_cycle(step.step_id, set()):
                raise ValueError(f"Cycle detected involving step {step.step_id}")
    
    def execute_workflow(
        self,
        definition: WorkflowDef,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """Execute a workflow"""
        self._ensure_initialized()
        
        execution_id = f"exec_{int(datetime.now().timestamp() * 1000)}"
        workflow_id = self.create_workflow(definition)
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status="running",
            started_at=datetime.now(),
            context=context or {},
        )
        
        self._executions[execution_id] = execution
        self._step_executions[execution_id] = {}
        
        try:
            # Initialize step executions
            for step in definition.steps:
                self._step_executions[execution_id][step.step_id] = StepExecution(
                    step_id=step.step_id
                )
            
            # Compute execution order
            execution_order = self._compute_execution_order(definition)
            
            # Execute steps
            for step_group in execution_order:
                if len(step_group) == 1:
                    self._execute_step(execution_id, step_group[0], execution.context)
                else:
                    self._execute_parallel(execution_id, step_group, execution.context)
                
                if execution.status == "failed":
                    break
            
            if execution.status != "failed":
                execution.status = "completed"
                execution.completed_at = datetime.now()
                
        except Exception as e:
            execution.status = "failed"
            execution.error = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")
        
        return execution
    
    def _compute_execution_order(self, definition: WorkflowDef) -> List[List[WorkflowStep]]:
        """Compute parallel execution groups based on dependencies"""
        steps_by_id = {s.step_id: s for s in definition.steps}
        in_degree = {s.step_id: len(s.depends_on) for s in definition.steps}
        dependents = {s.step_id: [] for s in definition.steps}
        
        for step in definition.steps:
            for dep in step.depends_on:
                dependents[dep].append(step.step_id)
        
        order = []
        ready = [sid for sid, deg in in_degree.items() if deg == 0]
        completed = set()
        
        while ready:
            current_group = [steps_by_id[sid] for sid in ready]
            order.append(current_group)
            
            next_ready = []
            for sid in ready:
                completed.add(sid)
                for dependent in dependents[sid]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_ready.append(dependent)
            
            ready = next_ready
        
        return order
    
    def _execute_step(
        self,
        execution_id: str,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> None:
        """Execute a single step"""
        step_exec = self._step_executions[execution_id][step.step_id]
        step_exec.state = StepState.RUNNING
        step_exec.started_at = datetime.now()
        
        execution = self._executions[execution_id]
        handler = self._step_handlers.get(step.agent_type)
        
        if not handler:
            step_exec.state = StepState.FAILED
            step_exec.error = f"No handler for agent type: {step.agent_type}"
            execution.status = "failed"
            return
        
        # Prepare input from dependencies
        input_data = self._prepare_step_input(execution_id, step, context)
        
        # Execute with retry
        max_retries = step.max_retries if self.enable_retry else 0
        
        for attempt in range(max_retries + 1):
            try:
                result = handler(
                    step.task_description,
                    input_data,
                    step.parameters,
                )
                
                step_exec.output = result
                step_exec.state = StepState.COMPLETED
                step_exec.completed_at = datetime.now()
                execution.completed_steps.append(step.step_id)
                
                if step.output_key:
                    context[step.output_key] = result
                
                break
                
            except Exception as e:
                step_exec.retry_count += 1
                
                if attempt < max_retries:
                    import time
                    time.sleep(2.0 * (2 ** attempt))  # Exponential backoff
                else:
                    step_exec.state = StepState.FAILED
                    step_exec.error = str(e)
                    execution.status = "failed"
                    execution.error = f"Step {step.step_id} failed: {e}"
    
    def _execute_parallel(
        self,
        execution_id: str,
        steps: List[WorkflowStep],
        context: Dict[str, Any],
    ) -> None:
        """Execute steps in parallel using ThreadPool"""
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as pool:
            futures = [
                pool.submit(self._execute_step, execution_id, step, context)
                for step in steps
            ]
            for future in futures:
                future.result()
    
    def _prepare_step_input(
        self,
        execution_id: str,
        step: WorkflowStep,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare input data for step execution"""
        input_data = dict(context)
        
        step_execs = self._step_executions.get(execution_id, {})
        for dep_id in step.depends_on:
            dep_exec = step_execs.get(dep_id)
            if dep_exec and dep_exec.output is not None:
                input_data[f"{dep_id}_output"] = dep_exec.output
        
        return input_data
    
    def get_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get detailed metrics for execution"""
        execution = self._executions.get(execution_id)
        if not execution:
            return {}
        
        step_execs = self._step_executions.get(execution_id, {})
        total = len(step_execs)
        completed = sum(1 for s in step_execs.values() if s.state == StepState.COMPLETED)
        failed = sum(1 for s in step_execs.values() if s.state == StepState.FAILED)
        
        duration = None
        if execution.started_at and execution.completed_at:
            duration = (execution.completed_at - execution.started_at).total_seconds()
        
        return {
            "execution_id": execution_id,
            "status": execution.status,
            "total_steps": total,
            "completed_steps": completed,
            "failed_steps": failed,
            "progress": completed / total if total > 0 else 0,
            "duration_seconds": duration,
            "error": execution.error,
        }
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Namespace Workflow Adapter")
    parser.add_argument("--workflow", type=Path, required=True, help="Workflow JSON file")
    parser.add_argument("--output", type=Path, default=Path("workflow_result.json"))
    args = parser.parse_args()
    
    with open(args.workflow) as f:
        wf_data = json.load(f)
    
    steps = [WorkflowStep(**s) for s in wf_data.get("steps", [])]
    workflow = WorkflowDef(
        name=wf_data.get("name", "unnamed"),
        steps=steps,
        description=wf_data.get("description", ""),
    )
    
    adapter = NamespaceAdapter()
    
    # Register mock handlers
    def mock_handler(task, input_data, params):
        return f"Mock result for: {task}"
    
    adapter.register_step_handler("decomposer", mock_handler)
    adapter.register_step_handler("router", mock_handler)
    adapter.register_step_handler("executor", mock_handler)
    
    execution = adapter.execute_workflow(workflow, wf_data.get("context", {}))
    
    metrics = adapter.get_execution_metrics(execution.execution_id)
    
    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)
    
    print(f"✅ Workflow: {execution.status}")
    print(f"   Steps: {metrics['completed_steps']}/{metrics['total_steps']}")
    print(f"   Duration: {metrics.get('duration_seconds', 'N/A')}s")
    print(f"   Saved to: {args.output}")


if __name__ == "__main__":
    main()
