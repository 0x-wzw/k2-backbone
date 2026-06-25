"""
Interleaved Thinking Engine — Extended thinking after tool results.

In Anthropic's system, agents use extended thinking after each tool result
to evaluate quality and refine their next query. This creates a feedback
loop that we implement here.

Pattern: Tool Call → Result → Extended Thinking → Refined Query → Next Tool Call

This replaces the "fire and forget" execution pattern with a reflective loop.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class ThinkingPhase(Enum):
    """Phases of the interleaved thinking cycle"""
    INITIAL = "initial"                     # First analysis pass
    EVALUATE_RESULT = "evaluate_result"     # Evaluate tool output quality
    IDENTIFY_GAPS = "identify_gaps"         # Find what's missing
    REFINE_QUERY = "refine_query"           # Improve the next query
    CROSS_CHECK = "cross_check"             # Verify against other findings
    SYNTHESIZE = "synthesize"               # Combine multiple results


@dataclass
class ThinkingStep:
    """A single thinking step in the interleaved cycle"""
    phase: ThinkingPhase
    input_context: str                       # What triggered this thinking
    thinking: str                            # The extended thinking output
    refined_query: Optional[str] = None      # Refined query for next step
    confidence_delta: float = 0.0            # How confidence changed
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class InterleavedThinkingTrace:
    """
    Full trace of interleaved thinking for a single analysis.
    
    Records every thinking step so we can audit the agent's reasoning
    and understand how it refined its approach.
    """
    analyst_role: str
    initial_query: str
    steps: List[ThinkingStep] = field(default_factory=list)
    final_confidence: float = 0.0
    total_thinking_ms: float = 0.0
    refinement_count: int = 0
    
    def add_step(self, step: ThinkingStep):
        self.steps.append(step)
        self.total_thinking_ms += step.duration_ms
        if step.refined_query:
            self.refinement_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyst_role": self.analyst_role,
            "initial_query": self.initial_query,
            "steps": [
                {
                    "phase": s.phase.value,
                    "input_context": s.input_context[:100],
                    "thinking": s.thinking[:200],
                    "refined_query": s.refined_query,
                    "confidence_delta": s.confidence_delta,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
            "final_confidence": self.final_confidence,
            "total_thinking_ms": self.total_thinking_ms,
            "refinement_count": self.refinement_count,
        }


class InterleavedThinkingEngine:
    """
    Engine that enables interleaved thinking for analyst agents.
    
    After each tool result, the agent:
    1. Evaluates the quality of the result
    2. Identifies gaps or inconsistencies
    3. Refines the next query
    4. Executes the refined query
    
    This loop continues until:
    - Confidence threshold is met
    - Max iterations reached
    - No more refinements possible
    """
    
    def __init__(
        self,
        max_iterations: int = 3,
        confidence_threshold: float = 0.7,
        min_confidence_delta: float = 0.05,
        evaluator: Optional[Callable] = None,
    ):
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.min_confidence_delta = min_confidence_delta
        self.evaluator = evaluator or self._default_evaluator
    
    def run(
        self,
        analyst_role: str,
        initial_query: str,
        execute_fn: Callable[[str], Any],
        initial_confidence: float = 0.5,
    ) -> tuple[Any, InterleavedThinkingTrace]:
        """
        Run an analysis with interleaved thinking.
        
        Args:
            analyst_role: Which analyst is running
            initial_query: The initial query to analyze
            execute_fn: Function that executes a query and returns a result
            initial_confidence: Starting confidence level
            
        Returns:
            (final_result, thinking_trace)
        """
        trace = InterleavedThinkingTrace(
            analyst_role=analyst_role,
            initial_query=initial_query,
        )
        
        current_query = initial_query
        current_confidence = initial_confidence
        all_results = []
        
        for iteration in range(self.max_iterations):
            logger.info(f"  [{analyst_role}] Thinking iteration {iteration + 1}/{self.max_iterations}")
            
            # Step 1: Execute the current query
            start = time.time()
            result = execute_fn(current_query)
            exec_duration = (time.time() - start) * 1000
            all_results.append(result)
            
            # Step 2: Evaluate the result (extended thinking)
            start = time.time()
            evaluation = self._evaluate_result(result, current_query, iteration)
            thinking_duration = (time.time() - start) * 1000
            
            # Step 3: Record the thinking step
            step = ThinkingStep(
                phase=ThinkingPhase.EVALUATE_RESULT if iteration > 0 else ThinkingPhase.INITIAL,
                input_context=f"Iteration {iteration + 1}: {current_query[:80]}",
                thinking=evaluation.get("thinking", "No extended thinking"),
                refined_query=evaluation.get("refined_query"),
                confidence_delta=evaluation.get("confidence_delta", 0.0),
                duration_ms=thinking_duration,
            )
            trace.add_step(step)
            
            # Step 4: Update confidence
            current_confidence += evaluation.get("confidence_delta", 0.0)
            current_confidence = max(0.0, min(1.0, current_confidence))
            
            # Step 5: Check if we should continue
            if current_confidence >= self.confidence_threshold:
                logger.info(f"  [{analyst_role}] Confidence threshold met: {current_confidence:.2f}")
                break
            
            if not evaluation.get("refined_query"):
                logger.info(f"  [{analyst_role}] No refinement suggested, stopping")
                break
            
            if abs(evaluation.get("confidence_delta", 0.0)) < self.min_confidence_delta:
                logger.info(f"  [{analyst_role}] Confidence delta below minimum, stopping")
                break
            
            # Step 6: Refine query for next iteration
            current_query = evaluation["refined_query"]
            logger.info(f"  [{analyst_role}] Refined query: {current_query[:80]}...")
        
        trace.final_confidence = current_confidence
        
        # Merge all results
        final_result = self._merge_results(all_results)
        
        return final_result, trace
    
    def _evaluate_result(
        self,
        result: Any,
        query: str,
        iteration: int,
    ) -> Dict[str, Any]:
        """
        Extended thinking: evaluate the result and decide next steps.
        
        This is where the agent reflects on what it found and decides
        whether to dig deeper, change direction, or stop.
        """
        result_text = str(result) if not hasattr(result, 'findings') else str(result.findings)
        
        # Simulated extended thinking — in production, this would call the LLM
        # with a thinking prompt like: "Evaluate your analysis. What's missing?
        # What would you investigate next? How confident are you?"
        
        evaluation = {
            "thinking": self._generate_thinking(result_text, query, iteration),
            "confidence_delta": self._estimate_confidence_delta(result_text),
            "refined_query": self._generate_refined_query(result_text, query, iteration),
        }
        
        return evaluation
    
    def _generate_thinking(self, result_text: str, query: str, iteration: int) -> str:
        """Generate extended thinking about the result"""
        # In production: LLM call with thinking prompt
        # For now: rule-based thinking simulation
        
        thinking_parts = []
        
        # Quality assessment
        quality_indicators = {
            "high": ["confident", "clear", "strong", "significant", "definitive"],
            "low": ["uncertain", "unclear", "ambiguous", "insufficient", "limited"],
        }
        
        high_count = sum(1 for w in quality_indicators["high"] if w in result_text.lower())
        low_count = sum(1 for w in quality_indicators["low"] if w in result_text.lower())
        
        if high_count > low_count:
            thinking_parts.append(f"Result quality appears high ({high_count} positive signals).")
        elif low_count > high_count:
            thinking_parts.append(f"Result quality needs improvement ({low_count} uncertainty signals).")
        else:
            thinking_parts.append("Result quality is mixed — some signals, some uncertainty.")
        
        # Gap analysis
        gap_words = ["unknown", "gap", "further", "requires", "needs", "unclear", "insufficient"]
        gaps = [w for w in gap_words if w in result_text.lower()]
        if gaps:
            thinking_parts.append(f"Identified gaps: {', '.join(gaps)}. These need further investigation.")
        else:
            thinking_parts.append("No obvious gaps detected in this result.")
        
        # Refinement decision
        if iteration < self.max_iterations - 1 and low_count > high_count:
            thinking_parts.append("Should refine query to address gaps and improve confidence.")
        else:
            thinking_parts.append("Current result is sufficient — no further refinement needed.")
        
        return " ".join(thinking_parts)
    
    def _estimate_confidence_delta(self, result_text: str) -> float:
        """Estimate how confidence should change based on result"""
        positive_signals = ["confident", "clear", "strong", "significant", "definitive", "evidence"]
        negative_signals = ["uncertain", "unclear", "ambiguous", "insufficient", "limited", "unknown"]
        
        pos_count = sum(1 for w in positive_signals if w in result_text.lower())
        neg_count = sum(1 for w in negative_signals if w in result_text.lower())
        
        # Delta ranges from -0.2 to +0.2
        net = (pos_count - neg_count) / max(pos_count + neg_count, 1) * 0.2
        return round(net, 3)
    
    def _generate_refined_query(self, result_text: str, query: str, iteration: int) -> Optional[str]:
        """Generate a refined query based on result evaluation"""
        if iteration >= self.max_iterations - 1:
            return None
        
        # Look for specific refinement signals
        refinement_triggers = [
            "further investigation", "needs more", "requires deeper",
            "unclear", "insufficient data", "additional analysis",
            "cross-reference", "verify", "validate",
        ]
        
        has_refinement = any(t in result_text.lower() for t in refinement_triggers)
        
        if has_refinement:
            # Build a more specific query
            return f"Deep dive: {query} — focus on resolving uncertainties and filling identified gaps"
        
        return None
    
    def _merge_results(self, results: List[Any]) -> Any:
        """Merge multiple iteration results into one"""
        if not results:
            return None
        if len(results) == 1:
            return results[0]
        
        # Take the last result as primary, enrich with earlier findings
        final = results[-1]
        if hasattr(final, 'findings') and hasattr(final, 'evidence'):
            for earlier in results[:-1]:
                if hasattr(earlier, 'evidence') and earlier.evidence:
                    final.evidence.extend(earlier.evidence)
        
        return final
    
    def _default_evaluator(self, result_text: str) -> Dict[str, Any]:
        """Default evaluation logic"""
        return {
            "thinking": "Standard evaluation completed.",
            "confidence_delta": 0.0,
            "refined_query": None,
        }
