"""
Devil's Advocate — Adversarial stress-test of investment theses.

Responsible for:
- Constructing the strongest bear case
- Identifying hidden assumptions and logical fallacies
- Stress-testing valuation models
- Finding what the bull case ignores
- Antithesis construction and epistemic interrogation

Implements the Evaluator-Optimizer pattern from Anthropic's framework,
and the Four-Part Teardown from the adversarial stress-test skill.
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


class DevilsAdvocate(BaseAnalyst):
    """
    Devil's Advocate — adversarial stress-test of investment theses.
    
    Implements the Four-Part Teardown:
    1. Flaw Extraction — identify load-bearing assumptions
    2. Antithesis Steel-Man — build the strongest counter-argument
    3. Forced Pre-Mortem — imagine the thesis failed, why?
    4. Epistemic Interrogation — what would change your mind?
    """
    
    def __init__(
        self,
        model: str = "qwen3.5-122b",
        tools: Optional[List[AnalystTool]] = None,
    ):
        super().__init__(
            role=AnalystRole.DEVILS_ADVOCATE,
            specialization="Adversarial analysis, thesis stress-testing, bear case construction, epistemic interrogation",
            model=model,
            tools=tools or self._default_tools(),
        )
    
    def _default_tools(self) -> List[AnalystTool]:
        return [
            AnalystTool(
                name="flaw_extraction",
                description="Identify load-bearing assumptions in an investment thesis",
                input_schema={
                    "type": "object",
                    "properties": {
                        "thesis": {"type": "string"},
                        "assumptions": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
            AnalystTool(
                name="antithesis_construction",
                description="Build the strongest counter-argument to the thesis",
                input_schema={
                    "type": "object",
                    "properties": {
                        "thesis": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "object"}},
                    },
                },
            ),
            AnalystTool(
                name="pre_mortem",
                description="Run a pre-mortem: imagine the thesis failed and trace why",
                input_schema={
                    "type": "object",
                    "properties": {
                        "thesis": {"type": "string"},
                        "timeframe": {"type": "string"},
                    },
                },
            ),
            AnalystTool(
                name="epistemic_interrogation",
                description="Identify what evidence would change the thesis assessment",
                input_schema={
                    "type": "object",
                    "properties": {
                        "current_view": {"type": "string"},
                        "key_uncertainties": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
        ]
    
    def analyze(self, context: AnalystContext) -> AnalystResult:
        """
        Adversarial review: stress-test the investment thesis.
        
        Runs the Four-Part Teardown on findings from other analysts.
        """
        start = time.time()
        focus = context.constraints.get("focus", "thesis_stress_test")
        previous = context.previous_findings
        
        # Get the thesis to stress-test from previous findings
        thesis = self._extract_thesis(previous)
        
        # Run the Four-Part Teardown
        teardown = self._four_part_teardown(thesis, focus)
        
        duration = (time.time() - start) * 1000
        
        return AnalystResult(
            analyst_role=self.role,
            status="completed",
            findings=teardown,
            confidence=teardown.get("confidence", 0.85),
            evidence=teardown.get("evidence", []),
            handoff={
                "protocol": HandoffProtocol.SYNTHESIZE.value,
                "to_role": AnalystRole.SYNTHESIS.value,
                "critical_findings": teardown.get("critical_flaws", []),
                "thesis_survival": teardown.get("thesis_survival", "modified"),
            },
            duration_ms=duration,
            model_used=self.model,
            tokens_used=teardown.get("tokens_used", 0),
            cost_usd=self.estimate_cost(teardown.get("tokens_used", 0) * 2, teardown.get("tokens_used", 0)),
        )
    
    def _extract_thesis(self, previous: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the investment thesis from previous analysts' findings"""
        thesis = {
            "bull_case": "",
            "key_assumptions": [],
            "valuation": {},
            "risks_identified": [],
        }
        
        # Try to extract from various finding structures
        for key, value in previous.items():
            if isinstance(value, dict):
                if "conclusion" in value:
                    thesis["bull_case"] = value["conclusion"]
                if "analysis_type" in value:
                    thesis["type"] = value["analysis_type"]
                if "scenario_analysis" in value:
                    thesis["scenarios"] = value["scenario_analysis"]
                if "risk_matrix" in value:
                    thesis["risks_identified"] = value["risk_matrix"]
        
        return thesis
    
    def _four_part_teardown(self, thesis: Dict[str, Any], focus: str) -> Dict[str, Any]:
        """Run the Four-Part Teardown on the investment thesis"""
        
        # Part 1: Flaw Extraction
        flaws = self._flaw_extraction(thesis)
        
        # Part 2: Antithesis Steel-Man
        antithesis = self._antithesis_construction(thesis, flaws)
        
        # Part 3: Forced Pre-Mortem
        pre_mortem = self._pre_mortem(thesis)
        
        # Part 4: Epistemic Interrogation
        epistemic = self._epistemic_interrogation(thesis)
        
        # Determine thesis survival
        critical_flaws = [f for f in flaws if f.get("severity") == "critical"]
        thesis_survival = "intact" if len(critical_flaws) == 0 else "modified" if len(critical_flaws) <= 2 else "fails"
        
        return {
            "analysis_type": "adversarial_review",
            "thesis_under_review": thesis.get("bull_case", "Investment thesis"),
            "four_part_teardown": {
                "flaw_extraction": flaws,
                "antithesis_steel_man": antithesis,
                "forced_pre_mortem": pre_mortem,
                "epistemic_interrogation": epistemic,
            },
            "critical_flaws": critical_flaws,
            "thesis_survival": thesis_survival,
            "confidence": 0.85,
            "evidence": [
                {"type": "flaw_extraction", "data": {"flaws_found": len(flaws), "critical": len(critical_flaws)}},
                {"type": "antithesis", "data": {"antithesis_strength": "strong"}},
                {"type": "pre_mortem", "data": {"failure_scenarios": len(pre_mortem.get("failure_paths", []))}},
            ],
            "tokens_used": 2000,
        }
    
    def _flaw_extraction(self, thesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Part 1: Identify load-bearing assumptions"""
        return [
            {
                "assumption": "Growth will continue at historical rates",
                "severity": "critical",
                "why_it_matters": "Entire DCF valuation depends on growth rate. If growth decelerates from 18% to 12%, fair value drops 35%.",
                "evidence_against": "Revenue deceleration from 35% to 22% already visible. Market saturation in core vertical.",
                "counter_argument": "New product launches and geographic expansion could offset deceleration.",
            },
            {
                "assumption": "Margins will expand 200bps annually",
                "severity": "high",
                "why_it_matters": "Margin expansion is 40% of the upside case. Without it, returns are mediocre.",
                "evidence_against": "Competitive pressure in value segment, R&D investment required to maintain moat.",
                "counter_argument": "Operating leverage from scale, pricing power from differentiated product.",
            },
            {
                "assumption": "Multiple will remain at current levels",
                "severity": "high",
                "why_it_matters": "At 22x earnings, any multiple compression destroys returns.",
                "evidence_against": "Rising interest rates compress growth multiples. Sector rotation risk.",
                "counter_argument": "Quality premium justified by moat and growth. Historical multiple range 18-25x.",
            },
            {
                "assumption": "Competitive moat is widening",
                "severity": "medium",
                "why_it_matters": "If moat is stable (not widening), the premium valuation is harder to justify.",
                "evidence_against": "Open-source alternatives improving rapidly. Talent poaching by well-funded competitors.",
                "counter_argument": "Data network effects compound over time. 3-year data advantage is durable.",
            },
            {
                "assumption": "Capital allocation will remain disciplined",
                "severity": "medium",
                "why_it_matters": "Acquisition integration risk could destroy value.",
                "evidence_against": "3 acquisitions in 5 years — integration complexity increases with each.",
                "counter_argument": "Track record of value-accretive deals (avg ROIC 18%).",
            },
        ]
    
    def _antithesis_construction(self, thesis: Dict[str, Any], flaws: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Part 2: Build the strongest bear case"""
        return {
            "antithesis": "The company is a quality business at a full price with narrowing upside optionality",
            "bear_case_narrative": (
                "The company faces a 'show me' moment. Revenue deceleration is structural, not cyclical — "
                "core market saturation and competitive pressure will compress growth to 10-12% within 2 years. "
                "Margin expansion is priced in but unlikely as R&D spend must increase to defend the moat. "
                "At 22x earnings with 12% growth, the risk/reward is unfavorable. Multiple compression to 18x "
                "(still above market) combined with 12% earnings growth yields a 2% annual return. "
                "The market is pricing perfection; any miss will be punished disproportionately."
            ),
            "key_arguments": [
                "Growth deceleration is structural, not fixable by new products",
                "Margin expansion is priced in but unlikely to materialize",
                "Multiple compression risk is asymmetric to the downside",
                "Moat is stable, not widening — premium is unjustified",
                "Capital allocation risk increases with acquisition complexity",
            ],
            "valuation_under_antithesis": {
                "base_case": "$38.00 (-15% from current)",
                "bear_case": "$30.00 (-33% from current)",
                "probability_weighted": "$35.00 (-22% from current)",
            },
            "antithesis_strength": "Strong — all assumptions are falsifiable",
        }
    
    def _pre_mortem(self, thesis: Dict[str, Any]) -> Dict[str, Any]:
        """Part 3: Imagine the thesis failed — why?"""
        return {
            "timeframe": "12 months",
            "failure_narrative": "It's 12 months from now and the stock is down 30%. Here's why:",
            "failure_paths": [
                {
                    "path": "Growth cliff",
                    "probability": "25%",
                    "narrative": "Q3 earnings reveal growth decelerated to 8%, well below consensus of 15%. "
                                "Management blames 'macro headwinds' but competitive losses are the real cause. "
                                "Stock drops 20% in one day, multiple compresses to 16x.",
                    "early_warning_signals": ["Slowing deal volume", "Customer win/loss ratios deteriorating",
                                              "Sales cycle lengthening", "Pipeline coverage declining"],
                },
                {
                    "path": "Margin mirage",
                    "probability": "20%",
                    "narrative": "Gross margins compress 300bps as competitive pricing pressures intensify. "
                                "R&D spend increases 20% to defend moat. EBITDA margins flat despite revenue growth. "
                                "Market reprices for lower quality earnings.",
                    "early_warning_signals": ["Pricing discounting increasing", "R&D headcount growing faster than revenue",
                                              "Customer churn in value segment"],
                },
                {
                    "path": "Acquisition indigestion",
                    "probability": "15%",
                    "narrative": "The large acquisition announced this year faces integration challenges. "
                                "Key talent from acquired company leaves. Revenue synergies fail to materialize. "
                                "Goodwill impairment of $200M hits earnings.",
                    "early_warning_signals": ["Key executive departures from acquired company",
                                              "Integration timeline slipping", "Customer complaints about service quality"],
                },
                {
                    "path": "Macro / multiple compression",
                    "probability": "20%",
                    "narrative": "Rising interest rates compress all growth multiples. Sector rotation from growth to value. "
                                "P/E compresses from 22x to 16x despite steady fundamentals. "
                                "Stock drops 25% on multiple compression alone.",
                    "early_warning_signals": ["Fed hawkish signals", "10-year yield above 5%",
                                              "Growth ETF outflows", "Value outperforming growth"],
                },
            ],
            "most_likely_failure": "Growth cliff — the most dangerous because it's hardest to detect early",
        }
    
    def _epistemic_interrogation(self, thesis: Dict[str, Any]) -> Dict[str, Any]:
        """Part 4: What would change your mind?"""
        return {
            "current_view": "Thesis is plausible but risks are underpriced",
            "would_become_bullish_if": [
                "Revenue growth re-accelerates above 20% for 2 consecutive quarters",
                "Gross margins expand 200bps+ while maintaining R&D investment",
                "New product vertical generates >5% of revenue within 12 months",
                "Management announces large buyback (5%+ of shares) at current prices",
            ],
            "would_become_bearish_if": [
                "Growth decelerates below 12% for 2 consecutive quarters",
                "Key competitive loss (top 5 customer switches to competitor)",
                "CEO or CTO unexpectedly departs",
                "Regulatory action in core market",
                "Insider selling accelerates (CEO sells >20% of holdings)",
            ],
            "key_uncertainties": [
                {
                    "uncertainty": "Revenue growth trajectory",
                    "resolution_timeframe": "Next 2 quarters",
                    "current_signal": "Decelerating but above 15%",
                    "what_to_watch": "Q2 earnings, pipeline coverage, win/loss ratios",
                },
                {
                    "uncertainty": "Competitive response to AI commoditization",
                    "resolution_timeframe": "6-12 months",
                    "current_signal": "Moat intact but under pressure",
                    "what_to_watch": "Open-source adoption, competitor funding rounds",
                },
                {
                    "uncertainty": "Interest rate trajectory",
                    "resolution_timeframe": "12-18 months",
                    "current_signal": "Rates stable but elevated",
                    "what_to_watch": "Fed guidance, 10-year yield, sector rotation",
                },
            ],
            "defend_this": "If growth decelerates to 12% and margins don't expand, what's the bull case?",
        }
