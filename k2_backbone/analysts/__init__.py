"""
K2-Analysts Stack — Multi-Agent Analyst System

A production-grade multi-agent analyst system built on K2-Backbone's swarm
architecture, inspired by Anthropic's system design patterns.

Architecture:
    Augmented LLM Layer → Workflow Patterns → Autonomous Agent Loop
    ─────────────────      ───────────────      ─────────────────────
    Each analyst agent     Orchestrator uses     Analysts operate
    has tools, memory,     prompt chaining,      autonomously within
    and retrieval.         routing, parallel,    their domain, with
                           orchestrator-workers, handoff protocols
                           evaluator-optimizer.  for escalation.

Analyst Roles:
    - Lead Analyst (orchestrator) — decomposes, routes, synthesizes
    - Quantitative Analyst — data modeling, statistical analysis
    - Fundamental Analyst — business model, competitive moat, unit economics
    - Risk Analyst — downside scenarios, black swans, concentration risk
    - Technical Analyst — market structure, on-chain data, technical signals
    - Sector Specialist — domain expertise (semiconductor, fintech, etc.)
    - Devil's Advocate — adversarial stress-test, antithesis construction
    - Synthesis Editor — final report compilation, narrative coherence

Advanced Properties (Anthropic-inspired):
    1. Dynamic Decomposition — spawn subagents mid-execution based on findings
    2. Interleaved Thinking — extended thinking after tool results
    3. Self-Improving Agents — meta-loop for tool quality improvement
    4. Effort Scaling — explicit rules for simple vs complex queries
    5. Citation Handling — dedicated CitationAgent for source attribution

Design Principles (Anthropic):
    1. Augmented LLM as base unit — every analyst has tools + memory + retrieval
    2. Workflow patterns for structured analysis — chaining, routing, parallel
    3. Autonomous loop for open-ended research — analysts self-direct within scope
    4. Handoff protocols between analysts — structured escalation and delegation
    5. Evaluator-optimizer for quality — Devil's Advocate critiques before synthesis
"""

from k2_backbone.analysts.lead_analyst import LeadAnalyst
from k2_backbone.analysts.quant_analyst import QuantAnalyst
from k2_backbone.analysts.fundamental_analyst import FundamentalAnalyst
from k2_backbone.analysts.risk_analyst import RiskAnalyst
from k2_backbone.analysts.technical_analyst import TechnicalAnalyst
from k2_backbone.analysts.sector_specialist import SectorSpecialist
from k2_backbone.analysts.devils_advocate import DevilsAdvocate
from k2_backbone.analysts.synthesis_editor import SynthesisEditor
from k2_backbone.analysts.orchestrator import AnalystOrchestratorV2 as AnalystOrchestrator
from k2_backbone.analysts.analyst_base import BaseAnalyst, AnalystContext, AnalystResult

# Advanced properties
from k2_backbone.analysts.dynamic_decomposition import (
    DynamicDecompositionEngine, DynamicDecompositionPlan,
    SpawnRequest, SpawnReason,
)
from k2_backbone.analysts.interleaved_thinking import (
    InterleavedThinkingEngine, InterleavedThinkingTrace,
    ThinkingStep, ThinkingPhase,
)
from k2_backbone.analysts.self_improving import (
    ToolTestingAgent, SelfImprovingAnalystMixin,
    ToolIssue, ToolIssueType, ToolImprovementProposal,
)
from k2_backbone.analysts.effort_scaling import (
    EffortScalingEngine, EffortBudget,
    ComplexityLevel, EFFORT_BUDGETS,
)
from k2_backbone.analysts.citation_agent import (
    CitationAgent, CitationReport, Citation,
    SourceType, CitationConfidence,
)

__all__ = [
    # Core analysts
    "LeadAnalyst",
    "QuantAnalyst",
    "FundamentalAnalyst",
    "RiskAnalyst",
    "TechnicalAnalyst",
    "SectorSpecialist",
    "DevilsAdvocate",
    "SynthesisEditor",
    "AnalystOrchestrator",  # AnalystOrchestratorV2
    "BaseAnalyst",
    "AnalystContext",
    "AnalystResult",
    
    # Dynamic Decomposition
    "DynamicDecompositionEngine",
    "DynamicDecompositionPlan",
    "SpawnRequest",
    "SpawnReason",
    
    # Interleaved Thinking
    "InterleavedThinkingEngine",
    "InterleavedThinkingTrace",
    "ThinkingStep",
    "ThinkingPhase",
    
    # Self-Improving
    "ToolTestingAgent",
    "SelfImprovingAnalystMixin",
    "ToolIssue",
    "ToolIssueType",
    "ToolImprovementProposal",
    
    # Effort Scaling
    "EffortScalingEngine",
    "EffortBudget",
    "ComplexityLevel",
    "EFFORT_BUDGETS",
    
    # Citation Handling
    "CitationAgent",
    "CitationReport",
    "Citation",
    "SourceType",
    "CitationConfidence",
]
