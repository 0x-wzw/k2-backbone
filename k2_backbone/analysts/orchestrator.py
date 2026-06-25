"""
Analyst Orchestrator v2 — The central coordinator for the K2-Analysts Stack.

Integrates all five Anthropic-inspired properties into the K2-Backbone pipeline:

1. Dynamic Decomposition — spawn subagents mid-execution based on findings
2. Interleaved Thinking — extended thinking after tool results
3. Self-Improving Agents — meta-loop for tool quality improvement
4. Effort Scaling — explicit rules for simple vs complex queries
5. Citation Handling — dedicated CitationAgent for source attribution

Pipeline:
  EffortScaling → LeadAnalyst (decompose)
    → DynamicDecomposition (adaptive spawning)
    → InterleavedThinking (reflective execution)
    → CitationAgent (source attribution)
    → Devil's Advocate (critique)
    → Synthesis Editor (report)
    → Obliviarch (compression)
    → SelfImproving (tool quality audit)
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from k2_backbone.analysts.analyst_base import (
    AnalystRole, AnalystContext, AnalystResult, AnalysisPhase,
    HandoffProtocol, AnalystRegistry,
)
from k2_backbone.analysts.lead_analyst import LeadAnalyst
from k2_backbone.analysts.quant_analyst import QuantAnalyst
from k2_backbone.analysts.fundamental_analyst import FundamentalAnalyst
from k2_backbone.analysts.risk_analyst import RiskAnalyst
from k2_backbone.analysts.technical_analyst import TechnicalAnalyst
from k2_backbone.analysts.sector_specialist import SectorSpecialist
from k2_backbone.analysts.devils_advocate import DevilsAdvocate
from k2_backbone.analysts.synthesis_editor import SynthesisEditor

# Advanced properties
from k2_backbone.analysts.dynamic_decomposition import (
    DynamicDecompositionEngine, DynamicDecompositionPlan, SpawnReason,
)
from k2_backbone.analysts.interleaved_thinking import InterleavedThinkingEngine
from k2_backbone.analysts.self_improving import ToolTestingAgent
from k2_backbone.analysts.effort_scaling import EffortScalingEngine, ComplexityLevel
from k2_backbone.analysts.citation_agent import CitationAgent

logger = logging.getLogger(__name__)


class AnalystOrchestratorV2:
    """
    Orchestrator v2 for the K2-Analysts Stack.
    
    Integrates all five Anthropic-inspired properties into a single pipeline.
    
    Pipeline:
    1. EffortScaling — classify query complexity, allocate budget
    2. LeadAnalyst — decompose into initial subtasks
    3. DynamicDecomposition — execute with adaptive spawning
    4. InterleavedThinking — reflective execution loop
    5. CitationAgent — source attribution on all findings
    6. Devil's Advocate — adversarial stress-test
    7. SynthesisEditor — final report compilation
    8. Obliviarch — memory compression
    9. SelfImproving — tool quality audit
    """
    
    def __init__(
        self,
        enable_obliviarch: bool = True,
        enable_self_improving: bool = True,
        enable_citations: bool = True,
        max_parallel: int = 5,
        output_dir: Optional[str] = None,
    ):
        self.max_parallel = max_parallel
        self.enable_obliviarch = enable_obliviarch
        self.enable_self_improving = enable_self_improving
        self.enable_citations = enable_citations
        self.output_dir = output_dir or str(
            Path.home() / ".openclaw" / "workspace" / "k2-backbone" / "executions" / "analyst_reports"
        )
        
        # Initialize registry
        self.registry = AnalystRegistry()
        self._register_default_analysts()
        
        # Initialize advanced engines
        self.effort_scaler = EffortScalingEngine()
        self.dynamic_decomp = DynamicDecompositionEngine(
            max_dynamic_spawns=5,
            max_depth=3,
        )
        self.thinking_engine = InterleavedThinkingEngine(
            max_iterations=3,
            confidence_threshold=0.7,
        )
        self.tool_tester = ToolTestingAgent(
            min_usage_before_review=5,
            auto_apply=False,
        ) if enable_self_improving else None
        self.citation_agent = CitationAgent(
            require_cross_reference=True,
        ) if enable_citations else None
        
        # Initialize Obliviarch if enabled
        self.obliviarch = None
        if enable_obliviarch:
            try:
                from k2_backbone.memory.obliviarch_adapter import ObliviarchAdapter
                self.obliviarch = ObliviarchAdapter()
                self.obliviarch.initialize()
                logger.info("Obliviarch initialized for analyst memory")
            except ImportError:
                logger.warning("Obliviarch not available, skipping memory compression")
                self.enable_obliviarch = False
        
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def _register_default_analysts(self):
        """Register all default analyst agents"""
        self.registry.register(LeadAnalyst())
        self.registry.register(QuantAnalyst())
        self.registry.register(FundamentalAnalyst())
        self.registry.register(RiskAnalyst())
        self.registry.register(TechnicalAnalyst())
        self.registry.register(SectorSpecialist())
        self.registry.register(DevilsAdvocate())
        self.registry.register(SynthesisEditor())
        
        logger.info(f"Registered {self.registry.count()} analyst agents")
    
    def analyze(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the full analysis pipeline with all five properties.
        
        Args:
            query: The investment query to analyze
            context: Optional context (budget, constraints, preferences)
            
        Returns:
            Complete analysis result with thesis, report, and metadata
        """
        start = time.time()
        task_id = f"analyst_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"{'='*60}")
        logger.info(f"K2-Analysts Stack v2: {task_id}")
        logger.info(f"{'='*60}")
        logger.info(f"Query: {query[:120]}...")
        
        # ── Step 0: Effort Scaling ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 0: Effort Scaling")
        effort_budget = self.effort_scaler.get_budget(query, context)
        analyst_roster = self.effort_scaler.get_analyst_roster(query, context)
        
        logger.info(f"  Complexity: {effort_budget.complexity.value}")
        logger.info(f"  Budget: ${effort_budget.budget_usd} | Analysts: {len(analyst_roster)} ({effort_budget.min_analysts}-{effort_budget.max_analysts})")
        logger.info(f"  Calls: {effort_budget.min_calls}-{effort_budget.max_calls} | Dynamic spawns: {effort_budget.max_dynamic_spawns}")
        logger.info(f"  Roster: {', '.join(analyst_roster)}")
        
        # Create the root context with effort-scaled budget
        root_context = AnalystContext(
            task_id=task_id,
            original_query=query,
            phase=AnalysisPhase.DECOMPOSE,
            constraints=context or {},
            budget={
                "max_cost_usd": effort_budget.budget_usd,
                "max_depth": effort_budget.max_depth,
                "max_analysts": effort_budget.max_analysts,
                "complexity": effort_budget.complexity.value,
            },
        )
        
        # ── Step 1: Decompose (Lead Analyst) ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 1: Decompose — Lead Analyst")
        lead = self.registry.get(AnalystRole.LEAD)
        lead_result = lead.analyze(root_context)
        
        if lead_result.status != "completed":
            return self._error_result(task_id, "Lead analyst decomposition failed", lead_result.error)
        
        decomposition = lead_result.findings
        workflow_plan = decomposition.get("workflow_plan", {})
        initial_steps = workflow_plan.get("steps", [])
        initial_groups = workflow_plan.get("parallel_groups", [])
        
        # Filter steps to only include analysts in the effort-scaled roster
        steps = [s for s in initial_steps if s.get("target_role") in analyst_roster]
        logger.info(f"  Decomposed into {len(initial_steps)} subtasks, filtered to {len(steps)} for effort budget")
        
        # ── Step 2: Dynamic Decomposition + Execution ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 2: Dynamic Decomposition + Execution")
        
        # Create dynamic decomposition plan
        decomp_plan = self.dynamic_decomp.create_plan(steps)
        decomp_plan.max_dynamic_spawns = effort_budget.max_dynamic_spawns
        decomp_plan.max_depth = effort_budget.max_depth
        
        all_results: Dict[str, AnalystResult] = {}
        citation_reports = []
        thinking_traces = []
        dynamic_spawn_log = []
        
        # Build dependency groups from initial + dynamically spawned subtasks
        execution_round = 0
        max_rounds = effort_budget.max_depth + 2  # Prevent infinite loops
        
        while execution_round < max_rounds:
            execution_round += 1
            current_subtasks = decomp_plan.all_subtasks
            
            # Get uncompleted subtasks
            pending = [s for s in current_subtasks if s["id"] not in decomp_plan.completed_subtasks]
            if not pending:
                logger.info(f"  All {len(decomp_plan.completed_subtasks)} subtasks completed")
                break
            
            # Group by dependencies (topological sort)
            groups = self._group_by_dependencies(pending)
            
            logger.info(f"  Execution round {execution_round}: {len(pending)} pending subtasks in {len(groups)} groups")
            
            for group_idx, group in enumerate(groups):
                logger.info(f"    Group {group_idx + 1}/{len(groups)}: {len(group)} subtasks")
                
                # Execute group in parallel
                with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
                    future_map = {}
                    for subtask in group:
                        target_role = subtask.get("target_role", "")
                        focus = subtask.get("focus", "")
                        is_dynamic = subtask.get("spawn_reason", None) is not None
                        
                        # Create child context
                        child_context = root_context.child(
                            phase=AnalysisPhase(subtask.get("phase", "research")),
                            constraints={"focus": focus, "is_dynamic": is_dynamic},
                            metadata={
                                "subtask_id": subtask["id"],
                                "subtask_type": subtask.get("type", ""),
                                "spawn_reason": subtask.get("spawn_reason", "initial"),
                                "trigger_analyst": subtask.get("trigger_analyst", ""),
                            },
                        )
                        child_context.previous_findings = {
                            k: v.to_dict() if isinstance(v, AnalystResult) else v
                            for k, v in all_results.items()
                        }
                        
                        # Get the analyst
                        try:
                            analyst_role = AnalystRole(target_role)
                        except ValueError:
                            logger.warning(f"      Unknown analyst role: {target_role}, skipping")
                            continue
                        
                        analyst = self.registry.get(analyst_role)
                        if not analyst:
                            logger.warning(f"      Analyst not found: {target_role}, skipping")
                            continue
                        
                        # Wrap execution with interleaved thinking
                        future = pool.submit(
                            self._execute_with_thinking,
                            analyst, child_context, subtask,
                        )
                        future_map[future] = (subtask["id"], target_role, is_dynamic)
                    
                    # Collect results
                    for future in as_completed(future_map):
                        subtask_id, role, is_dynamic = future_map[future]
                        try:
                            result, thinking_trace = future.result()
                            all_results[subtask_id] = result
                            decomp_plan.completed_subtasks.append(subtask_id)
                            
                            if thinking_trace:
                                thinking_traces.append(thinking_trace)
                            
                            # Log dynamic spawn info
                            if is_dynamic:
                                spawn_info = subtask.get("spawn_reason", "unknown")
                                trigger = subtask.get("trigger_analyst", "unknown")
                                dynamic_spawn_log.append({
                                    "subtask_id": subtask_id,
                                    "reason": spawn_info,
                                    "triggered_by": trigger,
                                    "confidence": result.confidence,
                                })
                                logger.info(f"      [DYNAMIC] {role} (spawned: {spawn_info}, triggered by: {trigger}) confidence: {result.confidence:.2f}")
                            else:
                                logger.info(f"      {role}: {result.status} (confidence: {result.confidence:.2f})")
                            
                            # ── Citation handling on each result ──
                            if self.enable_citations and self.citation_agent:
                                cit_report = self.citation_agent.process_findings(
                                    task_id, role, result.findings
                                )
                                citation_reports.append(cit_report)
                            
                            # ── Dynamic Decomposition: evaluate result for new spawns ──
                            spawn_requests = self.dynamic_decomp.evaluate_result(
                                decomp_plan, subtask_id, result, role
                            )
                            
                            for req in spawn_requests:
                                if decomp_plan.add_spawn_request(req):
                                    new_subtask = decomp_plan.materialize_spawn(req)
                                    logger.info(f"      → Spawned new subtask '{new_subtask['id']}': {req.suggested_role} ({req.reason.value})")
                                else:
                                    logger.info(f"      → Spawn rejected (at limit): {req.reason.value}")
                            
                            # ── Self-Improving: record tool usage ──
                            if self.tool_tester:
                                self.tool_tester.record_usage(
                                    f"{role}_analysis",
                                    success=(result.status == "completed"),
                                    error=result.error,
                                )
                        
                        except Exception as e:
                            logger.error(f"      {role} failed: {e}")
                            all_results[subtask_id] = AnalystResult(
                                analyst_role=AnalystRole(role),
                                status="failed",
                                findings={"error": str(e)},
                                error=str(e),
                            )
                            decomp_plan.completed_subtasks.append(subtask_id)
        
        # ── Step 3: Devil's Advocate Critique ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 3: Critique — Devil's Advocate")
        devil = self.registry.get(AnalystRole.DEVILS_ADVOCATE)
        if devil and effort_budget.complexity.value in ["moderate", "complex", "very_complex"]:
            critique_context = root_context.child(
                phase=AnalysisPhase.CRITIQUE,
                constraints={"focus": "thesis_stress_test"},
            )
            critique_context.previous_findings = {
                k: v.to_dict() if isinstance(v, AnalystResult) else v
                for k, v in all_results.items()
            }
            critique_result = devil.analyze(critique_context)
            all_results["devil_1"] = critique_result
            logger.info(f"  Devil's Advocate: {critique_result.status} (thesis survival: {critique_result.findings.get('thesis_survival', 'unknown')})")
            
            # Citations for critique
            if self.enable_citations and self.citation_agent:
                cit_report = self.citation_agent.process_findings(
                    task_id, "devils_advocate", critique_result.findings
                )
                citation_reports.append(cit_report)
        else:
            logger.info(f"  Skipped (complexity: {effort_budget.complexity.value})")
        
        # ── Step 4: Synthesize ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 4: Synthesize — Synthesis Editor")
        synthesis = self.registry.get(AnalystRole.SYNTHESIS)
        if synthesis:
            synthesis_context = root_context.child(
                phase=AnalysisPhase.SYNTHESIZE,
                constraints={"focus": "report_generation"},
            )
            synthesis_context.previous_findings = {
                k: v.to_dict() if isinstance(v, AnalystResult) else v
                for k, v in all_results.items()
            }
            synthesis_result = synthesis.analyze(synthesis_context)
            all_results["synthesis"] = synthesis_result
            logger.info(f"  Synthesis: {synthesis_result.status} (verdict: {synthesis_result.findings.get('thesis', {}).get('verdict', 'unknown')})")
        
        # ── Step 5: Merge Citations ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 5: Citation Report")
        merged_citations = None
        if self.enable_citations and self.citation_agent and citation_reports:
            merged_citations = self.citation_agent.merge_reports(citation_reports)
            citation_section = self.citation_agent.generate_citation_section(merged_citations)
            logger.info(f"  Citations: {merged_citations.total_citations} total, {len(merged_citations.high_confidence_citations)} high confidence, {len(merged_citations.uncited_claims)} uncited")
        else:
            citation_section = None
            logger.info("  Citations disabled or no reports to merge")
        
        # ── Step 6: Compress (Obliviarch) ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 6: Compress — Obliviarch")
        obliviarch_id = None
        if self.enable_obliviarch and self.obliviarch:
            try:
                trace = {
                    "task_id": task_id,
                    "query": query,
                    "complexity": effort_budget.complexity.value,
                    "dynamic_spawns": len(decomp_plan.dynamically_spawned),
                    "thinking_iterations": sum(t.refinement_count for t in thinking_traces),
                    "total_citations": merged_citations.total_citations if merged_citations else 0,
                    "results": {k: v.to_dict() for k, v in all_results.items()},
                    "duration_ms": (time.time() - start) * 1000,
                }
                obliviarch_id = self.obliviarch.ingest(task_id, trace)
                logger.info(f"  Compressed: {obliviarch_id}")
            except Exception as e:
                logger.warning(f"  Obliviarch compression failed: {e}")
        else:
            logger.info("  Skipped (disabled)")
        
        # ── Step 7: Self-Improving Report ──
        logger.info(f"\n{'─'*50}")
        logger.info("Step 7: Self-Improving Audit")
        improvement_report = None
        if self.tool_tester:
            improvement_report = self.tool_tester.get_improvement_report()
            logger.info(f"  Tools monitored: {improvement_report['tools_monitored']}")
            logger.info(f"  Issues found: {improvement_report['issues_found']}")
            if improvement_report['issues_found'] > 0:
                logger.info(f"  Proposals made: {improvement_report['proposals_made']}")
                logger.info(f"  Proposals applied: {improvement_report['proposals_applied']}")
        else:
            logger.info("  Skipped (disabled)")
        
        # ── Build Final Result ──
        total_duration = (time.time() - start) * 1000
        
        final_result = {
            "task_id": task_id,
            "query": query,
            "status": "completed",
            "pipeline": "k2_analysts_stack_v2",
            "version": "2.0.0",
            
            # Effort Scaling
            "effort_scaling": {
                "complexity": effort_budget.complexity.value,
                "budget_usd": effort_budget.budget_usd,
                "analyst_roster": analyst_roster,
                "min_analysts": effort_budget.min_analysts,
                "max_analysts": effort_budget.max_analysts,
                "min_calls": effort_budget.min_calls,
                "max_calls": effort_budget.max_calls,
                "max_dynamic_spawns": effort_budget.max_dynamic_spawns,
                "max_depth": effort_budget.max_depth,
            },
            
            # Dynamic Decomposition
            "dynamic_decomposition": {
                "initial_subtasks": len(decomp_plan.initial_subtasks),
                "dynamically_spawned": len(decomp_plan.dynamically_spawned),
                "total_subtasks": decomp_plan.total_subtasks,
                "execution_rounds": execution_round,
                "spawn_log": dynamic_spawn_log,
            },
            
            # Interleaved Thinking
            "interleaved_thinking": {
                "total_traces": len(thinking_traces),
                "total_refinements": sum(t.refinement_count for t in thinking_traces),
                "total_thinking_ms": sum(t.total_thinking_ms for t in thinking_traces),
                "traces": [t.to_dict() for t in thinking_traces[:5]],  # First 5 for brevity
            },
            
            # Citation Handling
            "citations": merged_citations.to_dict() if merged_citations else {"total_citations": 0},
            "citation_section": citation_section,
            
            # Self-Improving
            "self_improving": improvement_report,
            
            # Core analysis
            "analysts_engaged": list(set(
                r.analyst_role.value for r in all_results.values()
            )),
            "lead_analysis": lead_result.to_dict(),
            "analyst_results": {
                k: v.to_dict() for k, v in all_results.items()
                if k not in ["synthesis"]
            },
            "synthesis": synthesis_result.to_dict() if synthesis else None,
            "thesis": synthesis_result.findings.get("thesis", {}) if synthesis else {},
            "report": synthesis_result.findings.get("report", {}) if synthesis else {},
            
            # Memory
            "obliviarch_schema_id": obliviarch_id,
            
            # Performance
            "duration_ms": total_duration,
            "cost_usd": sum(r.cost_usd for r in all_results.values()),
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        # Save to disk
        output_path = Path(self.output_dir) / f"{task_id}.json"
        with open(output_path, "w") as f:
            json.dump(final_result, f, indent=2, default=str)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Analysis Complete: {total_duration:.0f}ms, ${final_result['cost_usd']:.4f}")
        logger.info(f"  Dynamic spawns: {len(decomp_plan.dynamically_spawned)}")
        logger.info(f"  Thinking refinements: {sum(t.refinement_count for t in thinking_traces)}")
        logger.info(f"  Citations: {merged_citations.total_citations if merged_citations else 0}")
        logger.info(f"  Tool issues found: {improvement_report['issues_found'] if improvement_report else 0}")
        logger.info(f"Report saved: {output_path}")
        
        return final_result
    
    def _execute_with_thinking(
        self,
        analyst: Any,
        context: AnalystContext,
        subtask: Dict[str, Any],
    ) -> Tuple[AnalystResult, Any]:
        """
        Execute an analyst's analysis wrapped with interleaved thinking.
        
        For simple queries (trivial/simple), skip thinking to save cost.
        For complex queries, run the full interleaved thinking loop.
        """
        complexity = context.budget.get("complexity", "simple")
        
        # Skip interleaved thinking for trivial/simple queries
        if complexity in ["trivial", "simple"]:
            result = analyst.analyze(context)
            return result, None
        
        # Run with interleaved thinking for moderate+ queries
        def execute_fn(query: str) -> Any:
            # Create a modified context with the refined query
            ctx = context.child(
                phase=context.phase,
                constraints={**context.constraints, "refined_query": query},
            )
            return analyst.analyze(ctx)
        
        initial_query = subtask.get("description", context.original_query)
        result, thinking_trace = self.thinking_engine.run(
            analyst_role=analyst.role.value,
            initial_query=initial_query,
            execute_fn=execute_fn,
            initial_confidence=0.5,
        )
        
        return result, thinking_trace
    
    def _group_by_dependencies(
        self,
        subtasks: List[Dict[str, Any]],
    ) -> List[List[Dict[str, Any]]]:
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
    
    def _error_result(self, task_id: str, message: str, error: Optional[str] = None) -> Dict[str, Any]:
        """Build an error result"""
        return {
            "task_id": task_id,
            "status": "failed",
            "error": message,
            "error_detail": error,
            "pipeline": "k2_analysts_stack_v2",
            "version": "2.0.0",
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def query_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query compressed analyst memory"""
        if self.obliviarch:
            return self.obliviarch.query(query, limit=limit)
        return []
    
    def list_reports(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent analyst reports"""
        import glob
        
        pattern = str(Path(self.output_dir) / "analyst_*.json")
        files = sorted(glob.glob(pattern), reverse=True)[:limit]
        
        reports = []
        for f in files:
            with open(f) as fp:
                data = json.load(fp)
                reports.append({
                    "task_id": data.get("task_id"),
                    "query": data.get("query", "")[:80],
                    "status": data.get("status"),
                    "verdict": data.get("thesis", {}).get("verdict", "N/A"),
                    "complexity": data.get("effort_scaling", {}).get("complexity", "N/A"),
                    "dynamic_spawns": data.get("dynamic_decomposition", {}).get("dynamically_spawned", 0),
                    "citations": data.get("citations", {}).get("total_citations", 0),
                    "duration_ms": data.get("duration_ms"),
                    "cost_usd": data.get("cost_usd"),
                    "generated_at": data.get("generated_at"),
                })
        
        return reports


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    """CLI entry point for the K2-Analysts Stack v2"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="K2-Analysts Stack v2 — Multi-Agent Investment Analysis with Anthropic-inspired properties",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full analysis with all properties
  python -m k2_backbone.analysts.orchestrator "Analyze NVIDIA for a long position"
  
  # Simple query (triggers effort scaling → 1 analyst, no thinking)
  python -m k2_backbone.analysts.orchestrator "What is Apple's P/E ratio?"
  
  # Complex query (triggers dynamic decomposition + interleaved thinking)
  python -m k2_backbone.analysts.orchestrator "Deep dive: Compare Tesla, Rivian, and Lucid with competitive analysis, valuation, and risk scenarios"
  
  # With budget constraint
  python -m k2_backbone.analysts.orchestrator "Is this a good time to buy Bitcoin?" --budget 1.0
  
  # Disable specific properties
  python -m k2_backbone.analysts.orchestrator "Analyze NVIDIA" --no-citations --no-self-improving
  
  # List recent reports
  python -m k2_backbone.analysts.orchestrator --list-reports
        """,
    )
    
    parser.add_argument("query", nargs="?", help="Investment query to analyze")
    parser.add_argument("--budget", type=float, default=None, help="Max cost in USD (overrides effort scaling)")
    parser.add_argument("--no-obliviarch", action="store_true", help="Skip Obliviarch compression")
    parser.add_argument("--no-citations", action="store_true", help="Skip citation handling")
    parser.add_argument("--no-self-improving", action="store_true", help="Skip self-improving audit")
    parser.add_argument("--list-reports", action="store_true", help="List recent reports")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)
    
    if args.list_reports:
        orchestrator = AnalystOrchestratorV2()
        reports = orchestrator.list_reports()
        if not reports:
            print("No reports found.")
        else:
            headers = f"{'Task ID':<30} {'Query':<30} {'Verdict':<14} {'Complexity':<14} {'Spawns':<8} {'Cites':<6} {'Cost':<8} {'Duration':<10}"
            print(headers)
            print("-" * len(headers))
            for r in reports:
                print(f"{r['task_id']:<30} {r['query']:<30} {r['verdict']:<14} {r['complexity']:<14} {r['dynamic_spawns']:<8} {r['citations']:<6} ${r['cost_usd']:<5.4f} {r['duration_ms']:<10.0f}ms")
        return
    
    if not args.query:
        parser.print_help()
        return
    
    # Build context
    context = {}
    if args.budget is not None:
        context["budget"] = {"max_cost_usd": args.budget}
    
    # Run analysis
    orchestrator = AnalystOrchestratorV2(
        enable_obliviarch=not args.no_obliviarch,
        enable_self_improving=not args.no_self_improving,
        enable_citations=not args.no_citations,
    )
    
    result = orchestrator.analyze(args.query, context=context)
    
    # Print summary
    if result["status"] == "failed":
        print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
        return
    
    thesis = result.get("thesis", {})
    report = result.get("report", {})
    effort = result.get("effort_scaling", {})
    dynamic = result.get("dynamic_decomposition", {})
    citations = result.get("citations", {})
    
    print(f"\n{'='*70}")
    print(f"📊 K2-Analysts Stack v2 — Analysis Complete")
    print(f"{'='*70}")
    print(f"Query: {result['query']}")
    print(f"Verdict: {thesis.get('verdict', 'N/A')} (Conviction: {thesis.get('conviction', 'N/A')})")
    print(f"{'─'*70}")
    print(f"Effort Scaling: {effort.get('complexity', 'N/A')} | Budget: ${effort.get('budget_usd', 0):.2f}")
    print(f"Dynamic Spawns: {dynamic.get('dynamically_spawned', 0)} | Total Subtasks: {dynamic.get('total_subtasks', 0)}")
    print(f"Citations: {citations.get('total_citations', 0)} | Uncited Claims: {len(citations.get('uncited_claims_list', []))}")
    print(f"Analysts: {', '.join(result.get('analysts_engaged', []))}")
    print(f"Duration: {result['duration_ms']:.0f}ms | Cost: ${result['cost_usd']:.4f}")
    
    if report:
        sections = report.get("sections", [])
        for section in sections:
            print(f"\n── {section['title']} ──")
            content = section.get("content", "")
            if isinstance(content, str):
                print(content[:400] + "..." if len(content) > 400 else content)
            elif isinstance(content, dict):
                for k, v in list(content.items())[:5]:
                    print(f"  {k}: {v}")
            elif isinstance(content, list):
                for item in content[:3]:
                    print(f"  • {item}")
    
    # Print citation section if available
    if result.get("citation_section"):
        print(f"\n── Sources & Citations ──")
        print(result["citation_section"][:500] + "..." if len(result["citation_section"]) > 500 else result["citation_section"])
    
    print(f"\n{'='*70}")
    
    # Save output if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Full report saved to: {args.output}")


if __name__ == "__main__":
    main()
