"""
Lead Analyst — Orchestrator of the analyst team.

Responsible for:
- Decomposing the client's query into structured analysis tasks
- Routing subtasks to the appropriate specialist analysts
- Synthesizing findings into a coherent investment thesis
- Managing the overall analysis workflow

Implements Anthropic's Orchestrator-Worker pattern.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from k2_backbone.analysts.analyst_base import (
    BaseAnalyst, AnalystRole, AnalystContext, AnalystResult,
    AnalysisPhase, HandoffProtocol, AnalystTool,
)

logger = logging.getLogger(__name__)


class LeadAnalyst(BaseAnalyst):
    """
    Lead Analyst — decomposes client queries into structured analysis tasks,
    routes to specialists, and synthesizes the final thesis.
    
    This is the orchestrator in Anthropic's Orchestrator-Worker pattern.
    """
    
    def __init__(
        self,
        model: str = "qwen3.5-122b",
        tools: Optional[List[AnalystTool]] = None,
    ):
        super().__init__(
            role=AnalystRole.LEAD,
            specialization="Investment thesis decomposition, workflow orchestration, synthesis",
            model=model,
            tools=tools or self._default_tools(),
        )
    
    def _default_tools(self) -> List[AnalystTool]:
        return [
            AnalystTool(
                name="decompose_query",
                description="Decompose a complex investment query into structured analysis subtasks",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The investment query to decompose"},
                        "context": {"type": "string", "description": "Additional context about the client or situation"},
                    },
                    "required": ["query"],
                },
            ),
            AnalystTool(
                name="route_subtask",
                description="Route a subtask to the appropriate specialist analyst",
                input_schema={
                    "type": "object",
                    "properties": {
                        "subtask": {"type": "string", "description": "The subtask description"},
                        "target_role": {"type": "string", "description": "Target analyst role"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                    "required": ["subtask", "target_role"],
                },
            ),
            AnalystTool(
                name="synthesize_findings",
                description="Synthesize findings from multiple analysts into a coherent thesis",
                input_schema={
                    "type": "object",
                    "properties": {
                        "findings": {"type": "array", "items": {"type": "object"}},
                        "thesis_type": {"type": "string", "enum": ["long", "short", "neutral", "hedge"]},
                    },
                    "required": ["findings", "thesis_type"],
                },
            ),
        ]
    
    def analyze(self, context: AnalystContext) -> AnalystResult:
        """
        Lead analysis: decompose query, plan workflow, synthesize results.
        
        This implements the Orchestrator-Worker pattern:
        1. Decompose the query into subtasks
        2. Plan the analysis workflow (which analysts, what order)
        3. Route subtasks to specialists
        4. Collect and synthesize findings
        """
        start = time.time()
        query = context.original_query
        
        # Phase 1: Decompose the query
        decomposition = self._decompose_query(query, context)
        
        # Phase 2: Plan the analysis workflow
        workflow_plan = self._plan_workflow(decomposition, context)
        
        # Phase 3: Create handoffs for each subtask
        handoffs = []
        for step in workflow_plan["steps"]:
            handoff = self.handoff(
                protocol=HandoffProtocol.DELEGATE,
                target_role=AnalystRole(step["target_role"]),
                context=context.child(
                    phase=AnalysisPhase(step["phase"]),
                    constraints={"focus": step["focus"]},
                ),
                findings={"decomposition": decomposition, "step": step},
            )
            handoffs.append(handoff)
        
        duration = (time.time() - start) * 1000
        
        return AnalystResult(
            analyst_role=self.role,
            status="completed",
            findings={
                "decomposition": decomposition,
                "workflow_plan": workflow_plan,
                "handoffs": handoffs,
                "thesis_preview": decomposition.get("preliminary_thesis", ""),
            },
            confidence=0.85,
            evidence=[{
                "type": "decomposition",
                "data": decomposition,
                "source": "lead_analyst",
            }],
            handoff={
                "protocol": HandoffProtocol.DELEGATE.value,
                "next_analysts": [h["to_role"] for h in handoffs],
                "parallel_groups": workflow_plan.get("parallel_groups", []),
            },
            duration_ms=duration,
            model_used=self.model,
        )
    
    def _decompose_query(self, query: str, context: AnalystContext) -> Dict[str, Any]:
        """
        Decompose an investment query into structured analysis tasks.
        
        Uses K2-Backbone's decomposition pattern adapted for financial analysis.
        """
        # In production, this would call the LLM with structured output
        # For now, we use a template-based decomposition
        
        # Detect query type
        query_lower = query.lower()
        
        if any(w in query_lower for w in ["ipo", "public offering", "listing"]):
            return self._decompose_ipo(query)
        elif any(w in query_lower for w in ["earnings", "quarterly", "results"]):
            return self._decompose_earnings(query)
        elif any(w in query_lower for w in ["m&a", "merger", "acquisition", "takeover"]):
            return self._decompose_ma(query)
        elif any(w in query_lower for w in ["sector", "industry", "thematic"]):
            return self._decompose_sector(query)
        elif any(w in query_lower for w in ["crypto", "token", "defi", "blockchain"]):
            return self._decompose_crypto(query)
        else:
            return self._decompose_generic(query)
    
    def _decompose_ipo(self, query: str) -> Dict[str, Any]:
        return {
            "query_type": "ipo_analysis",
            "preliminary_thesis": "Evaluate IPO fundamentals, valuation, and market timing",
            "subtasks": [
                {
                    "id": "fundamental_1",
                    "type": "business_model",
                    "description": "Analyze business model, revenue quality, unit economics",
                    "target_role": "fundamental_analyst",
                    "phase": "research",
                    "focus": "business_model_and_competitive_moat",
                },
                {
                    "id": "quant_1",
                    "type": "financial_modeling",
                    "description": "Build DCF, comps analysis, IPO pricing model",
                    "target_role": "quantitative_analyst",
                    "phase": "model",
                    "focus": "valuation_and_financial_projections",
                    "dependencies": ["fundamental_1"],
                },
                {
                    "id": "risk_1",
                    "type": "risk_assessment",
                    "description": "IPO-specific risks: lockup, dilution, market reception",
                    "target_role": "risk_analyst",
                    "phase": "research",
                    "focus": "ipo_risk_factors",
                },
                {
                    "id": "sector_1",
                    "type": "sector_context",
                    "description": "Sector positioning, comp set, market conditions for IPO",
                    "target_role": "sector_specialist",
                    "phase": "research",
                    "focus": "sector_and_market_timing",
                },
                {
                    "id": "devil_1",
                    "type": "adversarial_review",
                    "description": "Stress-test the bull case, identify hidden risks",
                    "target_role": "devils_advocate",
                    "phase": "critique",
                    "focus": "bear_case_construction",
                    "dependencies": ["quant_1", "risk_1", "sector_1"],
                },
            ],
            "workflow": "parallel_research_then_sequential_valuation",
        }
    
    def _decompose_earnings(self, query: str) -> Dict[str, Any]:
        return {
            "query_type": "earnings_analysis",
            "preliminary_thesis": "Evaluate earnings quality, guidance signals, and market reaction",
            "subtasks": [
                {
                    "id": "quant_1",
                    "type": "earnings_quality",
                    "description": "Analyze revenue quality, margin trends, cash flow vs accruals",
                    "target_role": "quantitative_analyst",
                    "phase": "model",
                    "focus": "earnings_quality_and_trends",
                },
                {
                    "id": "fundamental_1",
                    "type": "guidance_analysis",
                    "description": "Evaluate guidance quality, management credibility, forward signals",
                    "target_role": "fundamental_analyst",
                    "phase": "research",
                    "focus": "guidance_and_management_signals",
                },
                {
                    "id": "technical_1",
                    "type": "market_reaction",
                    "description": "Price action, options flow, institutional positioning",
                    "target_role": "technical_analyst",
                    "phase": "research",
                    "focus": "market_reaction_and_positioning",
                },
            ],
            "workflow": "parallel_all",
        }
    
    def _decompose_ma(self, query: str) -> Dict[str, Any]:
        return {
            "query_type": "ma_analysis",
            "preliminary_thesis": "Evaluate deal rationale, synergies, and regulatory risk",
            "subtasks": [
                {
                    "id": "fundamental_1",
                    "type": "strategic_rationale",
                    "description": "Analyze strategic fit, synergy potential, integration risk",
                    "target_role": "fundamental_analyst",
                    "phase": "research",
                    "focus": "strategic_rationale_and_synergies",
                },
                {
                    "id": "quant_1",
                    "type": "deal_valuation",
                    "description": "Accretion/dilution analysis, synergy valuation, deal financing",
                    "target_role": "quantitative_analyst",
                    "phase": "model",
                    "focus": "deal_valuation_and_financing",
                    "dependencies": ["fundamental_1"],
                },
                {
                    "id": "risk_1",
                    "type": "regulatory_risk",
                    "description": "Antitrust, regulatory hurdles, political risk",
                    "target_role": "risk_analyst",
                    "phase": "research",
                    "focus": "regulatory_and_antitrust_risk",
                },
                {
                    "id": "sector_1",
                    "type": "sector_consolidation",
                    "description": "Sector consolidation trends, precedent transactions",
                    "target_role": "sector_specialist",
                    "phase": "research",
                    "focus": "sector_consolidation_and_precedents",
                },
            ],
            "workflow": "parallel_research_then_sequential_valuation",
        }
    
    def _decompose_sector(self, query: str) -> Dict[str, Any]:
        return {
            "query_type": "sector_analysis",
            "preliminary_thesis": "Identify sector structure, key players, and investment themes",
            "subtasks": [
                {
                    "id": "sector_1",
                    "type": "sector_mapping",
                    "description": "Map sector structure, value chain, competitive dynamics",
                    "target_role": "sector_specialist",
                    "phase": "research",
                    "focus": "sector_structure_and_value_chain",
                },
                {
                    "id": "quant_1",
                    "type": "sector_metrics",
                    "description": "Sector-wide financial metrics, growth rates, valuation ranges",
                    "target_role": "quantitative_analyst",
                    "phase": "model",
                    "focus": "sector_financial_benchmarks",
                },
                {
                    "id": "fundamental_1",
                    "type": "company_screening",
                    "description": "Screen for best-in-class companies in the sector",
                    "target_role": "fundamental_analyst",
                    "phase": "research",
                    "focus": "company_screening_and_selection",
                    "dependencies": ["sector_1", "quant_1"],
                },
                {
                    "id": "devil_1",
                    "type": "thesis_stress_test",
                    "description": "Stress-test the sector investment thesis",
                    "target_role": "devils_advocate",
                    "phase": "critique",
                    "focus": "sector_thesis_stress_test",
                    "dependencies": ["fundamental_1"],
                },
            ],
            "workflow": "parallel_research_then_sequential_analysis",
        }
    
    def _decompose_crypto(self, query: str) -> Dict[str, Any]:
        return {
            "query_type": "crypto_analysis",
            "preliminary_thesis": "Evaluate token fundamentals, network metrics, and market structure",
            "subtasks": [
                {
                    "id": "fundamental_1",
                    "type": "token_economics",
                    "description": "Tokenomics, emission schedule, utility, governance",
                    "target_role": "fundamental_analyst",
                    "phase": "research",
                    "focus": "tokenomics_and_utility",
                },
                {
                    "id": "technical_1",
                    "type": "onchain_analysis",
                    "description": "On-chain metrics, wallet distribution, network activity",
                    "target_role": "technical_analyst",
                    "phase": "research",
                    "focus": "onchain_metrics_and_network_health",
                },
                {
                    "id": "quant_1",
                    "type": "token_valuation",
                    "description": "NVT ratio, P/E analogs, discounted cash flow for protocols",
                    "target_role": "quantitative_analyst",
                    "phase": "model",
                    "focus": "token_valuation_models",
                },
                {
                    "id": "risk_1",
                    "type": "crypto_risk",
                    "description": "Smart contract risk, regulatory risk, market structure risk",
                    "target_role": "risk_analyst",
                    "phase": "research",
                    "focus": "crypto_specific_risks",
                },
            ],
            "workflow": "parallel_all",
        }
    
    def _decompose_generic(self, query: str) -> Dict[str, Any]:
        return {
            "query_type": "general_investment_analysis",
            "preliminary_thesis": "Comprehensive investment analysis across all dimensions",
            "subtasks": [
                {
                    "id": "fundamental_1",
                    "type": "business_analysis",
                    "description": "Business model, competitive advantage, management quality",
                    "target_role": "fundamental_analyst",
                    "phase": "research",
                    "focus": "business_and_competitive_analysis",
                },
                {
                    "id": "quant_1",
                    "type": "financial_analysis",
                    "description": "Financial statements, ratios, growth metrics, valuation",
                    "target_role": "quantitative_analyst",
                    "phase": "model",
                    "focus": "financial_analysis_and_valuation",
                },
                {
                    "id": "risk_1",
                    "type": "risk_assessment",
                    "description": "Key risks, downside scenarios, black swans",
                    "target_role": "risk_analyst",
                    "phase": "research",
                    "focus": "comprehensive_risk_assessment",
                },
                {
                    "id": "sector_1",
                    "type": "sector_context",
                    "description": "Sector dynamics, competitive landscape, market position",
                    "target_role": "sector_specialist",
                    "phase": "research",
                    "focus": "sector_and_competitive_landscape",
                },
                {
                    "id": "devil_1",
                    "type": "adversarial_review",
                    "description": "Stress-test the investment thesis",
                    "target_role": "devils_advocate",
                    "phase": "critique",
                    "focus": "thesis_stress_test",
                    "dependencies": ["fundamental_1", "quant_1", "risk_1", "sector_1"],
                },
            ],
            "workflow": "parallel_research_then_critique",
        }
    
    def _plan_workflow(self, decomposition: Dict[str, Any], context: AnalystContext) -> Dict[str, Any]:
        """
        Plan the analysis workflow based on decomposition.
        
        Determines:
        - Which analysts to engage
        - Execution order (parallel vs sequential groups)
        - Dependencies between subtasks
        """
        subtasks = decomposition.get("subtasks", [])
        workflow = decomposition.get("workflow", "parallel_all")
        
        # Build dependency graph
        dependency_map = {}
        for st in subtasks:
            deps = st.get("dependencies", [])
            dependency_map[st["id"]] = deps
        
        # Group by dependency depth
        groups = self._group_by_dependencies(subtasks, dependency_map)
        
        # Determine parallel execution groups
        parallel_groups = []
        for group in groups:
            parallel_groups.append([st["id"] for st in group])
        
        return {
            "workflow_type": workflow,
            "total_steps": len(subtasks),
            "parallel_groups": parallel_groups,
            "steps": subtasks,
            "estimated_duration": f"{len(groups)} sequential phases with parallel execution within each",
            "analysts_needed": list(set(st["target_role"] for st in subtasks)),
        }
    
    def _group_by_dependencies(
        self,
        subtasks: List[Dict[str, Any]],
        dependency_map: Dict[str, List[str]],
    ) -> List[List[Dict[str, Any]]]:
        """Group subtasks by dependency depth for parallel execution"""
        if not subtasks:
            return []
        
        # Build in-degree map
        in_degree = {st["id"]: len(dependency_map.get(st["id"], [])) for st in subtasks}
        dependents = {st["id"]: [] for st in subtasks}
        
        for st in subtasks:
            for dep in dependency_map.get(st["id"], []):
                if dep in dependents:
                    dependents[dep].append(st["id"])
        
        # Topological sort
        groups = []
        subtask_map = {st["id"]: st for st in subtasks}
        ready = [sid for sid, deg in in_degree.items() if deg == 0]
        completed = set()
        
        while ready:
            group = [subtask_map[sid] for sid in ready]
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


import time  # Import at module level for duration calculation
