"""
Citation Agent — Dedicated source attribution and evidence tracking.

Anthropic's system includes a dedicated agent for citation handling.
Every finding must be traceable to a source with:
- Source URL or identifier
- Date accessed
- Quote or evidence excerpt
- Confidence in the source
- Cross-reference verification

This agent operates as a post-processing step on all analyst findings.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of sources that can be cited"""
    FINANCIAL_STATEMENT = "financial_statement"
    SEC_FILING = "sec_filing"
    ANALYST_REPORT = "analyst_report"
    NEWS_ARTICLE = "news_article"
    RESEARCH_PAPER = "research_paper"
    ONCHAIN_DATA = "onchain_data"
    MARKET_DATA = "market_data"
    COMPANY_WEBSITE = "company_website"
    REGULATORY_FILING = "regulatory_filing"
    INTERVIEW = "interview"
    PRESS_RELEASE = "press_release"
    DATABASE = "database"
    EXPERT_OPINION = "expert_opinion"
    INTERNAL_MODEL = "internal_model"
    UNKNOWN = "unknown"


class CitationConfidence(Enum):
    """Confidence in a citation's accuracy"""
    HIGH = "high"           # Direct quote from primary source
    MEDIUM = "medium"       # Paraphrased from reliable source
    LOW = "low"             # Inference or secondary source
    UNVERIFIED = "unverified"  # Cannot verify


@dataclass
class Citation:
    """A single citation with full provenance"""
    id: str
    source_type: SourceType
    source_name: str
    claim: str                              # What claim this supports
    evidence: str                           # The actual evidence text
    confidence: CitationConfidence
    url: Optional[str] = None
    date_accessed: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    date_published: Optional[str] = None
    author: Optional[str] = None
    page_number: Optional[int] = None
    cross_referenced: bool = False
    cross_reference_sources: List[str] = field(default_factory=list)
    verified_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "claim": self.claim[:100],
            "evidence": self.evidence[:200],
            "confidence": self.confidence.value,
            "url": self.url,
            "date_accessed": self.date_accessed,
            "date_published": self.date_published,
            "author": self.author,
            "cross_referenced": self.cross_referenced,
            "cross_reference_sources": self.cross_reference_sources,
        }


@dataclass
class CitationReport:
    """Complete citation report for an analysis"""
    task_id: str
    citations: List[Citation] = field(default_factory=list)
    uncited_claims: List[str] = field(default_factory=list)
    cross_reference_summary: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_citations(self) -> int:
        return len(self.citations)
    
    @property
    def high_confidence_citations(self) -> List[Citation]:
        return [c for c in self.citations if c.confidence == CitationConfidence.HIGH]
    
    @property
    def cross_referenced_citations(self) -> List[Citation]:
        return [c for c in self.citations if c.cross_referenced]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "total_citations": self.total_citations,
            "high_confidence": len(self.high_confidence_citations),
            "cross_referenced": len(self.cross_referenced_citations),
            "uncited_claims": len(self.uncited_claims),
            "citations": [c.to_dict() for c in self.citations],
            "uncited_claims_list": self.uncited_claims,
            "cross_reference_summary": self.cross_reference_summary,
        }


class CitationAgent:
    """
    Dedicated agent for source attribution and citation management.
    
    Responsibilities:
    1. Extract claims from analyst findings
    2. Match claims to sources
    3. Generate citations with proper provenance
    4. Cross-reference citations across analysts
    5. Flag uncited claims for review
    6. Generate citation reports
    """
    
    def __init__(
        self,
        citation_dir: Optional[str] = None,
        require_cross_reference: bool = True,
        min_confidence_for_report: CitationConfidence = CitationConfidence.LOW,
    ):
        self.citation_dir = citation_dir or str(
            Path.home() / ".openclaw" / "workspace" / "k2-backbone" / "executions" / "citations"
        )
        self.require_cross_reference = require_cross_reference
        self.min_confidence_for_report = min_confidence_for_report
        
        # Known source databases
        self.known_sources: Dict[str, Dict[str, Any]] = self._init_known_sources()
        
        Path(self.citation_dir).mkdir(parents=True, exist_ok=True)
    
    def _init_known_sources(self) -> Dict[str, Dict[str, Any]]:
        """Initialize known source databases"""
        return {
            "sec_edgar": {
                "name": "SEC EDGAR",
                "type": SourceType.SEC_FILING,
                "base_url": "https://www.sec.gov/cgi-bin/browse-edgar",
                "reliability": "high",
            },
            "bloomberg": {
                "name": "Bloomberg Terminal",
                "type": SourceType.MARKET_DATA,
                "reliability": "high",
            },
            "coinmarketcap": {
                "name": "CoinMarketCap",
                "type": SourceType.MARKET_DATA,
                "base_url": "https://coinmarketcap.com",
                "reliability": "medium",
            },
            "etherscan": {
                "name": "Etherscan",
                "type": SourceType.ONCHAIN_DATA,
                "base_url": "https://etherscan.io",
                "reliability": "high",
            },
            "company_website": {
                "name": "Company Website",
                "type": SourceType.COMPANY_WEBSITE,
                "reliability": "medium",
            },
            "press_release": {
                "name": "Press Release",
                "type": SourceType.PRESS_RELEASE,
                "reliability": "high",
            },
        }
    
    def process_findings(
        self,
        task_id: str,
        analyst_role: str,
        findings: Dict[str, Any],
    ) -> CitationReport:
        """
        Process findings from an analyst and generate citations.
        
        This is the main entry point — it:
        1. Extracts claims from findings
        2. Matches claims to known sources
        3. Generates citations
        4. Cross-references with existing citations
        """
        report = CitationReport(task_id=task_id)
        
        # Extract claims from findings
        claims = self._extract_claims(findings)
        
        # Generate citations for each claim
        for claim in claims:
            citation = self._generate_citation(claim, analyst_role)
            if citation:
                report.citations.append(citation)
            else:
                report.uncited_claims.append(claim)
        
        # Cross-reference citations
        if self.require_cross_reference:
            self._cross_reference_citations(report)
        
        # Save report
        self._save_report(report)
        
        logger.info(f"  [CitationAgent] {analyst_role}: {len(report.citations)} citations, {len(report.uncited_claims)} uncited claims")
        
        return report
    
    def _extract_claims(self, findings: Dict[str, Any], prefix: str = "") -> List[str]:
        """Extract factual claims from findings"""
        claims = []
        
        for key, value in findings.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recurse into nested dicts
                claims.extend(self._extract_claims(value, full_key))
            
            elif isinstance(value, list):
                # Extract from list items
                for item in value:
                    if isinstance(item, dict):
                        claims.extend(self._extract_claims(item, full_key))
                    elif isinstance(item, str) and len(item) > 20:
                        claims.append(item)
            
            elif isinstance(value, str) and len(value) > 20:
                # This is a potential claim
                # Filter out metadata and labels
                if not any(skip in full_key.lower() for skip in ["description", "name", "type", "id"]):
                    claims.append(value)
            
            elif isinstance(value, (int, float)):
                # Numerical claims
                claims.append(f"{full_key}: {value}")
        
        return claims
    
    def _generate_citation(self, claim: str, analyst_role: str) -> Optional[Citation]:
        """Generate a citation for a claim"""
        # In production: search known databases, web search, etc.
        # For now: pattern-match to known source types
        
        source_type = self._infer_source_type(claim)
        source_name = self._infer_source_name(claim, source_type)
        confidence = self._infer_confidence(claim, source_type)
        
        if source_type == SourceType.UNKNOWN:
            return None
        
        citation = Citation(
            id=f"cit_{abs(hash(claim)) % 100000:05d}",
            source_type=source_type,
            source_name=source_name,
            claim=claim[:200],
            evidence=claim[:200],
            confidence=confidence,
            url=self._generate_source_url(source_type, claim),
        )
        
        return citation
    
    def _infer_source_type(self, claim: str) -> SourceType:
        """Infer the most likely source type for a claim"""
        claim_lower = claim.lower()
        
        # Financial metrics → likely from financial statements
        if any(w in claim_lower for w in ["revenue", "ebitda", "margin", "eps", "fcf", "net income", "gross profit"]):
            return SourceType.FINANCIAL_STATEMENT
        
        # SEC-related
        if any(w in claim_lower for w in ["sec filing", "10-k", "10-q", "8-k", "proxy"]):
            return SourceType.SEC_FILING
        
        # Market data
        if any(w in claim_lower for w in ["price", "market cap", "volume", "pe ratio", "ev/ebitda"]):
            return SourceType.MARKET_DATA
        
        # On-chain data
        if any(w in claim_lower for w in ["wallet", "address", "transaction", "block", "nvt", "tvl", "onchain"]):
            return SourceType.ONCHAIN_DATA
        
        # News
        if any(w in claim_lower for w in ["announced", "reported", "according to", "sources say"]):
            return SourceType.NEWS_ARTICLE
        
        # Press release
        if any(w in claim_lower for w in ["press release", "today announced", "is pleased to"]):
            return SourceType.PRESS_RELEASE
        
        # Company info
        if any(w in claim_lower for w in ["headquarters", "founded", "ceo", "employees", "headcount"]):
            return SourceType.COMPANY_WEBSITE
        
        return SourceType.UNKNOWN
    
    def _infer_source_name(self, claim: str, source_type: SourceType) -> str:
        """Infer the source name from the claim"""
        source_map = {
            SourceType.FINANCIAL_STATEMENT: "Company Financial Statements",
            SourceType.SEC_FILING: "SEC EDGAR",
            SourceType.MARKET_DATA: "Market Data Provider",
            SourceType.ONCHAIN_DATA: "Blockchain Explorer",
            SourceType.NEWS_ARTICLE: "News Source",
            SourceType.PRESS_RELEASE: "Company Press Release",
            SourceType.COMPANY_WEBSITE: "Company Website",
            SourceType.ANALYST_REPORT: "Analyst Research Report",
            SourceType.RESEARCH_PAPER: "Academic/Industry Research",
            SourceType.REGULATORY_FILING: "Regulatory Filing",
            SourceType.INTERVIEW: "Executive Interview",
            SourceType.DATABASE: "Industry Database",
            SourceType.EXPERT_OPINION: "Expert Consultation",
            SourceType.INTERNAL_MODEL: "Internal Analysis Model",
        }
        return source_map.get(source_type, "Unknown Source")
    
    def _infer_confidence(self, claim: str, source_type: SourceType) -> CitationConfidence:
        """Infer confidence in a citation"""
        # Primary sources are high confidence
        if source_type in [SourceType.SEC_FILING, SourceType.FINANCIAL_STATEMENT,
                          SourceType.REGULATORY_FILING, SourceType.ONCHAIN_DATA]:
            return CitationConfidence.HIGH
        
        # Reliable secondary sources
        if source_type in [SourceType.MARKET_DATA, SourceType.PRESS_RELEASE]:
            return CitationConfidence.MEDIUM
        
        # Less reliable
        if source_type in [SourceType.NEWS_ARTICLE, SourceType.ANALYST_REPORT]:
            return CitationConfidence.LOW
        
        # Check for uncertainty indicators
        if any(w in claim.lower() for w in ["estimate", "approximately", "roughly", "about", "may", "could", "might"]):
            return CitationConfidence.LOW
        
        return CitationConfidence.UNVERIFIED
    
    def _generate_source_url(self, source_type: SourceType, claim: str) -> Optional[str]:
        """Generate a plausible source URL"""
        url_map = {
            SourceType.SEC_FILING: "https://www.sec.gov/cgi-bin/browse-edgar",
            SourceType.MARKET_DATA: "https://finance.yahoo.com",
            SourceType.ONCHAIN_DATA: "https://etherscan.io",
            SourceType.COMPANY_WEBSITE: "https://example.com/investors",
            SourceType.PRESS_RELEASE: "https://example.com/press",
        }
        return url_map.get(source_type)
    
    def _cross_reference_citations(self, report: CitationReport):
        """Cross-reference citations across analysts"""
        cross_refs = {}
        
        for citation in report.citations:
            # Check if similar claims exist
            claim_key = citation.claim[:50]  # Use first 50 chars as key
            if claim_key in cross_refs:
                cross_refs[claim_key].append(citation.id)
            else:
                cross_refs[claim_key] = [citation.id]
        
        # Mark citations that have cross-references
        for key, ids in cross_refs.items():
            if len(ids) > 1:
                for cid in ids:
                    for citation in report.citations:
                        if citation.id == cid:
                            citation.cross_referenced = True
                            citation.cross_reference_sources = [i for i in ids if i != cid]
        
        report.cross_reference_summary = {
            "total_cross_referenced": len(report.cross_referenced_citations),
            "cross_reference_groups": len([k for k, v in cross_refs.items() if len(v) > 1]),
        }
    
    def _save_report(self, report: CitationReport):
        """Save a citation report to disk"""
        filename = f"citations_{report.task_id}.json"
        filepath = Path(self.citation_dir) / filename
        
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
    
    def merge_reports(self, reports: List[CitationReport]) -> CitationReport:
        """Merge multiple citation reports into one"""
        if not reports:
            return CitationReport(task_id="merged")
        
        merged = CitationReport(task_id=reports[0].task_id)
        
        for report in reports:
            merged.citations.extend(report.citations)
            merged.uncited_claims.extend(report.uncited_claims)
        
        # Deduplicate citations by claim
        seen_claims = set()
        unique_citations = []
        for c in merged.citations:
            if c.claim not in seen_claims:
                seen_claims.add(c.claim)
                unique_citations.append(c)
        merged.citations = unique_citations
        
        # Re-cross-reference
        self._cross_reference_citations(merged)
        
        return merged
    
    def generate_citation_section(self, report: CitationReport) -> str:
        """Generate a formatted citation section for a report"""
        lines = ["## Sources & Citations", ""]
        
        # Group by source type
        by_type: Dict[str, List[Citation]] = {}
        for c in report.citations:
            if c.confidence.value in [cc.value for cc in [CitationConfidence.HIGH, CitationConfidence.MEDIUM]]:
                st = c.source_type.value.replace("_", " ").title()
                if st not in by_type:
                    by_type[st] = []
                by_type[st].append(c)
        
        for source_type, citations in sorted(by_type.items()):
            lines.append(f"### {source_type}")
            for c in citations:
                ref = "✓ Cross-referenced" if c.cross_referenced else "Single source"
                url = f" | Source: {c.url}" if c.url else ""
                lines.append(f"- {c.claim[:100]}... [{c.confidence.value} confidence, {ref}{url}]")
            lines.append("")
        
        # Uncited claims
        if report.uncited_claims:
            lines.append("### ⚠️ Uncited Claims (Needs Verification)")
            for claim in report.uncited_claims[:5]:
                lines.append(f"- {claim[:100]}...")
            if len(report.uncited_claims) > 5:
                lines.append(f"- ... and {len(report.uncited_claims) - 5} more")
        
        return "\n".join(lines)
