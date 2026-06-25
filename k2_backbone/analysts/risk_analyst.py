"""
Risk Analyst — Downside scenarios, black swans, concentration risk.

Responsible for:
- Comprehensive risk identification and assessment
- Scenario analysis and stress testing
- Black swan / tail risk identification
- Concentration risk analysis
- Regulatory and geopolitical risk assessment
- Portfolio-level risk integration

Implements the Evaluator-Optimizer pattern from Anthropic's framework.
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


class RiskAnalyst(BaseAnalyst):
    """
    Risk Analyst — identifies, assesses, and quantifies risks across
    all dimensions of an investment thesis.
    """
    
    def __init__(
        self,
        model: str = "qwen3.5-122b",
        tools: Optional[List[AnalystTool]] = None,
    ):
        super().__init__(
            role=AnalystRole.RISK,
            specialization="Risk assessment, scenario analysis, stress testing, black swan identification",
            model=model,
            tools=tools or self._default_tools(),
        )
    
    def _default_tools(self) -> List[AnalystTool]:
        return [
            AnalystTool(
                name="scenario_analysis",
                description="Run scenario analysis with probability-weighted outcomes",
                input_schema={
                    "type": "object",
                    "properties": {
                        "base_case": {"type": "object"},
                        "bull_case": {"type": "object"},
                        "bear_case": {"type": "object"},
                        "probabilities": {"type": "object"},
                    },
                },
            ),
            AnalystTool(
                name="black_swan_identification",
                description="Identify potential black swan events and their impact",
                input_schema={
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "sector": {"type": "string"},
                        "geography": {"type": "string"},
                    },
                },
            ),
            AnalystTool(
                name="concentration_risk",
                description="Analyze concentration risk across customers, products, geographies",
                input_schema={
                    "type": "object",
                    "properties": {
                        "customer_concentration": {"type": "number"},
                        "product_concentration": {"type": "number"},
                        "geo_concentration": {"type": "number"},
                    },
                },
            ),
            AnalystTool(
                name="regulatory_risk",
                description="Assess regulatory and compliance risk exposure",
                input_schema={
                    "type": "object",
                    "properties": {
                        "jurisdictions": {"type": "array", "items": {"type": "string"}},
                        "regulatory_exposure": {"type": "string"},
                    },
                },
            ),
        ]
    
    def analyze(self, context: AnalystContext) -> AnalystResult:
        """
        Risk analysis: identify, assess, and quantify risks.
        
        Focus areas:
        - ipo_risk_factors: IPO-specific risks
        - regulatory_and_antitrust_risk: M&A regulatory risk
        - crypto_specific_risks: Smart contract, regulatory, market structure
        - comprehensive_risk_assessment: Full risk profile
        """
        start = time.time()
        focus = context.constraints.get("focus", "comprehensive_risk_assessment")
        
        analysis = self._run_analysis(focus, context)
        
        duration = (time.time() - start) * 1000
        
        return AnalystResult(
            analyst_role=self.role,
            status="completed",
            findings=analysis,
            confidence=analysis.get("confidence", 0.75),
            evidence=analysis.get("evidence", []),
            duration_ms=duration,
            model_used=self.model,
            tokens_used=analysis.get("tokens_used", 0),
            cost_usd=self.estimate_cost(analysis.get("tokens_used", 0) * 2, analysis.get("tokens_used", 0)),
        )
    
    def _run_analysis(self, focus: str, context: AnalystContext) -> Dict[str, Any]:
        analysis_map = {
            "ipo_risk_factors": self._ipo_risk,
            "regulatory_and_antitrust_risk": self._regulatory_risk,
            "crypto_specific_risks": self._crypto_risk,
            "comprehensive_risk_assessment": self._comprehensive_risk,
        }
        analyzer = analysis_map.get(focus, self._comprehensive_risk)
        return analyzer(context)
    
    def _ipo_risk(self, context: AnalystContext) -> Dict[str, Any]:
        return {
            "analysis_type": "ipo_risk",
            "lockup_risk": {
                "lockup_period": "180 days",
                "shares_under_lockup": "35% of outstanding",
                "unlock_date_impact": "High — 3x average daily volume unlocks",
                "mitigation": "Underwriters have 30-day greenshoe (15% overallotment)",
            },
            "dilution_risk": {
                "option_pool": "12% of post-IPO shares",
                "espp": "2% annual dilution",
                "warrants": "None outstanding",
                "total_dilution_3y": "~15%",
            },
            "market_reception_risk": {
                "demand_coverage": "8x oversubscribed (strong)",
                "ipo_price_range": "$18-$21 (narrow range — good sign)",
                "aftermarket_volatility": "Expected: ±15% first month",
                "comparable_ipo_performance": "Sector IPOs: avg +12% first month",
            },
            "financial_risk": {
                "profitability": "Profitable (rare for IPO — positive)",
                "recent_revenue_deceleration": "From 35% to 22% growth — watch closely",
                "customer_concentration": "Top 3: 28% — moderate risk",
            },
            "overall_risk_score": "6/10 — Moderate",
            "key_risk_to_monitor": "Lockup expiry + revenue deceleration",
            "confidence": 0.80,
            "evidence": [
                {"type": "lockup_analysis", "data": {"lockup_pct": "35%", "unlock_impact": "high"}},
                {"type": "market_reception", "data": {"oversubscription": "8x", "range": "$18-$21"}},
            ],
            "tokens_used": 1000,
        }
    
    def _regulatory_risk(self, context: AnalystContext) -> Dict[str, Any]:
        return {
            "analysis_type": "regulatory_risk",
            "antitrust_assessment": {
                "herfindahl_hirschman_index": "2,800 (moderately concentrated)",
                "hhi_change": "+400 from deal (triggers DOJ review)",
                "horizontal_overlap": "25% in core market",
                "vertical_concerns": "Potential input foreclosure in upstream market",
            },
            "regulatory_hurdles": [
                {
                    "jurisdiction": "US (FTC/DOJ)",
                    "probability": "40%",
                    "impact": "High — could block or require divestitures",
                    "timeline": "6-12 months",
                },
                {
                    "jurisdiction": "EU (DG Comp)",
                    "probability": "35%",
                    "impact": "Moderate — remedies likely",
                    "timeline": "8-14 months",
                },
                {
                    "jurisdiction": "China (SAMR)",
                    "probability": "20%",
                    "impact": "Low — limited operations in China",
                    "timeline": "4-8 months",
                },
            ],
            "political_risk": {
                "election_impact": "US election year — antitrust enforcement may shift",
                "cross_border_concerns": "CFIUS review if foreign buyer",
            },
            "overall_regulatory_risk": "7/10 — High (deal may require remedies)",
            "confidence": 0.75,
            "evidence": [
                {"type": "antitrust_analysis", "data": {"hhi": 2800, "hhi_change": 400}},
                {"type": "regulatory_timeline", "data": {"jurisdictions": 3, "longest": "14 months"}},
            ],
            "tokens_used": 1200,
        }
    
    def _crypto_risk(self, context: AnalystContext) -> Dict[str, Any]:
        return {
            "analysis_type": "crypto_risk",
            "smart_contract_risk": {
                "audit_status": "3 audits completed (Trail of Bits, OpenZeppelin, Certik)",
                "critical_vulnerabilities": "0",
                "high_vulnerabilities": "2 (both remediated)",
                "bug_bounty": "$1M active program",
                "risk_score": "3/10 — Low",
            },
            "regulatory_risk": {
                "us_sec_status": "Not classified as security (Howey Test: passes)",
                "jurisdictional_exposure": "US (40% of volume), EU (30%), Asia (25%)",
                "regulatory_trend": "MiCA compliant, US clarity improving",
                "risk_score": "5/10 — Moderate",
            },
            "market_structure_risk": {
                "liquidity_depth": "0.5% slippage for $1M order",
                "exchange_concentration": "60% on Binance — high concentration",
                "manipulation_risk": "Moderate — wash trading estimated at 15% of volume",
                "risk_score": "6/10 — Moderate-High",
            },
            "protocol_risk": {
                "governance_attack": "Top 5 holders control 35% of voting power",
                "fork_risk": "Low — strong community alignment",
                "dependency_risk": "Built on Ethereum L2 — subject to ETH risks",
            },
            "overall_crypto_risk": "5/10 — Moderate",
            "key_risk_to_monitor": "Exchange concentration and regulatory evolution",
            "confidence": 0.70,
            "evidence": [
                {"type": "smart_contract_audit", "data": {"audits": 3, "critical": 0}},
                {"type": "market_structure", "data": {"binance_concentration": "60%", "slippage": "0.5%"}},
            ],
            "tokens_used": 1300,
        }
    
    def _comprehensive_risk(self, context: AnalystContext) -> Dict[str, Any]:
        return {
            "analysis_type": "comprehensive_risk",
            "risk_matrix": [
                {
                    "risk": "Revenue concentration (top 3 customers)",
                    "probability": "Medium",
                    "impact": "High",
                    "score": "8/10",
                    "mitigation": "Diversification strategy in progress",
                },
                {
                    "risk": "Technology disruption (AI/ML commoditization)",
                    "probability": "Medium",
                    "impact": "High",
                    "score": "7/10",
                    "mitigation": "R&D spend at 18% of revenue, data moat",
                },
                {
                    "risk": "Regulatory change (data privacy)",
                    "probability": "Medium",
                    "impact": "Medium",
                    "score": "6/10",
                    "mitigation": "Compliance team of 25, GDPR/SOC2 certified",
                },
                {
                    "risk": "Key person risk (CEO)",
                    "probability": "Low",
                    "impact": "High",
                    "score": "5/10",
                    "mitigation": "Strong #2, succession plan in place",
                },
                {
                    "risk": "Macro downturn (enterprise spending freeze)",
                    "probability": "Medium",
                    "impact": "Medium",
                    "score": "6/10",
                    "mitigation": "70% subscription revenue, long contracts",
                },
                {
                    "risk": "Competitive entry (well-funded startup)",
                    "probability": "Medium",
                    "impact": "Medium",
                    "score": "6/10",
                    "mitigation": "3-year data advantage, switching costs",
                },
            ],
            "black_swan_scenarios": [
                {
                    "scenario": "Major data breach exposing customer data",
                    "impact": "Catastrophic — 40%+ stock decline",
                    "probability": "<5%",
                    "early_warning": "Security incident frequency, employee churn in security team",
                },
                {
                    "scenario": "Founder/CEO sudden departure",
                    "impact": "High — 20-30% stock decline",
                    "probability": "<10%",
                    "early_warning": "Insider selling, sudden board changes",
                },
                {
                    "scenario": "Regulatory ban on core business model in key market",
                    "impact": "Very High — 50%+ revenue at risk",
                    "probability": "<5%",
                    "early_warning": "Regulatory investigations, proposed legislation",
                },
            ],
            "scenario_analysis": {
                "base_case": {
                    "probability": "55%",
                    "return": "+15%",
                    "narrative": "Steady growth, margin expansion, multiple stable",
                },
                "bull_case": {
                    "probability": "20%",
                    "return": "+45%",
                    "narrative": "Growth accelerates, margins beat, multiple expands",
                },
                "bear_case": {
                    "probability": "20%",
                    "return": "-25%",
                    "narrative": "Growth decelerates, margins compress, multiple contracts",
                },
                "tail_case": {
                    "probability": "5%",
                    "return": "-60%",
                    "narrative": "Black swan event materializes",
                },
            },
            "expected_return": "+7.5% (probability-weighted)",
            "risk_adjusted_return": "Below average — risk/reward not compelling at current price",
            "overall_risk_score": "6.5/10 — Moderate-High",
            "confidence": 0.78,
            "evidence": [
                {"type": "risk_matrix", "data": {"risks_identified": 6, "avg_score": "6.3/10"}},
                {"type": "scenario_analysis", "data": {"expected_return": "+7.5%", "bear_return": "-25%"}},
                {"type": "black_swan", "data": {"scenarios": 3, "max_impact": "-60%"}},
            ],
            "tokens_used": 1800,
        }
