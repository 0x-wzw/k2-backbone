"""
Effort Scaling Engine — Dynamic resource allocation based on query complexity.

Anthropic's system uses explicit rules:
- Simple queries → 1 agent with 3-10 calls
- Complex queries → 10+ subagents with full pipeline

This engine classifies queries by complexity and allocates resources accordingly.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Complexity levels for query classification"""
    TRIVIAL = "trivial"           # Simple fact lookup, 1 agent, 1-2 calls
    SIMPLE = "simple"             # Basic analysis, 1-2 agents, 3-10 calls
    MODERATE = "moderate"         # Multi-faceted, 3-5 agents, 10-20 calls
    COMPLEX = "complex"           # Deep analysis, 5-8 agents, 20-50 calls
    VERY_COMPLEX = "very_complex" # Full pipeline, 8+ agents, 50+ calls


@dataclass
class EffortBudget:
    """Resource budget for a query based on complexity"""
    complexity: ComplexityLevel
    max_analysts: int
    min_analysts: int
    max_calls: int
    min_calls: int
    max_iterations: int          # For interleaved thinking
    max_dynamic_spawns: int      # For dynamic decomposition
    max_depth: int               # Max re-decomposition depth
    budget_usd: float
    time_budget_seconds: int
    required_roles: List[str]    # Minimum roles that must be engaged
    optional_roles: List[str]    # Roles to add if complexity warrants
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "complexity": self.complexity.value,
            "max_analysts": self.max_analysts,
            "min_analysts": self.min_analysts,
            "max_calls": self.max_calls,
            "min_calls": self.min_calls,
            "max_iterations": self.max_iterations,
            "max_dynamic_spawns": self.max_dynamic_spawns,
            "max_depth": self.max_depth,
            "budget_usd": self.budget_usd,
            "time_budget_seconds": self.time_budget_seconds,
            "required_roles": self.required_roles,
            "optional_roles": self.optional_roles,
        }


# ── Effort Budgets by Complexity ─────────────────────────────────────

EFFORT_BUDGETS = {
    ComplexityLevel.TRIVIAL: EffortBudget(
        complexity=ComplexityLevel.TRIVIAL,
        max_analysts=1,
        min_analysts=1,
        max_calls=2,
        min_calls=1,
        max_iterations=1,
        max_dynamic_spawns=0,
        max_depth=0,
        budget_usd=0.05,
        time_budget_seconds=10,
        required_roles=[],
        optional_roles=[],
    ),
    ComplexityLevel.SIMPLE: EffortBudget(
        complexity=ComplexityLevel.SIMPLE,
        max_analysts=2,
        min_analysts=1,
        max_calls=10,
        min_calls=3,
        max_iterations=2,
        max_dynamic_spawns=1,
        max_depth=1,
        budget_usd=0.20,
        time_budget_seconds=30,
        required_roles=["fundamental_analyst"],
        optional_roles=["quantitative_analyst"],
    ),
    ComplexityLevel.MODERATE: EffortBudget(
        complexity=ComplexityLevel.MODERATE,
        max_analysts=5,
        min_analysts=3,
        max_calls=20,
        min_calls=10,
        max_iterations=3,
        max_dynamic_spawns=3,
        max_depth=2,
        budget_usd=0.50,
        time_budget_seconds=60,
        required_roles=["fundamental_analyst", "quantitative_analyst"],
        optional_roles=["risk_analyst", "sector_specialist"],
    ),
    ComplexityLevel.COMPLEX: EffortBudget(
        complexity=ComplexityLevel.COMPLEX,
        max_analysts=8,
        min_analysts=5,
        max_calls=50,
        min_calls=20,
        max_iterations=4,
        max_dynamic_spawns=5,
        max_depth=3,
        budget_usd=1.50,
        time_budget_seconds=180,
        required_roles=[
            "fundamental_analyst", "quantitative_analyst",
            "risk_analyst", "sector_specialist",
        ],
        optional_roles=["technical_analyst", "devils_advocate"],
    ),
    ComplexityLevel.VERY_COMPLEX: EffortBudget(
        complexity=ComplexityLevel.VERY_COMPLEX,
        max_analysts=10,
        min_analysts=8,
        max_calls=100,
        min_calls=50,
        max_iterations=5,
        max_dynamic_spawns=8,
        max_depth=4,
        budget_usd=5.00,
        time_budget_seconds=600,
        required_roles=[
            "fundamental_analyst", "quantitative_analyst",
            "risk_analyst", "sector_specialist",
            "technical_analyst", "devils_advocate",
        ],
        optional_roles=[],
    ),
}


class EffortScalingEngine:
    """
    Engine that classifies query complexity and allocates resources.
    
    Rules:
    - Simple fact lookup → 1 agent, 1-2 calls, no dynamic spawning
    - Basic analysis → 1-2 agents, 3-10 calls, limited thinking
    - Multi-faceted → 3-5 agents, 10-20 calls, interleaved thinking
    - Deep analysis → 5-8 agents, 20-50 calls, full dynamic decomposition
    - Full pipeline → 8+ agents, 50+ calls, everything enabled
    """
    
    def __init__(self):
        self.classification_history: List[Dict[str, Any]] = []
    
    def classify(self, query: str, context: Optional[Dict[str, Any]] = None) -> ComplexityLevel:
        """
        Classify a query by complexity.
        
        Uses:
        - Query length and structure
        - Domain-specific keywords
        - Number of entities mentioned
        - Analysis depth indicators
        - User-specified budget (if provided)
        """
        score = 0
        
        # Factor 1: Query length
        word_count = len(query.split())
        if word_count > 50:
            score += 3
        elif word_count > 20:
            score += 2
        elif word_count > 10:
            score += 1
        
        # Factor 2: Number of entities (companies, sectors, metrics)
        entities = self._count_entities(query)
        score += min(entities, 5)
        
        # Factor 3: Analysis depth indicators
        depth_indicators = [
            "deep dive", "comprehensive", "thorough", "detailed",
            "full analysis", "in-depth", "complete", "exhaustive",
        ]
        for indicator in depth_indicators:
            if indicator in query.lower():
                score += 2
        
        # Factor 4: Multi-domain indicators
        domain_indicators = [
            "compare", "vs", "versus", "sector", "industry",
            "competitive", "landscape", "ecosystem", "market",
        ]
        for indicator in domain_indicators:
            if indicator in query.lower():
                score += 1
        
        # Factor 5: Risk/uncertainty indicators
        risk_indicators = [
            "risk", "uncertain", "scenario", "what if",
            "downside", "black swan", "tail risk",
        ]
        for indicator in risk_indicators:
            if indicator in query.lower():
                score += 1
        
        # Factor 6: User-specified budget override
        if context and "budget" in context:
            user_budget = context["budget"].get("max_cost_usd", 0)
            if user_budget >= 5.0:
                score += 5
            elif user_budget >= 2.0:
                score += 3
            elif user_budget >= 0.5:
                score += 1
        
        # Map score to complexity level
        if score >= 12:
            level = ComplexityLevel.VERY_COMPLEX
        elif score >= 8:
            level = ComplexityLevel.COMPLEX
        elif score >= 5:
            level = ComplexityLevel.MODERATE
        elif score >= 2:
            level = ComplexityLevel.SIMPLE
        else:
            level = ComplexityLevel.TRIVIAL
        
        # Record classification
        self.classification_history.append({
            "query": query[:100],
            "score": score,
            "level": level.value,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat(),
        })
        
        logger.info(f"  [EffortScale] Query complexity: {level.value} (score: {score})")
        
        return level
    
    def get_budget(self, query: str, context: Optional[Dict[str, Any]] = None) -> EffortBudget:
        """Get the effort budget for a query"""
        level = self.classify(query, context)
        return EFFORT_BUDGETS[level]
    
    def get_analyst_roster(self, query: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Get the list of analysts to engage for a query.
        
        Returns the minimum viable roster based on complexity.
        """
        budget = self.get_budget(query, context)
        
        # Start with required roles
        roster = list(budget.required_roles)
        
        # Add optional roles if complexity warrants
        if budget.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            roster.extend(budget.optional_roles)
        elif budget.complexity == ComplexityLevel.MODERATE:
            # Add optional roles based on query content
            for role in budget.optional_roles:
                if self._query_needs_role(query, role):
                    roster.append(role)
        
        # Ensure we don't exceed max
        if len(roster) > budget.max_analysts:
            roster = roster[:budget.max_analysts]
        
        return roster
    
    def _count_entities(self, query: str) -> int:
        """Count the number of entities (companies, tickers, sectors) in a query"""
        count = 0
        
        # Count capitalized words (potential company names)
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1:
                count += 1
        
        # Count ticker patterns (2-5 uppercase letters)
        tickers = re.findall(r'\b[A-Z]{2,5}\b', query)
        count += len(tickers)
        
        return count
    
    def _query_needs_role(self, query: str, role: str) -> bool:
        """Check if a query likely needs a specific analyst role"""
        role_keywords = {
            "risk_analyst": ["risk", "downside", "scenario", "uncertain", "volatility"],
            "technical_analyst": ["price", "technical", "chart", "options", "onchain", "momentum"],
            "sector_specialist": ["sector", "industry", "market", "competitive", "landscape"],
            "devils_advocate": ["critique", "stress test", "weakness", "flaw", "counter"],
        }
        
        keywords = role_keywords.get(role, [])
        return any(k in query.lower() for k in keywords)
    
    def get_classification_summary(self) -> Dict[str, Any]:
        """Get a summary of all classifications made"""
        levels = {}
        for record in self.classification_history:
            level = record["level"]
            levels[level] = levels.get(level, 0) + 1
        
        return {
            "total_classified": len(self.classification_history),
            "by_level": levels,
            "recent": self.classification_history[-5:] if self.classification_history else [],
        }
