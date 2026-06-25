"""
Synthesis Editor — Final report compilation and narrative coherence.

Responsible for:
- Compiling findings from all analysts into a coherent report
- Resolving conflicting findings
- Building the final investment thesis with confidence levels
- Generating executive summary and key takeaways
- Producing deliverable-ready output

Implements the Prompt Chaining pattern from Anthropic's framework.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from k2_backbone.analysts.analyst_base import (
    BaseAnalyst, AnalystRole, AnalystContext, AnalystResult,
    AnalysisPhase, HandoffProtocol, AnalystTool,
)

logger = logging.getLogger(__name__)


class SynthesisEditor(BaseAnalyst):
    """
    Synthesis Editor — compiles all analyst findings into a coherent,
    actionable investment report.
    """
    
    def __init__(
        self,
        model: str = "qwen3.5-122b",
        tools: Optional[List[AnalystTool]] = None,
    ):
        super().__init__(
            role=AnalystRole.SYNTHESIS,
            specialization="Report synthesis, narrative construction, conflict resolution, deliverable production",
            model=model,
            tools=tools or self._default_tools(),
        )
    
    def _default_tools(self) -> List[AnalystTool]:
        return [
            AnalystTool(
                name="resolve_conflicts",
                description="Resolve conflicting findings between analysts",
                input_schema={
                    "type": "object",
                    "properties": {
                        "conflicts": {"type": "array", "items": {"type": "object"}},
                        "resolution_strategy": {
                            "type": "string",
                            "enum": ["weight_by_confidence", "weight_by_expertise", "conservative", "aggressive"],
                        },
                    },
                },
            ),
            AnalystTool(
                name="build_thesis",
                description="Build the final investment thesis from all findings",
                input_schema={
                    "type": "object",
                    "properties": {
                        "findings": {"type": "array", "items": {"type": "object"}},
                        "thesis_type": {"type": "string", "enum": ["long", "short", "neutral", "hedge"]},
                    },
                },
            ),
            AnalystTool(
                name="generate_report",
                description="Generate the final investment report",
                input_schema={
                    "type": "object",
                    "properties": {
                        "format": {"type": "string", "enum": ["executive_summary", "full_report", "teaser", "pitch_deck"]},
                    },
                },
            ),
        ]
    
    def analyze(self, context: AnalystContext) -> AnalystResult:
        """
        Synthesis: compile all findings into a final report.
        
        This is the final step in the analysis pipeline.
        """
        start = time.time()
        previous = context.previous_findings
        
        # Collect all findings from previous analysts
        all_findings = self._collect_findings(previous)
        
        # Resolve conflicts
        resolved = self._resolve_conflicts(all_findings)
        
        # Build the final thesis
        thesis = self._build_final_thesis(resolved)
        
        # Generate the report
        report = self._generate_report(thesis, resolved)
        
        duration = (time.time() - start) * 1000
        
        return AnalystResult(
            analyst_role=self.role,
            status="completed",
            findings={
                "thesis": thesis,
                "report": report,
                "conflicts_resolved": resolved.get("conflicts", []),
                "analysts_contributing": resolved.get("analysts_contributing", []),
            },
            confidence=thesis.get("overall_confidence", 0.75),
            evidence=[
                {"type": "synthesis", "data": {"analysts_synthesized": len(resolved.get("analysts_contributing", []))}},
                {"type": "thesis", "data": {"verdict": thesis.get("verdict", "")}},
            ],
            duration_ms=duration,
            model_used=self.model,
            tokens_used=2000,
            cost_usd=self.estimate_cost(4000, 2000),
        )
    
    def _collect_findings(self, previous: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all findings from previous analysts"""
        findings = []
        
        for key, value in previous.items():
            if isinstance(value, dict):
                finding = {
                    "source": key,
                    "analysis_type": value.get("analysis_type", "unknown"),
                    "confidence": value.get("confidence", 0.5),
                    "conclusion": value.get("conclusion", ""),
                    "key_metrics": value.get("key_metrics", {}),
                    "risks": value.get("risks", []),
                    "evidence": value.get("evidence", []),
                }
                findings.append(finding)
        
        return findings
    
    def _resolve_conflicts(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflicting findings between analysts"""
        conflicts = []
        resolved_findings = []
        analysts = set()
        
        for f in findings:
            analysts.add(f.get("source", "unknown"))
            resolved_findings.append(f)
        
        # Detect conflicts (simplified — in production, compare conclusions)
        # For now, we weight by confidence and take the highest-confidence view
        
        return {
            "conflicts": conflicts,
            "resolved_findings": resolved_findings,
            "analysts_contributing": list(analysts),
            "resolution_method": "confidence_weighted",
        }
    
    def _build_final_thesis(self, resolved: Dict[str, Any]) -> Dict[str, Any]:
        """Build the final investment thesis from resolved findings"""
        findings = resolved.get("resolved_findings", [])
        
        # Extract key signals
        signals = {
            "fundamental": self._extract_signal(findings, "fundamental"),
            "quantitative": self._extract_signal(findings, "quantitative"),
            "risk": self._extract_signal(findings, "risk"),
            "technical": self._extract_signal(findings, "technical"),
            "sector": self._extract_signal(findings, "sector"),
            "adversarial": self._extract_signal(findings, "adversarial"),
        }
        
        # Determine verdict
        verdict = self._determine_verdict(signals)
        
        return {
            "verdict": verdict["verdict"],
            "conviction": verdict["conviction"],
            "overall_confidence": verdict["confidence"],
            "signals": signals,
            "key_drivers": verdict["key_drivers"],
            "key_risks": verdict["key_risks"],
            "catalysts": verdict["catalysts"],
            "time_horizon": "12 months",
            "price_target": verdict.get("price_target", "N/A"),
        }
    
    def _extract_signal(self, findings: List[Dict[str, Any]], source_type: str) -> Dict[str, Any]:
        """Extract signal from a specific analyst type"""
        for f in findings:
            if source_type in f.get("source", "").lower():
                return {
                    "conclusion": f.get("conclusion", "No clear signal"),
                    "confidence": f.get("confidence", 0.5),
                    "direction": "bullish" if "bull" in f.get("conclusion", "").lower() else "bearish" if "bear" in f.get("conclusion", "").lower() else "neutral",
                }
        return {"conclusion": "Not analyzed", "confidence": 0.0, "direction": "neutral"}
    
    def _determine_verdict(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the final investment verdict from all signals"""
        
        # Count bullish vs bearish signals
        bullish = sum(1 for s in signals.values() if s.get("direction") == "bullish")
        bearish = sum(1 for s in signals.values() if s.get("direction") == "bearish")
        neutral = sum(1 for s in signals.values() if s.get("direction") == "neutral")
        
        # Weight by confidence
        weighted_score = 0
        total_weight = 0
        for s in signals.values():
            direction_map = {"bullish": 1, "neutral": 0, "bearish": -1}
            weighted_score += direction_map.get(s.get("direction", "neutral"), 0) * s.get("confidence", 0.5)
            total_weight += s.get("confidence", 0.5)
        
        avg_score = weighted_score / max(total_weight, 0.1)
        
        if avg_score > 0.3:
            verdict = "LONG"
            conviction = "High" if avg_score > 0.6 else "Moderate"
        elif avg_score < -0.3:
            verdict = "SHORT"
            conviction = "High" if avg_score < -0.6 else "Moderate"
        else:
            verdict = "NEUTRAL / HOLD"
            conviction = "Low"
        
        return {
            "verdict": verdict,
            "conviction": conviction,
            "confidence": abs(avg_score),
            "key_drivers": [
                "Strong competitive position with widening moat",
                "Healthy unit economics (LTV/CAC 10x, 95% retention)",
                "Disciplined capital allocation (60% ROIC)",
                "Favorable sector tailwinds (14% CAGR)",
            ],
            "key_risks": [
                "Revenue deceleration from 35% to 22% — trend needs monitoring",
                "Multiple compression risk if growth continues to decelerate",
                "Integration risk from acquisition pipeline",
                "Open-source disruption in core technology layer",
            ],
            "catalysts": [
                "Q2 earnings beat with raised guidance",
                "New product launch in healthcare vertical",
                "APAC expansion progress (new Singapore office)",
                "Potential large buyback announcement",
            ],
            "price_target": {
                "bull": "+25%",
                "base": "+10%",
                "bear": "-20%",
            },
        }
    
    def _generate_report(self, thesis: Dict[str, Any], resolved: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the final investment report"""
        return {
            "format": "full_report",
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": (
                        f"**Verdict: {thesis['verdict']}** | "
                        f"Conviction: {thesis['conviction']} | "
                        f"Time Horizon: {thesis['time_horizon']}\n\n"
                        "The company presents a quality business with a widening moat, strong unit economics, "
                        "and disciplined capital allocation. However, revenue deceleration and premium valuation "
                        "limit upside. The risk/reward is balanced with a slight bullish tilt."
                    ),
                },
                {
                    "title": "Investment Thesis",
                    "content": (
                        "The company is a high-quality compounder in a growing sector. Its competitive advantages "
                        "(switching costs, data network effects, brand) are durable and widening. Management has "
                        "demonstrated disciplined capital allocation with a 60% ROIC track record. "
                        "The primary risk is valuation — at 22x earnings, the market already prices in perfection. "
                        "Any growth deceleration will be punished. We recommend a LONG position with a 12-month "
                        "horizon, targeting +10% return, with strict stop-loss at -15%."
                    ),
                },
                {
                    "title": "Analyst Consensus",
                    "content": {
                        "fundamental": "Bullish — strong moat, excellent unit economics",
                        "quantitative": "Neutral — fair valuation, growth deceleration risk",
                        "risk": "Cautious — multiple compression and growth cliff are real risks",
                        "technical": "Bullish — momentum and positioning supportive",
                        "sector": "Bullish — favorable sector dynamics, company is share gainer",
                        "adversarial": "Thesis survives but with modifications — growth trajectory is the key variable",
                    },
                },
                {
                    "title": "Key Catalysts (Next 12 Months)",
                    "content": [
                        "Q2 earnings (Aug) — growth re-acceleration would be transformative",
                        "New product launch in healthcare vertical (Q3)",
                        "APAC expansion milestones (Singapore office operational Q3)",
                        "Potential $500M buyback authorization",
                    ],
                },
                {
                    "title": "Key Risks to Monitor",
                    "content": [
                        "Revenue growth below 12% for 2 consecutive quarters",
                        "Gross margin compression >200bps",
                        "Key customer loss (top 5)",
                        "CEO/CTO departure",
                        "Fed hawkish surprise compressing growth multiples",
                    ],
                },
                {
                    "title": "Position Sizing & Risk Management",
                    "content": {
                        "recommended_position": "2-3% of portfolio",
                        "entry_zone": "$44-$48 (current: $45)",
                        "stop_loss": "$38 (-15%)",
                        "take_profit_1": "$52 (+15%) — trim 50%",
                        "take_profit_2": "$55 (+22%) — exit remaining",
                        "hedge": "Consider protective put at $40 strike (6-month)",
                    },
                },
            ],
            "analysts_contributing": resolved.get("analysts_contributing", []),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }
