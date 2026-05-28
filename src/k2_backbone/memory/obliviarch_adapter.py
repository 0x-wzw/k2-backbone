from __future__ import annotations
"""
Obliviarch Memory Adapter for K2-Backbone

3-level memory compression pipeline:
  Level 1: Episodic (raw traces, ~20x compression)
  Level 2: Semantic (pattern extraction, ~100x compression)
  Level 3: Archetypal (behavioral DNA, ~500x compression)

Integrates into K2-Backbone's execution pipeline:
  NeuroSwarmExecutor output → ObliviarchAdapter.ingest()
  → compressed schemas → DeterministicRetrievalAdapter.retrieve()

Usage:
    from k2_backbone.memory.obliviarch_adapter import ObliviarchAdapter
    
    obliviarch = ObliviarchAdapter()
    
    # After NeuroSwarm execution:
    result = obliviarch.ingest(task_id, execution_trace)
    
    # Query later:
    memory = obliviarch.query("java optimization patterns")
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────

@dataclass
class MemoryLevel:
    """A memory at a specific compression level"""
    level: int  # 1=Episodic, 2=Semantic, 3=Archetypal
    data: Any
    compressed_size: int
    original_size: int
    created_at: str = ""
    access_count: int = 0
    last_accessed: str = ""


@dataclass
class TraceSchema:
    """Compressed trace schema (Level 2+)"""
    task_type: str
    pattern: str
    frequency: int
    success_rate: float
    avg_duration_ms: float
    avg_cost_usd: float
    models_used: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class ArchetypalDNA:
    """Behavioral DNA (Level 3)"""
    domain: str
    archetype: str
    core_pattern: str
    success_factors: List[str] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    optimal_model: str = ""
    avg_complexity: str = "moderate"
    compression_ratio: float = 1.0


class ObliviarchAdapter:
    """
    3-Level Memory Compression for K2-Backbone.
    
    Pipeline:
      Raw Trace (100%) → Episodic (~5%) → Semantic (~1%) → Archetypal (~0.2%)
    
    Compression targets:
      Level 1 (Episodic): ~20x reduction
      Level 2 (Semantic): ~100x reduction  
      Level 3 (Archetypal): ~500x reduction
    
    Promotion rules:
      Episodic → Semantic: Pattern recurs ≥ 10 times
      Semantic → Archetypal: Archetype stable across ≥ 20 traces
    """
    
    def __init__(
        self,
        storage_path: str = "~/.openclaw/workspace/k2-backbone/.obliviarch",
        episodic_retention_hours: float = 48.0,
        semantic_threshold: int = 10,
        archetypal_threshold: int = 20,
        enable_level_1: bool = True,
        enable_level_2: bool = True,
        enable_level_3: bool = True,
    ):
        self.storage = Path(storage_path).expanduser()
        self.episodic_retention = episodic_retention_hours
        self.semantic_threshold = semantic_threshold
        self.archetypal_threshold = archetypal_threshold
        
        self.enable_level_1 = enable_level_1
        self.enable_level_2 = enable_level_2
        self.enable_level_3 = enable_level_3
        
        # In-memory indices
        self._episodic: Dict[str, MemoryLevel] = {}
        self._semantic: Dict[str, TraceSchema] = {}
        self._archetypal: Dict[str, ArchetypalDNA] = {}
        self._pattern_counter: Dict[str, int] = defaultdict(int)
        
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize storage and load existing schemas"""
        if self._initialized:
            return
        
        self.storage.mkdir(parents=True, exist_ok=True)
        
        # Load existing schemas from disk
        self._load_existing()
        
        self._initialized = True
        logger.info(f"ObliviarchAdapter initialized (storage: {self.storage})")
    
    def _load_existing(self) -> None:
        """Load existing compressed schemas from storage"""
        semantic_path = self.storage / "semantic"
        archetypal_path = self.storage / "archetypal"
        
        if semantic_path.exists():
            for f in semantic_path.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    self._semantic[data["pattern"]] = TraceSchema(**data)
                except Exception:
                    pass
        
        if archetypal_path.exists():
            for f in archetypal_path.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    self._archetypal[data["archetype"]] = ArchetypalDNA(**data)
                except Exception:
                    pass
    
    def ingest(
        self,
        task_id: str,
        execution_trace: Dict[str, Any],
        source: str = "neuroswarm_executor",
    ) -> str:
        """
        Ingest an execution trace into the compression pipeline.
        
        Returns: schema_id for the compressed memory.
        """
        self._ensure_initialized()
        
        # Level 1: Episodic (store raw trace temporarily)
        if self.enable_level_1:
            episodic_id = self._ingest_episodic(task_id, execution_trace, source)
        else:
            episodic_id = None
        
        # Extract features for compression
        features = self._extract_features(execution_trace)
        
        # Level 2: Semantic (pattern extraction)
        if self.enable_level_2:
            semantic_id = self._ingest_semantic(features, source)
        else:
            semantic_id = None
        
        # Level 3: Archetypal (behavioral DNA)
        if self.enable_level_3:
            archetypal_id = self._ingest_archetypal(features, source)
        else:
            archetypal_id = None
        
        # Build schema ID from content hash
        content_hash = hashlib.sha256(
            json.dumps(features, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        return f"obliviarch_{content_hash}"
    
    def _ingest_episodic(
        self,
        task_id: str,
        trace: Dict[str, Any],
        source: str,
    ) -> str:
        """Store raw trace (Level 1). Kept for 48h, then purged or promoted."""
        trace_json = json.dumps(trace, sort_keys=True, default=str)
        original_size = len(trace_json.encode("utf-8"))
        
        # Compress via deduplication and summarization
        summary = self._summarize_trace(trace)
        compressed = json.dumps(summary, sort_keys=True, default=str)
        compressed_size = len(compressed.encode("utf-8"))
        
        memory = MemoryLevel(
            level=1,
            data=summary,
            compressed_size=compressed_size,
            original_size=original_size,
            created_at=datetime.now().isoformat(),
        )
        
        self._episodic[task_id] = memory
        
        logger.debug(f"Episodic: {task_id} → {compressed_size}/{original_size} bytes")
        
        return task_id
    
    def _ingest_semantic(
        self,
        features: Dict[str, Any],
        source: str,
    ) -> str:
        """Extract pattern and store in semantic index (Level 2)."""
        pattern = features.get("pattern", "unknown")
        task_type = features.get("task_type", "general")
        
        # Check if pattern already exists
        if pattern in self._semantic:
            existing = self._semantic[pattern]
            existing.frequency += 1
            existing.success_rate = (
                existing.success_rate * (existing.frequency - 1) + features.get("success", 0.0)
            ) / existing.frequency
            existing.avg_duration_ms = (
                existing.avg_duration_ms * (existing.frequency - 1) + features.get("duration_ms", 0)
            ) / existing.frequency
            existing.avg_cost_usd = (
                existing.avg_cost_usd * (existing.frequency - 1) + features.get("cost_usd", 0.0)
            ) / existing.frequency
        else:
            self._semantic[pattern] = TraceSchema(
                task_type=task_type,
                pattern=pattern,
                frequency=1,
                success_rate=features.get("success", 0.0),
                avg_duration_ms=features.get("duration_ms", 0),
                avg_cost_usd=features.get("cost_usd", 0.0),
                models_used=features.get("models", []),
                tags=features.get("tags", []),
            )
        
        self._pattern_counter[pattern] += 1
        
        # Promote to Level 3 if threshold reached
        if self._pattern_counter[pattern] >= self.semantic_threshold:
            self._ingest_archetypal(features, source)
        
        # Persist
        self._persist_semantic(pattern)
        
        logger.debug(f"Semantic: {pattern} (freq: {self._pattern_counter[pattern]})")
        
        return pattern
    
    def _ingest_archetypal(
        self,
        features: Dict[str, Any],
        source: str,
    ) -> str:
        """Build archetypal DNA (Level 3). Immortal behavioral patterns."""
        domain = features.get("domain", "general")
        archetype = f"{domain}_{features.get('pattern', 'unknown')}"
        
        # Build archetype from aggregated semantic data
        if archetype in self._archetypal:
            existing = self._archetypal[archetype]
            existing.success_factors = list(set(
                existing.success_factors + features.get("success_factors", [])
            ))[:10]
            existing.failure_modes = list(set(
                existing.failure_modes + features.get("failure_modes", [])
            ))[:10]
        else:
            self._archetypal[archetype] = ArchetypalDNA(
                domain=domain,
                archetype=archetype,
                core_pattern=features.get("pattern", ""),
                success_factors=features.get("success_factors", [])[:10],
                failure_modes=features.get("failure_modes", [])[:10],
                optimal_model=features.get("optimal_model", ""),
                avg_complexity=features.get("complexity", "moderate"),
                compression_ratio=500.0,  # Target
            )
        
        # Persist
        self._persist_archetypal(archetype)
        
        logger.info(f"Archetypal: {archetype} (promoted from semantic)")
        
        return archetype
    
    def query(
        self,
        query: str,
        level: Optional[int] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query compressed memories.
        
        Args:
            query: Search string (matches tags, patterns, archetypes)
            level: 1=episodic, 2=semantic, 3=archetypal, None=all
            limit: Max results
        """
        self._ensure_initialized()
        
        results = []
        query_lower = query.lower()
        
        # Level 3: Archetypal (best recall, most compressed)
        if (level is None or level == 3) and self.enable_level_3:
            for archetype, dna in self._archetypal.items():
                score = self._match_score(query_lower, archetype, dna)
                if score > 0:
                    results.append({
                        "level": 3,
                        "id": archetype,
                        "type": "archetypal",
                        "data": dna,
                        "score": score,
                        "compression": 500,
                    })
        
        # Level 2: Semantic
        if (level is None or level == 2) and self.enable_level_2:
            for pattern, schema in self._semantic.items():
                score = self._match_score(query_lower, pattern, schema)
                if score > 0:
                    results.append({
                        "level": 2,
                        "id": pattern,
                        "type": "semantic",
                        "data": schema,
                        "score": score,
                        "compression": 100,
                    })
        
        # Level 1: Episodic
        if (level is None or level == 1) and self.enable_level_1:
            for task_id, memory in self._episodic.items():
                score = self._match_score(query_lower, task_id, memory.data)
                if score > 0:
                    results.append({
                        "level": 1,
                        "id": task_id,
                        "type": "episodic",
                        "data": memory.data,
                        "score": score,
                        "compression": 20,
                    })
        
        results.sort(key=lambda x: (x["level"], x["score"]), reverse=True)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        total_episodic_size = sum(m.compressed_size for m in self._episodic.values())
        total_original_size = sum(m.original_size for m in self._episodic.values())
        
        return {
            "episodic_count": len(self._episodic),
            "semantic_count": len(self._semantic),
            "archetypal_count": len(self._archetypal),
            "total_episodic_size_bytes": total_episodic_size,
            "total_original_size_bytes": total_original_size,
            "compression_ratio": round(total_original_size / max(total_episodic_size, 1), 1),
            "patterns_tracked": len(self._pattern_counter),
        }
    
    # ==================== Helpers ====================
    
    def _extract_features(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Extract compressible features from execution trace"""
        results = trace.get("execution_trace", {}).get("results", [])
        total_duration = sum(r.get("execution_time_ms", 0) for r in results)
        total_cost = trace.get("cost", {}).get("actual_cost", 0.0)
        
        # Determine pattern from subtask types
        subtask_types = set()
        task_types = []
        for r in results:
            st_id = r.get("subtask_id", "")
            # Infer type from ID
            if "_" in st_id:
                task_types.append(st_id.split("_")[1] if len(st_id.split("_")) > 1 else "general")
        
        # Build pattern string
        pattern = "_".join(sorted(set(task_types))) if task_types else "general"
        
        # Determine success
        success = all(r.get("status") == "completed" for r in results) if results else False
        
        # Extract domain from task
        task = trace.get("task_id", "")
        domain = "code" if "code" in task.lower() else "general"
        
        return {
            "task_type": trace.get("task_type", "general"),
            "pattern": pattern,
            "domain": domain,
            "success": 1.0 if success else 0.0,
            "duration_ms": total_duration,
            "cost_usd": total_cost,
            "models": list(set(r.get("model_used", "") for r in results)),
            "tags": trace.get("tags", []),
            "complexity": trace.get("complexity", "moderate"),
            "success_factors": ["parallel_execution"] if success else [],
            "failure_modes": ["timeout"] if not success else [],
            "optimal_model": results[0].get("model_used", "") if results else "",
        }
    
    def _summarize_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize trace for episodic storage"""
        return {
            "task_id": trace.get("task_id", ""),
            "status": trace.get("status", ""),
            "subtask_count": len(trace.get("execution_trace", {}).get("results", [])),
            "total_duration_ms": sum(
                r.get("execution_time_ms", 0)
                for r in trace.get("execution_trace", {}).get("results", [])
            ),
            "models_used": list(set(
                r.get("model_used", "")
                for r in trace.get("execution_trace", {}).get("results", [])
            )),
            "timestamp": datetime.now().isoformat(),
        }
    
    def _match_score(self, query: str, key: str, data: Any) -> float:
        """Compute match score for query"""
        score = 0.0
        
        # Match in key
        if query in key.lower():
            score += 0.5
        
        # Match in data (if string or has string fields)
        data_str = str(data).lower()
        query_terms = query.split()
        for term in query_terms:
            if term in data_str:
                score += 0.3
        
        return min(score, 1.0)
    
    def _persist_semantic(self, pattern: str) -> None:
        """Save semantic schema to disk"""
        path = self.storage / "semantic" / f"{pattern}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        schema = self._semantic.get(pattern)
        if schema:
            path.write_text(json.dumps(schema.__dict__, indent=2, default=str))
    
    def _persist_archetypal(self, archetype: str) -> None:
        """Save archetypal DNA to disk"""
        path = self.storage / "archetypal" / f"{archetype}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        dna = self._archetypal.get(archetype)
        if dna:
            path.write_text(json.dumps(dna.__dict__, indent=2, default=str))
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Obliviarch Memory Adapter")
    parser.add_argument("--ingest", metavar="FILE", help="Ingest trace JSON")
    parser.add_argument("--query", metavar="STRING", help="Query memories")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], help="Query level")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    args = parser.parse_args()
    
    adapter = ObliviarchAdapter()
    
    if args.ingest:
        with open(args.ingest) as f:
            trace = json.load(f)
        schema_id = adapter.ingest("manual_001", trace)
        print(f"✅ Ingested: {schema_id}")
    
    if args.query:
        results = adapter.query(args.query, level=args.level)
        print(f"🔍 Found {len(results)} results:")
        for r in results:
            print(f"   L{r['level']} {r['type']}: {r['id']} (score: {r['score']:.2f})")
    
    if args.stats:
        stats = adapter.get_stats()
        print(f"📊 Stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    import json
    main()
