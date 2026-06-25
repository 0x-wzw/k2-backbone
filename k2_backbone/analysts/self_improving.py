"""
Self-Improving Agents — Meta-loop for tool quality and agent improvement.

In Anthropic's system, agents can improve their own tools by:
1. Testing tool descriptions against real usage
2. Finding bugs, ambiguities, or gaps in tool definitions
3. Rewriting tool descriptions to be more effective
4. Learning from execution patterns

This is a meta-loop that operates above the analysis pipeline.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ToolIssueType(Enum):
    """Types of issues found in tool definitions"""
    AMBIGUOUS_DESCRIPTION = "ambiguous_description"
    MISSING_PARAMETER = "missing_parameter"
    INCORRECT_SCHEMA = "incorrect_schema"
    POOR_EXAMPLE = "poor_example"
    CONFUSING_NAME = "confusing_name"
    REDUNDANT_TOOL = "redundant_tool"
    MISSING_ERROR_HANDLING = "missing_error_handling"
    INSUFFICIENT_OUTPUT_DOC = "insufficient_output_documentation"


@dataclass
class ToolIssue:
    """An issue found in a tool definition"""
    tool_name: str
    issue_type: ToolIssueType
    description: str
    severity: str  # "critical", "high", "medium", "low"
    suggested_fix: str
    evidence: str  # What usage pattern revealed this
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ToolUsageRecord:
    """Record of how a tool was used"""
    tool_name: str
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_response_time_ms: float = 0.0
    common_errors: List[str] = field(default_factory=list)
    user_feedback: List[str] = field(default_factory=list)
    last_used: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        if self.call_count == 0:
            return 1.0
        return self.success_count / self.call_count


@dataclass
class ToolImprovementProposal:
    """A proposal to improve a tool definition"""
    tool_name: str
    original_description: str
    proposed_description: str
    original_schema: Dict[str, Any]
    proposed_schema: Dict[str, Any]
    issues_addressed: List[ToolIssue]
    expected_improvement: str
    applied: bool = False
    applied_at: Optional[str] = None


class ToolTestingAgent:
    """
    Agent that tests tool descriptions and finds bugs.
    
    This is the meta-loop that makes the system self-improving.
    It monitors tool usage, identifies issues, and proposes fixes.
    """
    
    def __init__(
        self,
        improvement_dir: Optional[str] = None,
        auto_apply: bool = False,
        min_usage_before_review: int = 5,
    ):
        self.improvement_dir = improvement_dir or str(
            Path.home() / ".openclaw" / "workspace" / "k2-backbone" / "executions" / "tool_improvements"
        )
        self.auto_apply = auto_apply
        self.min_usage_before_review = min_usage_before_review
        
        # Track tool usage
        self.usage_records: Dict[str, ToolUsageRecord] = {}
        self.known_issues: List[ToolIssue] = []
        self.proposals: List[ToolImprovementProposal] = []
        
        # Ensure directory exists
        Path(self.improvement_dir).mkdir(parents=True, exist_ok=True)
    
    def record_usage(
        self,
        tool_name: str,
        success: bool,
        error: Optional[str] = None,
        response_time_ms: float = 0.0,
    ):
        """Record a tool usage for analysis"""
        if tool_name not in self.usage_records:
            self.usage_records[tool_name] = ToolUsageRecord(tool_name=tool_name)
        
        record = self.usage_records[tool_name]
        record.call_count += 1
        if success:
            record.success_count += 1
        else:
            record.failure_count += 1
            if error:
                record.common_errors.append(error)
        
        # Update average response time
        record.avg_response_time_ms = (
            (record.avg_response_time_ms * (record.call_count - 1) + response_time_ms)
            / record.call_count
        )
        record.last_used = datetime.utcnow().isoformat()
        
        # Check if we should review this tool
        if record.call_count >= self.min_usage_before_review:
            self._review_tool(tool_name, record)
    
    def _review_tool(self, tool_name: str, record: ToolUsageRecord):
        """Review a tool's usage patterns and find issues"""
        issues = []
        
        # Check 1: Low success rate
        if record.success_rate < 0.7 and record.call_count >= 5:
            issues.append(ToolIssue(
                tool_name=tool_name,
                issue_type=ToolIssueType.AMBIGUOUS_DESCRIPTION,
                description=f"Tool has {record.success_rate:.0%} success rate — description may be ambiguous",
                severity="high",
                suggested_fix="Clarify tool description with explicit examples and edge cases",
                evidence=f"{record.failure_count} failures out of {record.call_count} calls. Common errors: {record.common_errors[:3]}",
            ))
        
        # Check 2: Common error patterns
        if record.common_errors:
            error_counts = {}
            for err in record.common_errors:
                error_counts[err] = error_counts.get(err, 0) + 1
            
            most_common = max(error_counts, key=error_counts.get)
            if error_counts[most_common] >= 3:
                issues.append(ToolIssue(
                    tool_name=tool_name,
                    issue_type=ToolIssueType.MISSING_ERROR_HANDLING,
                    description=f"Recurring error: '{most_common}' occurred {error_counts[most_common]} times",
                    severity="medium",
                    suggested_fix=f"Add error handling for '{most_common}' in tool implementation",
                    evidence=f"Error occurred {error_counts[most_common]} times in {record.call_count} calls",
                ))
        
        # Check 3: Slow response time
        if record.avg_response_time_ms > 5000 and record.call_count >= 3:
            issues.append(ToolIssue(
                tool_name=tool_name,
                issue_type=ToolIssueType.INSUFFICIENT_OUTPUT_DOC,
                description=f"Average response time {record.avg_response_time_ms:.0f}ms — may need optimization",
                severity="low",
                suggested_fix="Document expected response time and add timeout guidance",
                evidence=f"Average: {record.avg_response_time_ms:.0f}ms across {record.call_count} calls",
            ))
        
        if issues:
            self.known_issues.extend(issues)
            for issue in issues:
                logger.info(f"  [ToolTest] Found issue in '{tool_name}': {issue.issue_type.value}")
    
    def analyze_tool_definition(
        self,
        tool_name: str,
        description: str,
        schema: Dict[str, Any],
    ) -> List[ToolIssue]:
        """Analyze a tool definition for potential issues"""
        issues = []
        
        # Check 1: Description quality
        if len(description) < 20:
            issues.append(ToolIssue(
                tool_name=tool_name,
                issue_type=ToolIssueType.AMBIGUOUS_DESCRIPTION,
                description=f"Description too short ({len(description)} chars) — may be ambiguous",
                severity="medium",
                suggested_fix="Expand description to at least 50 characters with clear purpose and examples",
                evidence=f"Current: '{description}'",
            ))
        
        if not any(c.isupper() for c in description.split()):
            issues.append(ToolIssue(
                tool_name=tool_name,
                issue_type=ToolIssueType.AMBIGUOUS_DESCRIPTION,
                description="Description lacks proper capitalization — may confuse parsing",
                severity="low",
                suggested_fix="Use proper sentence structure with capitalization",
                evidence=f"Current: '{description}'",
            ))
        
        # Check 2: Schema completeness
        if "properties" in schema:
            props = schema["properties"]
            for prop_name, prop_def in props.items():
                if "description" not in prop_def:
                    issues.append(ToolIssue(
                        tool_name=tool_name,
                        issue_type=ToolIssueType.MISSING_PARAMETER,
                        description=f"Parameter '{prop_name}' lacks description",
                        severity="medium",
                        suggested_fix=f"Add description for parameter '{prop_name}'",
                        evidence=f"Parameter '{prop_name}' in {tool_name} has no description",
                    ))
        
        # Check 3: Required parameters
        if "required" in schema and not schema["required"]:
            issues.append(ToolIssue(
                tool_name=tool_name,
                issue_type=ToolIssueType.INCORRECT_SCHEMA,
                description="No required parameters — tool may be too permissive",
                severity="low",
                suggested_fix="Add at least one required parameter to ensure meaningful usage",
                evidence="'required' array is empty",
            ))
        
        return issues
    
    def propose_improvement(
        self,
        tool_name: str,
        original_description: str,
        original_schema: Dict[str, Any],
        issues: List[ToolIssue],
    ) -> Optional[ToolImprovementProposal]:
        """Propose an improvement to a tool definition"""
        if not issues:
            return None
        
        # Generate improved description
        improved_description = self._generate_improved_description(
            original_description, original_schema, issues
        )
        
        # Generate improved schema
        improved_schema = self._generate_improved_schema(
            original_schema, issues
        )
        
        proposal = ToolImprovementProposal(
            tool_name=tool_name,
            original_description=original_description,
            proposed_description=improved_description,
            original_schema=original_schema,
            proposed_schema=improved_schema,
            issues_addressed=issues,
            expected_improvement=self._estimate_improvement(issues),
        )
        
        self.proposals.append(proposal)
        
        if self.auto_apply:
            self.apply_proposal(proposal)
        
        return proposal
    
    def _generate_improved_description(
        self,
        original: str,
        schema: Dict[str, Any],
        issues: List[ToolIssue],
    ) -> str:
        """Generate an improved tool description"""
        # Start with original
        improved = original
        
        # Add parameter descriptions if missing
        if "properties" in schema:
            param_descs = []
            for name, prop in schema["properties"].items():
                if "description" in prop:
                    param_descs.append(f"{name}: {prop['description']}")
            
            if param_descs:
                improved += f"\n\nParameters:\n" + "\n".join(f"- {d}" for d in param_descs)
        
        # Add usage guidance
        improved += "\n\nUsage: Call this tool when you need to analyze the specified domain. "
        improved += "The tool will return structured findings with confidence scores."
        
        # Add error handling
        improved += "\n\nErrors: Returns error message if analysis fails. Retry with different parameters if needed."
        
        return improved
    
    def _generate_improved_schema(
        self,
        original: Dict[str, Any],
        issues: List[ToolIssue],
    ) -> Dict[str, Any]:
        """Generate an improved tool schema"""
        improved = {**original}
        
        # Add missing descriptions to parameters
        if "properties" in improved:
            for name, prop in improved["properties"].items():
                if "description" not in prop:
                    prop["description"] = f"The {name} parameter for this analysis"
        
        # Ensure required is not empty
        if "required" in improved and not improved["required"]:
            # Make the first parameter required
            if improved.get("properties"):
                first_prop = list(improved["properties"].keys())[0]
                improved["required"] = [first_prop]
        
        return improved
    
    def _estimate_improvement(self, issues: List[ToolIssue]) -> str:
        """Estimate the expected improvement from applying fixes"""
        critical = sum(1 for i in issues if i.severity == "critical")
        high = sum(1 for i in issues if i.severity == "high")
        medium = sum(1 for i in issues if i.severity == "medium")
        
        if critical > 0:
            return f"Resolves {critical} critical and {high} high severity issues — significant reliability improvement expected"
        elif high > 0:
            return f"Resolves {high} high severity issues — moderate improvement expected"
        elif medium > 0:
            return f"Resolves {medium} medium severity issues — minor improvement expected"
        else:
            return "Resolves low severity issues — marginal improvement"
    
    def apply_proposal(self, proposal: ToolImprovementProposal) -> bool:
        """Apply a tool improvement proposal"""
        proposal.applied = True
        proposal.applied_at = datetime.utcnow().isoformat()
        
        # Save the proposal
        self._save_proposal(proposal)
        
        logger.info(f"  [ToolTest] Applied improvement to '{proposal.tool_name}': {proposal.expected_improvement}")
        return True
    
    def _save_proposal(self, proposal: ToolImprovementProposal):
        """Save a proposal to disk"""
        filename = f"improvement_{proposal.tool_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(self.improvement_dir) / filename
        
        with open(filepath, "w") as f:
            json.dump({
                "tool_name": proposal.tool_name,
                "original_description": proposal.original_description,
                "proposed_description": proposal.proposed_description,
                "original_schema": proposal.original_schema,
                "proposed_schema": proposal.proposed_schema,
                "issues_addressed": [
                    {"type": i.issue_type.value, "description": i.description, "severity": i.severity}
                    for i in proposal.issues_addressed
                ],
                "expected_improvement": proposal.expected_improvement,
                "applied": proposal.applied,
                "applied_at": proposal.applied_at,
            }, f, indent=2)
    
    def get_improvement_report(self) -> Dict[str, Any]:
        """Get a report of all improvements made"""
        return {
            "tools_monitored": len(self.usage_records),
            "total_calls": sum(r.call_count for r in self.usage_records.values()),
            "issues_found": len(self.known_issues),
            "proposals_made": len(self.proposals),
            "proposals_applied": sum(1 for p in self.proposals if p.applied),
            "tools_by_success_rate": {
                name: record.success_rate
                for name, record in sorted(
                    self.usage_records.items(),
                    key=lambda x: x[1].success_rate,
                )
            },
            "common_errors": self._get_common_errors(),
        }
    
    def _get_common_errors(self) -> Dict[str, int]:
        """Get the most common errors across all tools"""
        error_counts: Dict[str, int] = {}
        for record in self.usage_records.values():
            for error in record.common_errors:
                error_counts[error] = error_counts.get(error, 0) + 1
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10])


class SelfImprovingAnalystMixin:
    """
    Mixin that adds self-improving capabilities to any analyst.
    
    Usage:
        class MyAnalyst(BaseAnalyst, SelfImprovingAnalystMixin):
            ...
    
    This mixin:
    - Monitors tool usage
    - Finds issues in tool definitions
    - Proposes improvements
    - Applies improvements (if auto-apply is enabled)
    """
    
    def __init__(self, *args, **kwargs):
        self._tool_tester = ToolTestingAgent()
        super().__init__(*args, **kwargs)
        
        # Analyze initial tool definitions
        self._analyze_initial_tools()
    
    def _analyze_initial_tools(self):
        """Analyze all tool definitions for issues"""
        for tool in self.tools:
            issues = self._tool_tester.analyze_tool_definition(
                tool.name, tool.description, tool.input_schema
            )
            if issues:
                self._tool_tester.propose_improvement(
                    tool.name, tool.description, tool.input_schema, issues
                )
    
    def record_tool_usage(self, tool_name: str, success: bool, error: Optional[str] = None):
        """Record tool usage for self-improvement"""
        self._tool_tester.record_usage(tool_name, success, error=error)
    
    def get_improvement_report(self) -> Dict[str, Any]:
        """Get improvement report for this analyst"""
        return self._tool_tester.get_improvement_report()
