"""
Dynamic Decomposition Engine — Adaptive subtask spawning mid-execution.

Unlike K2's upfront decomposition, this engine lets the Lead Analyst
spawn new subagents during execution based on intermediate findings.

Pattern: Decompose → Execute → Evaluate → Re-Decompose (if needed)
This is the discovery-driven workflow pattern from Anthropic's system.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class SpawnReason(Enum):
    """Why a new subagent is being spawned"""
    GAP_FOUND = "gap_found"                 # Analyst found a knowledge gap
    CONTRADICTION = "contradiction"          # Two analysts disagree
    DEPTH_NEEDED = "depth_needed"            # Surface finding needs deeper dive
    NEW_ANGLE = "new_angle"                  # Intermediate result suggests new direction
    UNCERTAINTY_HIGH = "uncertainty_high"    # Confidence too low, need more evidence
    CROSS_REFERENCE = "cross_reference"      # Need to verify across sources


@dataclass
class SpawnRequest:
    """A request to spawn a new subagent during execution"""
    reason: SpawnReason
    trigger_analyst: str          # Which analyst triggered this
    trigger_finding: str          # What finding triggered it
    new_query: str                # What to investigate
    suggested_role: str           # Which analyst role to use
    priority: str = "medium"      # high/medium/low
    parent_subtask_id: str = ""
    spawned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class DynamicDecompositionPlan:
    """
    A decomposition plan that can grow during execution.
    
    Unlike a static TaskSpec, this plan:
    - Starts with an initial decomposition
    - Accepts spawn requests mid-execution
    - Tracks which subtasks were dynamically added
    - Records why each spawn was triggered
    """
    initial_subtasks: List[Dict[str, Any]] = field(default_factory=list)
    dynamically_spawned: List[Dict[str, Any]] = field(default_factory=list)
    spawn_requests: List[SpawnRequest] = field(default_factory=list)
    completed_subtasks: List[str] = field(default_factory=list)
    max_dynamic_spawns: int = 5
    max_depth: int = 3  # How deep can re-decomposition go
    
    @property
    def total_subtasks(self) -> int:
        return len(self.initial_subtasks) + len(self.dynamically_spawned)
    
    @property
    def all_subtasks(self) -> List[Dict[str, Any]]:
        return self.initial_subtasks + self.dynamically_spawned
    
    def can_spawn(self, current_depth: int) -> bool:
        """Check if we can spawn more subagents"""
        if len(self.dynamically_spawned) >= self.max_dynamic_spawns:
            return False
        if current_depth >= self.max_depth:
            return False
        return True
    
    def add_spawn_request(self, request: SpawnRequest) -> bool:
        """Add a spawn request if within limits"""
        depth = len([s for s in self.spawn_requests if s.parent_subtask_id == request.parent_subtask_id])
        if not self.can_spawn(depth):
            logger.info(f"Spawn rejected: at limit (depth={depth}, total_spawns={len(self.dynamically_spawned)})")
            return False
        
        self.spawn_requests.append(request)
        return True
    
    def materialize_spawn(self, request: SpawnRequest) -> Dict[str, Any]:
        """Convert a spawn request into an actual subtask"""
        subtask = {
            "id": f"dynamic_{len(self.dynamically_spawned) + 1}",
            "type": "dynamic_analysis",
            "description": request.new_query,
            "target_role": request.suggested_role,
            "phase": "research",
            "focus": request.new_query,
            "priority": request.priority,
            "spawn_reason": request.reason.value,
            "trigger_analyst": request.trigger_analyst,
            "trigger_finding": request.trigger_finding,
            "parent_subtask_id": request.parent_subtask_id,
            "dependencies": [request.parent_subtask_id] if request.parent_subtask_id else [],
        }
        self.dynamically_spawned.append(subtask)
        return subtask


class DynamicDecompositionEngine:
    """
    Engine that enables dynamic decomposition during execution.
    
    How it works:
    1. Lead Analyst provides initial decomposition (as before)
    2. As analysts complete their work, their results are evaluated
    3. If gaps, contradictions, or new angles are found, spawn requests are created
    4. The engine materializes valid spawn requests into new subtasks
    5. New subtasks are executed in the next available parallel batch
    
    This replaces the static pipeline with an adaptive one.
    """
    
    def __init__(
        self,
        max_dynamic_spawns: int = 5,
        max_depth: int = 3,
        spawn_evaluator: Optional[Callable] = None,
    ):
        self.max_dynamic_spawns = max_dynamic_spawns
        self.max_depth = max_depth
        self.spawn_evaluator = spawn_evaluator or self._default_evaluator
    
    def create_plan(self, initial_subtasks: List[Dict[str, Any]]) -> DynamicDecompositionPlan:
        """Create a new dynamic decomposition plan"""
        return DynamicDecompositionPlan(
            initial_subtasks=initial_subtasks,
            max_dynamic_spawns=self.max_dynamic_spawns,
            max_depth=self.max_depth,
        )
    
    def evaluate_result(
        self,
        plan: DynamicDecompositionPlan,
        subtask_id: str,
        result: Any,
        analyst_role: str,
    ) -> List[SpawnRequest]:
        """
        Evaluate an analyst's result and generate spawn requests.
        
        This is the key method — it looks at each result and decides
        whether to spawn new subagents.
        """
        if not hasattr(result, 'findings'):
            return []
        
        findings = result.findings if hasattr(result, 'findings') else {}
        spawn_requests = []
        
        # Check 1: Low confidence → spawn deeper analysis
        if hasattr(result, 'confidence') and result.confidence is not None:
            if result.confidence < 0.5:
                spawn_requests.append(SpawnRequest(
                    reason=SpawnReason.UNCERTAINTY_HIGH,
                    trigger_analyst=analyst_role,
                    trigger_finding=f"Low confidence ({result.confidence:.2f}) in findings",
                    new_query=f"Deep-dive investigation to resolve uncertainty in {analyst_role}'s analysis",
                    suggested_role=self._role_for_deeper_dive(analyst_role),
                    priority="high",
                    parent_subtask_id=subtask_id,
                ))
        
        # Check 2: Knowledge gaps in findings
        if isinstance(findings, dict):
            gap_indicators = ["unknown", "uncertain", "needs further", "requires", "gap", "insufficient"]
            for key, value in findings.items():
                if isinstance(value, str) and any(g in value.lower() for g in gap_indicators):
                    spawn_requests.append(SpawnRequest(
                        reason=SpawnReason.GAP_FOUND,
                        trigger_analyst=analyst_role,
                        trigger_finding=f"Gap detected in '{key}': {value[:100]}",
                        new_query=f"Investigate: {value}",
                        suggested_role=self._role_for_gap(key, analyst_role),
                        priority="medium",
                        parent_subtask_id=subtask_id,
                    ))
        
        # Check 3: New angles suggested
        if isinstance(findings, dict):
            for key, value in findings.items():
                if isinstance(value, str) and any(w in value.lower() for w in ["suggests", "implies", "indicates", "warrants further"]):
                    spawn_requests.append(SpawnRequest(
                        reason=SpawnReason.NEW_ANGLE,
                        trigger_analyst=analyst_role,
                        trigger_finding=f"New angle in '{key}': {value[:100]}",
                        new_query=f"Explore new angle: {value}",
                        suggested_role=self._role_for_new_angle(value),
                        priority="low",
                        parent_subtask_id=subtask_id,
                    ))
        
        # Check 4: Contradictions with previous findings
        if hasattr(result, 'evidence') and result.evidence:
            for ev in (result.evidence if isinstance(result.evidence, list) else []):
                if isinstance(ev, dict) and ev.get("type") == "contradiction":
                    spawn_requests.append(SpawnRequest(
                        reason=SpawnReason.CONTRADICTION,
                        trigger_analyst=analyst_role,
                        trigger_finding=f"Contradiction: {ev.get('data', '')}",
                        new_query=f"Resolve contradiction: {ev.get('data', '')}",
                        suggested_role="devils_advocate",
                        priority="high",
                        parent_subtask_id=subtask_id,
                    ))
        
        return spawn_requests
    
    def _default_evaluator(self, result: Any) -> List[str]:
        """Default evaluation — extract gaps from result text"""
        gaps = []
        text = str(result)
        gap_indicators = ["unknown", "uncertain", "needs further", "requires", "gap", "insufficient"]
        for indicator in gap_indicators:
            if indicator in text.lower():
                gaps.append(indicator)
        return gaps
    
    def _role_for_deeper_dive(self, current_role: str) -> str:
        """Map a role to its deeper-dive counterpart"""
        mapping = {
            "fundamental_analyst": "quantitative_analyst",
            "quantitative_analyst": "fundamental_analyst",
            "risk_analyst": "devils_advocate",
            "technical_analyst": "quantitative_analyst",
            "sector_specialist": "fundamental_analyst",
            "devils_advocate": "risk_analyst",
        }
        return mapping.get(current_role, "fundamental_analyst")
    
    def _role_for_gap(self, gap_key: str, current_role: str) -> str:
        """Determine which role can best fill a knowledge gap"""
        gap_lower = gap_key.lower()
        if any(w in gap_lower for w in ["valuation", "financial", "model", "quant", "ratio"]):
            return "quantitative_analyst"
        elif any(w in gap_lower for w in ["moat", "competitive", "business", "management", "strategy"]):
            return "fundamental_analyst"
        elif any(w in gap_lower for w in ["risk", "scenario", "downside", "black swan"]):
            return "risk_analyst"
        elif any(w in gap_lower for w in ["sector", "industry", "market", "competitive landscape"]):
            return "sector_specialist"
        elif any(w in gap_lower for w in ["price", "technical", "onchain", "options"]):
            return "technical_analyst"
        else:
            return self._role_for_deeper_dive(current_role)
    
    def _role_for_new_angle(self, finding: str) -> str:
        """Determine which role should explore a new angle"""
        finding_lower = finding.lower()
        if any(w in finding_lower for w in ["risk", "danger", "threat", "vulnerability"]):
            return "risk_analyst"
        elif any(w in finding_lower for w in ["opportunity", "growth", "potential"]):
            return "fundamental_analyst"
        elif any(w in finding_lower for w in ["valuation", "price", "multiple"]):
            return "quantitative_analyst"
        else:
            return "devils_advocate"
