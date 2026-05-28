from __future__ import annotations
"""
Memory Evolution Adapter for K2-Backbone

Self-improving memory system with:
- Access pattern tracking and decay scoring
- Automatic relationship inference
- Memory rewriting and versioning
- Importance-based retrieval ranking

Ported from Nexys: unified_platform/adapters/memory_evolution_adapter.py
Simplified for K2-Backbone's pipeline architecture.
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A stored memory with metadata"""
    key: str
    data: Any
    timestamp: float = 0.0
    tags: List[str] = field(default_factory=list)
    importance: float = 1.0
    source: str = ""


@dataclass
class TrackedMemory:
    """Memory entry with evolution tracking"""
    entry: MemoryEntry
    access_count: int = 0
    last_accessed: float = 0.0
    created_at: float = 0.0
    relationships: Set[str] = field(default_factory=set)
    versions: List[Any] = field(default_factory=list)
    decay_score: float = 1.0
    importance_score: float = 1.0
    rewrite_count: int = 0


@dataclass
class SearchResult:
    """Result from memory search"""
    key: str
    data: Any
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryEvolutionAdapter:
    """
    Self-Improving Memory System for K2-Backbone.
    
    Tracks access patterns, infers relationships, and rewrites
    memories for clarity and consolidation.
    
    Usage:
        adapter = MemoryEvolutionAdapter()
        adapter.store("task_001", {"result": "success"}, importance=2.0)
        
        entry = adapter.retrieve("task_001")  # Access tracked
        results = adapter.search("success")   # Importance-weighted
        
        report = adapter.evolve()  # Infer relationships, rewrite memories
    """
    
    def __init__(
        self,
        track_access: bool = True,
        enable_decay: bool = True,
        enable_relationships: bool = True,
        enable_rewriting: bool = True,
        decay_halflife_hours: float = 168.0,
        importance_boost: float = 0.1,
        max_importance: float = 10.0,
        min_cooccurrence: int = 3,
    ):
        self.track_access = track_access
        self.enable_decay = enable_decay
        self.enable_relationships = enable_relationships
        self.enable_rewriting = enable_rewriting
        self.decay_halflife = decay_halflife_hours
        self.importance_boost = importance_boost
        self.max_importance = max_importance
        self.min_cooccurrence = min_cooccurrence
        
        self._memories: Dict[str, TrackedMemory] = {}
        self._access_log: List[Dict[str, Any]] = []
        self._access_sequences: List[List[str]] = []
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize memory evolution system"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("MemoryEvolutionAdapter initialized")
    
    def store(
        self,
        key: str,
        data: Any,
        importance: float = 1.0,
        tags: Optional[List[str]] = None,
        source: str = "",
    ) -> None:
        """Store memory with tracking"""
        self._ensure_initialized()
        
        entry = MemoryEntry(
            key=key,
            data=data,
            timestamp=time.time(),
            tags=tags or [],
            importance=importance,
            source=source,
        )
        
        now = time.time()
        tracked = TrackedMemory(
            entry=entry,
            created_at=now,
            last_accessed=now,
            importance_score=importance,
        )
        
        self._memories[key] = tracked
        
        if self.track_access:
            self._access_log.append({
                "memory_id": key,
                "operation": "write",
                "timestamp": now,
            })
        
        logger.debug(f"Stored memory: {key}")
    
    def retrieve(self, key: str) -> Optional[MemoryEntry]:
        """Retrieve memory with access tracking"""
        self._ensure_initialized()
        
        tracked = self._memories.get(key)
        if not tracked:
            return None
        
        now = time.time()
        tracked.access_count += 1
        tracked.last_accessed = now
        tracked.importance_score = min(
            tracked.importance_score + self.importance_boost,
            self.max_importance,
        )
        
        if self.track_access:
            self._access_log.append({
                "memory_id": key,
                "operation": "read",
                "timestamp": now,
            })
        
        if self.enable_decay:
            tracked.decay_score = self._compute_decay_score(tracked)
        
        return tracked.entry
    
    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> List[SearchResult]:
        """Search with importance-weighted scoring"""
        self._ensure_initialized()
        
        results = []
        query_lower = query.lower()
        
        for key, tracked in self._memories.items():
            # Compute base similarity
            data_str = str(tracked.entry.data).lower()
            score = self._text_similarity(query_lower, data_str)
            
            # Boost by importance and decay
            if self.enable_decay:
                importance_boost = tracked.importance_score / self.max_importance
                score = score * (0.5 + 0.5 * importance_boost) * tracked.decay_score
            
            if score >= min_score:
                results.append(SearchResult(
                    key=key,
                    data=tracked.entry.data,
                    score=score,
                    metadata={
                        "importance": tracked.importance_score,
                        "access_count": tracked.access_count,
                        "decay_score": tracked.decay_score,
                    }
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def delete(self, key: str) -> bool:
        """Delete memory"""
        if key in self._memories:
            del self._memories[key]
            return True
        return False
    
    def evolve(self) -> Dict[str, Any]:
        """
        Evolve memory structures:
        1. Infer relationships from co-access patterns
        2. Adjust importance scores based on decay
        3. Rewrite frequently accessed memories
        """
        self._ensure_initialized()
        
        new_relationships = 0
        schema_changes = []
        
        # 1. Infer relationships
        if self.enable_relationships:
            for key, tracked in self._memories.items():
                coaccess = self._get_coaccess_patterns(key)
                
                for other_key, count in coaccess.items():
                    if count >= self.min_cooccurrence:
                        if other_key not in tracked.relationships:
                            tracked.relationships.add(other_key)
                            new_relationships += 1
                            
                            # Reciprocal
                            if other_key in self._memories:
                                self._memories[other_key].relationships.add(key)
        
        # 2. Adjust importance with decay
        if self.enable_decay:
            for tracked in self._memories.values():
                tracked.decay_score = self._compute_decay_score(tracked)
        
        # 3. Rewrite important memories
        if self.enable_rewriting:
            rewritten = self._rewrite_important_memories()
            schema_changes.append(f"rewritten:{rewritten}")
        
        logger.info(f"Evolution complete: {new_relationships} new relationships")
        
        return {
            "new_relationships": new_relationships,
            "total_memories": len(self._memories),
            "total_relationships": sum(len(m.relationships) for m in self._memories.values()),
            "schema_changes": schema_changes,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory evolution statistics"""
        total_memories = len(self._memories)
        total_accesses = sum(m.access_count for m in self._memories.values())
        avg_importance = sum(m.importance_score for m in self._memories.values()) / max(total_memories, 1)
        total_relationships = sum(len(m.relationships) for m in self._memories.values())
        
        frequently_accessed = self._get_frequently_accessed(threshold=5)
        
        return {
            "total_memories": total_memories,
            "total_accesses": total_accesses,
            "avg_importance": round(avg_importance, 2),
            "total_relationships": total_relationships,
            "frequently_accessed": len(frequently_accessed),
            "access_log_size": len(self._access_log),
        }
    
    def get_related(self, key: str) -> List[str]:
        """Get memories related to a given key"""
        tracked = self._memories.get(key)
        if not tracked:
            return []
        return list(tracked.relationships)
    
    def get_version_history(self, key: str) -> List[Any]:
        """Get version history for a memory"""
        tracked = self._memories.get(key)
        if not tracked:
            return []
        return tracked.versions
    
    # ==================== Helper Methods ====================
    
    def _compute_decay_score(self, tracked: TrackedMemory) -> float:
        """Compute decay score based on time since last access"""
        hours_since_access = (time.time() - tracked.last_accessed) / 3600
        halflife = self.decay_halflife
        
        decay = 0.5 ** (hours_since_access / halflife)
        access_boost = min(tracked.access_count * 0.05, 1.0)
        
        return min(decay + access_boost, 1.0)
    
    def _text_similarity(self, query: str, text: str) -> float:
        """Simple text similarity score"""
        query_terms = query.split()
        if not query_terms:
            return 0.0
        
        matches = sum(1 for term in query_terms if term in text)
        return matches / len(query_terms)
    
    def _get_coaccess_patterns(self, key: str) -> Dict[str, int]:
        """Get memories frequently accessed together"""
        coaccess = defaultdict(int)
        
        for sequence in self._access_sequences:
            if key in sequence:
                for other in sequence:
                    if other != key:
                        coaccess[other] += 1
        
        return dict(coaccess)
    
    def _get_frequently_accessed(self, threshold: int = 5) -> List[Tuple[str, int]]:
        """Get memories accessed more than threshold times"""
        counts = defaultdict(int)
        for entry in self._access_log:
            counts[entry["memory_id"]] += 1
        
        return [(mid, count) for mid, count in counts.items() if count >= threshold]
    
    def _rewrite_important_memories(self) -> int:
        """Rewrite frequently accessed memories"""
        rewritten = 0
        frequently_accessed = self._get_frequently_accessed(threshold=10)
        
        for key, count in frequently_accessed:
            tracked = self._memories.get(key)
            if tracked and tracked.rewrite_count < 3:
                # Store current version
                tracked.versions.append(tracked.entry.data)
                tracked.entry.tags.append(f"rewritten_v{tracked.rewrite_count + 1}")
                tracked.rewrite_count += 1
                rewritten += 1
        
        return rewritten
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Memory Evolution Adapter")
    parser.add_argument("--store", nargs=2, metavar=("KEY", "VALUE"), help="Store a memory")
    parser.add_argument("--retrieve", metavar="KEY", help="Retrieve a memory")
    parser.add_argument("--search", metavar="QUERY", help="Search memories")
    parser.add_argument("--evolve", action="store_true", help="Run evolution")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    args = parser.parse_args()
    
    adapter = MemoryEvolutionAdapter()
    
    if args.store:
        adapter.store(args.store[0], args.store[1], importance=1.0)
        print(f"✅ Stored: {args.store[0]}")
    
    if args.retrieve:
        entry = adapter.retrieve(args.retrieve)
        if entry:
            print(f"✅ Found: {entry.data}")
        else:
            print(f"❌ Not found: {args.retrieve}")
    
    if args.search:
        results = adapter.search(args.search)
        print(f"🔍 Found {len(results)} results:")
        for r in results[:5]:
            print(f"   {r.key} (score: {r.score:.2f})")
    
    if args.evolve:
        report = adapter.evolve()
        print(f"🧬 Evolution: {report['new_relationships']} new relationships")
    
    if args.stats:
        stats = adapter.get_stats()
        print(f"📊 Stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    import json
    main()
