"""
Core interfaces for K2-Backbone.

All components implement these protocols, enabling swappable implementations
and clean dependency injection.
"""

from typing import Protocol, runtime_checkable
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Optional


@runtime_checkable
class Decomposer(Protocol):
    """Task decomposition into structured subtask plans."""

    def decompose(self, task: str, context: str = "") -> dict:
        """
        Decompose a task into a structured plan.

        Returns: TaskSpec dict conforming to k2-task-spec.schema.json
        """
        ...


@runtime_checkable
class Router(Protocol):
    """Assigns models/agents to subtasks based on capability and cost."""

    def route(self, task_spec: dict) -> dict:
        """
        Assign execution targets to each subtask.

        Returns: TaskSpec with `assigned_model` filled on each subtask.
        """
        ...


@runtime_checkable
class Executor(Protocol):
    """Runs subtasks and collects results."""

    def execute(self, routed_spec: dict) -> dict:
        """
        Execute all subtasks respecting dependencies.

        Returns: dict with `results`, `traces`, `status`.
        """
        ...


@runtime_checkable
class Memory(Protocol):
    """Stores, compresses, and retrieves execution traces."""

    def ingest(self, task_id: str, traces: list[dict]) -> str:
        """
        Ingest raw traces, return compressed schema ID.
        """
        ...

    def retrieve(self, query: str, exact: bool = False) -> list[dict]:
        """
        Retrieve relevant compressed traces.
        """
        ...


@runtime_checkable
class Federation(Protocol):
    """Bridges to external agent systems."""

    def bridge(self, protocol: str, payload: dict) -> dict:
        """
        Translate and send payload to external system.

        protocol: "a2a", "mcp", "hermes", "openclaw", "swarm", "langgraph", "crewai"
        """
        ...

    def discover(self) -> list[dict]:
        """
        List available agents/systems in the mesh.
        """
        ...
