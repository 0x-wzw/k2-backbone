"""
Base classes for the K2-Analysts Stack.

Every analyst agent implements this protocol, providing:
- Augmented LLM with tools, memory, and retrieval (Anthropic Pattern 1)
- Structured handoff via AnalystContext
- Verifiable output with confidence scoring
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ── Enums ──────────────────────────────────────────────────────────────

class AnalystRole(Enum):
    """Analyst roles in the K2-Analysts Stack"""
    LEAD = "lead_analyst"
    QUANT = "quantitative_analyst"
    FUNDAMENTAL = "fundamental_analyst"
    RISK = "risk_analyst"
    TECHNICAL = "technical_analyst"
    SECTOR = "sector_specialist"
    DEVILS_ADVOCATE = "devils_advocate"
    SYNTHESIS = "synthesis_editor"


class AnalysisPhase(Enum):
    """Phases of the analysis workflow"""
    DECOMPOSE = "decompose"
    RESEARCH = "research"
    MODEL = "model"
    CRITIQUE = "critique"
    SYNTHESIZE = "synthesize"
    REVIEW = "review"
    DELIVER = "deliver"


class HandoffProtocol(Enum):
    """Protocols for analyst-to-analyst handoffs"""
    DELEGATE = "delegate"           # Assign subtask to another analyst
    ESCALATE = "escalate"           # Escalate for deeper analysis
    CONSULT = "consult"             # Request input without blocking
    REVIEW = "review"               # Request review of completed work
    APPROVE = "approve"             # Request approval before proceeding
    SYNTHESIZE = "synthesize"       # Send to synthesis for compilation


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class AnalystContext:
    """Context passed between analysts during handoffs"""
    task_id: str
    original_query: str
    phase: AnalysisPhase
    parent_context: Optional["AnalystContext"] = None
    previous_findings: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, float] = field(default_factory=lambda: {
        "max_cost_usd": 1.0,
        "max_depth": 3,
        "max_analysts": 5,
    })
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def child(self, phase: AnalysisPhase, **overrides) -> "AnalystContext":
        """Create a child context for delegated subtasks"""
        return AnalystContext(
            task_id=self.task_id,
            original_query=self.original_query,
            phase=phase,
            parent_context=self,
            previous_findings=self.previous_findings,
            constraints={**self.constraints, **overrides.get("constraints", {})},
            budget={**self.budget, **overrides.get("budget", {})},
            metadata={**self.metadata, **overrides.get("metadata", {})},
        )


@dataclass
class AnalystResult:
    """Standardized output from any analyst agent"""
    analyst_role: AnalystRole
    status: str  # "completed", "partial", "failed", "escalated"
    findings: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0  # 0.0 to 1.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    handoff: Optional[Dict[str, Any]] = None  # HandoffProtocol + target
    duration_ms: float = 0.0
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyst_role": self.analyst_role.value,
            "status": self.status,
            "findings": self.findings,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "handoff": self.handoff,
            "duration_ms": self.duration_ms,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "error": self.error,
        }


# ── Tool Protocol ─────────────────────────────────────────────────────

@dataclass
class AnalystTool:
    """A tool available to an analyst agent (Anthropic Augmented LLM pattern)"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Optional[callable] = None

    def to_tool_def(self) -> Dict[str, Any]:
        """Convert to Anthropic-compatible tool definition"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


# ── Base Analyst ──────────────────────────────────────────────────────

class BaseAnalyst(ABC):
    """
    Abstract base for all analyst agents.
    
    Implements the Augmented LLM pattern from Anthropic's framework:
    - LLM + Tools + Memory + Retrieval
    
    Each analyst has:
    - A role and specialization
    - A set of tools they can invoke
    - Memory of previous analyses
    - Handoff protocols for delegation
    """
    
    def __init__(
        self,
        role: AnalystRole,
        specialization: str,
        model: str = "deepseek-v4-flash",
        tools: Optional[List[AnalystTool]] = None,
        memory_path: Optional[str] = None,
    ):
        self.role = role
        self.specialization = specialization
        self.model = model
        self.tools = tools or []
        self.memory_path = memory_path or Path.home() / ".openclaw" / "workspace" / "k2-backbone" / "executions" / "analyst_memory"
        
        # Ensure memory directory exists
        Path(self.memory_path).mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def analyze(self, context: AnalystContext) -> AnalystResult:
        """
        Execute analysis for this analyst's specialization.
        
        This is the core method — each analyst implements their
        domain-specific analysis logic here.
        
        Args:
            context: Analysis context with query, constraints, previous findings
            
        Returns:
            AnalystResult with findings, confidence, evidence
        """
        ...
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions in Anthropic-compatible format"""
        return [t.to_tool_def() for t in self.tools]
    
    def save_to_memory(self, result: AnalystResult) -> str:
        """Persist analysis result to analyst memory"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.role.value}_{timestamp}.json"
        filepath = Path(self.memory_path) / filename
        
        with open(filepath, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
        
        return str(filepath)
    
    def load_from_memory(self, limit: int = 5) -> List[AnalystResult]:
        """Load recent analyses from memory"""
        import glob
        
        pattern = str(Path(self.memory_path) / f"{self.role.value}_*.json")
        files = sorted(glob.glob(pattern), reverse=True)[:limit]
        
        results = []
        for f in files:
            with open(f) as fp:
                data = json.load(fp)
                result = AnalystResult(
                    analyst_role=AnalystRole(data["analyst_role"]),
                    status=data["status"],
                    findings=data.get("findings", {}),
                    confidence=data.get("confidence", 0.0),
                )
                results.append(result)
        
        return results
    
    def handoff(
        self,
        protocol: HandoffProtocol,
        target_role: AnalystRole,
        context: AnalystContext,
        findings: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a structured handoff to another analyst.
        
        This implements Anthropic's handoff pattern — analysts
        can delegate, escalate, consult, or request review.
        """
        return {
            "protocol": protocol.value,
            "from_role": self.role.value,
            "to_role": target_role.value,
            "context": {
                "task_id": context.task_id,
                "phase": context.phase.value,
                "findings_to_pass": findings,
                "constraints": context.constraints,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for this analyst's model"""
        # DeepSeek V4 Flash pricing (approximate)
        rates = {
            "deepseek-v4-flash": {"input": 0.15, "output": 0.60},
            "deepseek-v4-pro": {"input": 0.50, "output": 2.00},
            "qwen3.5-122b": {"input": 0.30, "output": 1.20},
            "qwen3.5-397b": {"input": 0.80, "output": 3.20},
            "minimax-m3": {"input": 0.40, "output": 1.60},
        }
        
        rate = rates.get(self.model, {"input": 0.15, "output": 0.60})
        return (input_tokens * rate["input"] + output_tokens * rate["output"]) / 1_000_000


# ── Analyst Registry ─────────────────────────────────────────────────

class AnalystRegistry:
    """
    Registry of available analyst agents.
    
    The orchestrator uses this to discover and dispatch to analysts.
    Implements the Routing pattern from Anthropic's framework.
    """
    
    def __init__(self):
        self._analysts: Dict[AnalystRole, BaseAnalyst] = {}
    
    def register(self, analyst: BaseAnalyst):
        """Register an analyst agent"""
        self._analysts[analyst.role] = analyst
        logger.info(f"Registered analyst: {analyst.role.value} ({analyst.specialization})")
    
    def get(self, role: AnalystRole) -> Optional[BaseAnalyst]:
        """Get analyst by role"""
        return self._analysts.get(role)
    
    def get_by_specialization(self, query: str) -> List[BaseAnalyst]:
        """Find analysts matching a specialization query"""
        query_lower = query.lower()
        matches = []
        for analyst in self._analysts.values():
            if query_lower in analyst.specialization.lower():
                matches.append(analyst)
        return matches
    
    def list_roles(self) -> List[AnalystRole]:
        """List all registered analyst roles"""
        return list(self._analysts.keys())
    
    def count(self) -> int:
        return len(self._analysts)
