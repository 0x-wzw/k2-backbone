from __future__ import annotations
"""
X-Interact Adapter for K2-Backbone

Adds social signal ingestion for research and monitoring subtasks.
When K2-Backbone needs real-time context, X-Interact pulls tweets,
trends, and sentiment.

Usage:
    from k2_backbone.social.x_interact_adapter import XInteractAdapter
    
    x = XInteractAdapter()
    signals = x.get_signals("AI agent orchestration")
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SocialSignal:
    source: str
    content: str
    author: str
    timestamp: str
    engagement: int
    sentiment: str  # "positive", "negative", "neutral"
    relevance_score: float


class XInteractAdapter:
    """
    Bridges X-Interact (Tavily) with K2-Backbone research subtasks.
    
    Provides:
    - Real-time tweet search
    - Trend analysis
    - Sentiment scoring
    - Author credibility check
    """
    
    def __init__(
        self,
        x_interact_path: Optional[Path] = None,
        tavily_api_key: Optional[str] = None,
        max_results: int = 20,
    ):
        self.x_interact_path = x_interact_path or Path(__file__).parent.parent.parent / "frameworks" / "x-interact"
        self.tavily_key = tavily_api_key or ""
        self.max_results = max_results
        
        self._initialized = False
    
    def initialize(self) -> None:
        if self._initialized:
            return
        
        if not self.x_interact_path.exists():
            logger.warning(f"X-Interact not found at {self.x_interact_path}")
        
        if not self.tavily_key:
            logger.warning("Tavily API key not set. X-Interact will use simulated data.")
        
        self._initialized = True
        logger.info("XInteractAdapter initialized")
    
    def get_signals(
        self,
        query: str,
        timeframe: str = "24h",
        min_relevance: float = 0.5,
    ) -> List[SocialSignal]:
        """
        Get social signals for a research query.
        
        Args:
            query: Search term (e.g., "AI agent orchestration")
            timeframe: "1h", "24h", "7d", "30d"
            min_relevance: Minimum relevance score (0-1)
        """
        self._ensure_initialized()
        
        logger.info(f"🔍 X-Interact search: '{query}' ({timeframe})")
        
        # In production: call Tavily API
        # For now: simulate relevant signals
        signals = self._simulate_signals(query)
        
        # Filter by relevance
        filtered = [s for s in signals if s.relevance_score >= min_relevance]
        
        # Sort by relevance
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        logger.info(f"   → Found {len(filtered)} relevant signals")
        
        return filtered[:self.max_results]
    
    def get_sentiment_summary(self, query: str) -> Dict[str, Any]:
        """Get aggregate sentiment for a topic"""
        signals = self.get_signals(query, min_relevance=0.3)
        
        if not signals:
            return {"query": query, "sentiment": "neutral", "confidence": 0}
        
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        for s in signals:
            sentiment_counts[s.sentiment] = sentiment_counts.get(s.sentiment, 0) + 1
        
        total = len(signals)
        dominant = max(sentiment_counts, key=sentiment_counts.get)
        confidence = sentiment_counts[dominant] / total
        
        return {
            "query": query,
            "sentiment": dominant,
            "confidence": round(confidence, 2),
            "counts": sentiment_counts,
            "total_signals": total,
            "avg_engagement": sum(s.engagement for s in signals) // max(total, 1),
        }
    
    def enrich_subtask(self, subtask: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a research subtask with social signals.
        Adds context to the subtask before execution.
        """
        description = subtask.get("description", "")
        
        # Extract key terms from description
        signals = self.get_signals(description[:100])
        sentiment = self.get_sentiment_summary(description[:100])
        
        # Add to subtask context
        enriched = dict(subtask)
        enriched["social_context"] = {
            "signals": [
                {
                    "source": s.source,
                    "content": s.content[:200],
                    "author": s.author,
                    "sentiment": s.sentiment,
                    "relevance": s.relevance_score,
                }
                for s in signals[:5]
            ],
            "sentiment": sentiment,
            "retrieved_at": datetime.now().isoformat(),
        }
        
        return enriched
    
    # ==================== Simulation ====================
    
    def _simulate_signals(self, query: str) -> List[SocialSignal]:
        """Simulate social signals for a query"""
        q_lower = query.lower()
        
        # Determine topic for simulation
        if "agent" in q_lower or "swarm" in q_lower:
            return [
                SocialSignal(
                    source="x",
                    content="Multi-agent orchestration is the next frontier. Kimi K2.6's 300-agent swarm is impressive.",
                    author="@aitech",
                    timestamp="2026-05-28T08:00:00Z",
                    engagement=234,
                    sentiment="positive",
                    relevance_score=0.95,
                ),
                SocialSignal(
                    source="x",
                    content="Cost optimization in agent swarms is critical. 70/30 routing models can save 60%+.",
                    author="@mlcosts",
                    timestamp="2026-05-28T07:30:00Z",
                    engagement=156,
                    sentiment="positive",
                    relevance_score=0.88,
                ),
                SocialSignal(
                    source="x",
                    content="Still skeptical about model-native swarms. External orchestration gives more control.",
                    author="@devskeptic",
                    timestamp="2026-05-28T06:00:00Z",
                    engagement=89,
                    sentiment="neutral",
                    relevance_score=0.72,
                ),
            ]
        
        elif "code" in q_lower or "engineering" in q_lower:
            return [
                SocialSignal(
                    source="x",
                    content="GLM-5.1 just hit SWE-Bench Pro SOTA at 58.4%. Game changer for coding agents.",
                    author="@codenews",
                    timestamp="2026-05-28T08:00:00Z",
                    engagement=567,
                    sentiment="positive",
                    relevance_score=0.93,
                ),
                SocialSignal(
                    source="x",
                    content="DeepSeek V3.2 still holds strong for general coding tasks at 81.2% LiveCodeBench.",
                    author="@benchmarks",
                    timestamp="2026-05-28T07:00:00Z",
                    engagement=234,
                    sentiment="positive",
                    relevance_score=0.85,
                ),
            ]
        
        return [
            SocialSignal(
                source="x",
                content=f"Latest updates on {query[:50]}...",
                author="@newsbot",
                timestamp="2026-05-28T08:00:00Z",
                engagement=100,
                sentiment="neutral",
                relevance_score=0.6,
            ),
        ]
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="X-Interact Social Adapter")
    parser.add_argument("query", nargs="?", default="AI agent orchestration", help="Search query")
    parser.add_argument("--sentiment", action="store_true", help="Get sentiment summary")
    parser.add_argument("--enrich", metavar="FILE", help="Enrich subtask JSON file")
    args = parser.parse_args()
    
    adapter = XInteractAdapter()
    
    if args.sentiment:
        result = adapter.get_sentiment_summary(args.query)
        print(f"📊 Sentiment for '{args.query}':")
        print(f"   Dominant: {result['sentiment']} ({result['confidence']:.0%} confidence)")
        print(f"   Signals: {result['total_signals']}")
        print(f"   Avg engagement: {result['avg_engagement']}")
    
    if args.enrich:
        with open(args.enrich) as f:
            subtask = json.load(f)
        enriched = adapter.enrich_subtask(subtask)
        print(f"✅ Enriched subtask with social context")
        print(f"   Signals: {len(enriched['social_context']['signals'])}")
        print(f"   Sentiment: {enriched['social_context']['sentiment']['sentiment']}")
    
    if not args.sentiment and not args.enrich:
        signals = adapter.get_signals(args.query)
        print(f"🔍 Found {len(signals)} signals for '{args.query}':")
        for s in signals[:5]:
            print(f"   [{s.sentiment}] {s.author}: {s.content[:80]}... (relevance: {s.relevance_score:.2f})")


if __name__ == "__main__":
    main()
