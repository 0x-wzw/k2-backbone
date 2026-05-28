from __future__ import annotations
"""
Deterministic Retrieval Adapter for K2-Backbone

Predictable, path-based file and memory retrieval with:
- Exact path lookup (fastest, most reliable)
- Glob/wildcard pattern matching
- Hybrid mode: deterministic first, semantic fallback
- Confidence scoring for retrieval results
- Path normalization and caching

Ported from Nexys: unified_platform/adapters/deterministic_retrieval_adapter.py
Simplified for K2-Backbone's pipeline architecture.
"""

import glob
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    """Supported retrieval modes"""
    DETERMINISTIC = "deterministic"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class RetrievalResult:
    """Result from a retrieval operation"""
    path: str
    content: Any
    exists: bool
    mode: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchResult:
    """Result from a search operation"""
    key: str
    data: Any
    score: float
    metadata: Dict[str, Any] = None


class DeterministicRetrievalAdapter:
    """
    Predictable Path-Based Retrieval for K2-Backbone.
    
    Core principle: Same input always produces same output.
    
    Usage:
        adapter = DeterministicRetrievalAdapter()
        
        # Exact path retrieval
        entry = adapter.retrieve("memory/2026-05-28.md")
        
        # Glob search
        results = adapter.search("memory/2026-*.md")
        
        # Hybrid: try exact, then semantic fallback
        adapter.set_mode(RetrievalMode.HYBRID)
        entry = adapter.retrieve("latest session notes")
    """
    
    def __init__(
        self,
        memory_base: str = "~/.openclaw/workspace/memory",
        workspace_base: str = "~/.openclaw/workspace",
        default_mode: RetrievalMode = RetrievalMode.DETERMINISTIC,
        enable_glob: bool = True,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 300,
        max_file_size_mb: float = 10.0,
    ):
        self.memory_base = Path(memory_base).expanduser().resolve()
        self.workspace_base = Path(workspace_base).expanduser().resolve()
        self.mode = default_mode
        self.enable_glob = enable_glob
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl_seconds
        self.max_file_size_mb = max_file_size_mb
        
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize retrieval engine"""
        if self._initialized:
            return
        
        self.memory_base.mkdir(parents=True, exist_ok=True)
        self.workspace_base.mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        logger.info(f"DeterministicRetrievalAdapter initialized (mode: {self.mode.value})")
    
    def set_mode(self, mode: RetrievalMode) -> None:
        """Set retrieval mode"""
        self.mode = mode
        logger.info(f"Retrieval mode set to: {mode.value}")
    
    # ==================== Path Resolution ====================
    
    def _resolve_path(self, key: str) -> Path:
        """Resolve a key to an absolute path"""
        path = Path(key)
        
        if path.is_absolute():
            return path
        
        # Try memory base first
        memory_path = self.memory_base / path
        if memory_path.exists():
            return memory_path
        
        # Try workspace base
        workspace_path = self.workspace_base / path
        if workspace_path.exists():
            return workspace_path
        
        # Default to memory base
        return memory_path
    
    def _is_glob_pattern(self, key: str) -> bool:
        """Check if key contains glob patterns"""
        return any(c in key for c in "*?[]")
    
    def _read_file(self, path: Path) -> Optional[str]:
        """Read file contents safely"""
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > self.max_file_size_mb:
                logger.warning(f"File too large: {path} ({size_mb:.1f} MB)")
                return None
            
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
                
        except Exception as e:
            logger.warning(f"Could not read {path}: {e}")
            return None
    
    def _get_cache_key(self, key: str, mode: str) -> str:
        """Generate cache key"""
        return f"{mode}:{key}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get from cache if valid"""
        if not self.enable_cache:
            return None
        
        cached = self._cache.get(cache_key)
        if not cached:
            return None
        
        age = (datetime.now() - cached["timestamp"]).total_seconds()
        if age > self.cache_ttl:
            del self._cache[cache_key]
            return None
        
        return cached["data"]
    
    def _set_in_cache(self, cache_key: str, data: Any) -> None:
        """Store in cache"""
        if not self.enable_cache:
            return
        
        # Evict oldest if cache too large
        if len(self._cache) >= 1000:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest]
        
        self._cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now(),
        }
    
    # ==================== Core Retrieval ====================
    
    def store(self, key: str, data: Any) -> None:
        """Store data at deterministic path"""
        self._ensure_initialized()
        
        path = self._resolve_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        content = json.dumps(data, indent=2, default=str) if not isinstance(data, str) else data
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Invalidate cache
        for mode in ["deterministic", "semantic", "hybrid"]:
            cache_key = self._get_cache_key(key, mode)
            if cache_key in self._cache:
                del self._cache[cache_key]
        
        logger.debug(f"Stored at: {path}")
    
    def retrieve(self, key: str) -> Optional[RetrievalResult]:
        """Retrieve with deterministic path resolution"""
        self._ensure_initialized()
        
        cache_key = self._get_cache_key(key, self.mode.value)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        result = None
        
        # DETERMINISTIC or HYBRID
        if self.mode in (RetrievalMode.DETERMINISTIC, RetrievalMode.HYBRID):
            result = self._deterministic_retrieve(key)
        
        # SEMANTIC or HYBRID fallback
        if not result and self.mode in (RetrievalMode.SEMANTIC, RetrievalMode.HYBRID):
            result = self._semantic_retrieve(key)
        
        if result:
            self._set_in_cache(cache_key, result)
        
        return result
    
    def _deterministic_retrieve(self, key: str) -> Optional[RetrievalResult]:
        """Exact path-based retrieval"""
        path = self._resolve_path(key)
        
        if path.exists():
            content = self._read_file(path)
            if content is not None:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = content
                
                return RetrievalResult(
                    path=str(path),
                    content=data,
                    exists=True,
                    mode="deterministic",
                    confidence=1.0,
                    metadata={
                        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                        "size": path.stat().st_size,
                    }
                )
        
        return None
    
    def _semantic_retrieve(self, key: str) -> Optional[RetrievalResult]:
        """Semantic fallback retrieval"""
        query_lower = key.lower().replace(" ", "_").replace("-", "_")
        
        for ext in [".md", ".txt", ".json", ".py"]:
            pattern = f"**/*{query_lower}*{ext}"
            
            for base in [self.memory_base, self.workspace_base]:
                matches = list(base.glob(pattern))
                if matches:
                    best = matches[0]
                    content = self._read_file(best)
                    if content is not None:
                        try:
                            data = json.loads(content)
                        except json.JSONDecodeError:
                            data = content
                        
                        return RetrievalResult(
                            path=str(best.relative_to(base)),
                            content=data,
                            exists=True,
                            mode="semantic",
                            confidence=0.85,
                        )
        
        return None
    
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Search with glob pattern support"""
        self._ensure_initialized()
        
        results = []
        
        # Glob patterns
        if self._is_glob_pattern(query) and self.enable_glob:
            for base in [self.memory_base, self.workspace_base]:
                try:
                    matches = list(base.glob(query))[:100]
                    for match in matches:
                        if match.is_file():
                            content = self._read_file(match)
                            if content is not None:
                                try:
                                    data = json.loads(content)
                                except json.JSONDecodeError:
                                    data = content
                                
                                results.append(SearchResult(
                                    key=str(match.relative_to(base)),
                                    data=data,
                                    score=0.95,
                                ))
                except Exception as e:
                    logger.warning(f"Glob search failed: {e}")
        
        # Non-glob: filename search
        else:
            query_lower = query.lower()
            
            for base in [self.memory_base, self.workspace_base]:
                for path in base.rglob("*"):
                    if not path.is_file():
                        continue
                    
                    score = 0.0
                    if query_lower in path.name.lower():
                        score = 1.0
                    
                    if score > 0:
                        content = self._read_file(path)
                        if content is not None:
                            try:
                                data = json.loads(content)
                            except json.JSONDecodeError:
                                data = content
                            
                            results.append(SearchResult(
                                key=str(path.relative_to(base)),
                                data=data,
                                score=score,
                            ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def delete(self, key: str) -> bool:
        """Delete file at deterministic path"""
        path = self._resolve_path(key)
        
        if path.exists():
            path.unlink()
            
            # Invalidate cache
            for mode in ["deterministic", "semantic", "hybrid"]:
                cache_key = self._get_cache_key(key, mode)
                if cache_key in self._cache:
                    del self._cache[cache_key]
            
            return True
        
        return False
    
    def exists(self, key: str) -> bool:
        """Check if path exists"""
        self._ensure_initialized()
        return self._resolve_path(key).exists()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        file_count = 0
        total_size = 0
        
        for base in [self.memory_base, self.workspace_base]:
            for path in base.rglob("*"):
                if path.is_file():
                    file_count += 1
                    total_size += path.stat().st_size
        
        return {
            "mode": self.mode.value,
            "file_count": file_count,
            "total_size_bytes": total_size,
            "cache_entries": len(self._cache),
            "memory_base": str(self.memory_base),
            "workspace_base": str(self.workspace_base),
            "glob_enabled": self.enable_glob,
            "cache_enabled": self.enable_cache,
        }
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deterministic Retrieval Adapter")
    parser.add_argument("--store", nargs=2, metavar=("KEY", "VALUE"), help="Store data")
    parser.add_argument("--retrieve", metavar="KEY", help="Retrieve data")
    parser.add_argument("--search", metavar="QUERY", help="Search")
    parser.add_argument("--delete", metavar="KEY", help="Delete")
    parser.add_argument("--exists", metavar="KEY", help="Check exists")
    parser.add_argument("--stats", action="store_true", help="Show stats")
    parser.add_argument("--mode", choices=["deterministic", "semantic", "hybrid"], default="deterministic")
    args = parser.parse_args()
    
    adapter = DeterministicRetrievalAdapter()
    adapter.set_mode(RetrievalMode(args.mode))
    
    if args.store:
        adapter.store(args.store[0], args.store[1])
        print(f"✅ Stored: {args.store[0]}")
    
    if args.retrieve:
        result = adapter.retrieve(args.retrieve)
        if result:
            print(f"✅ Found ({result.mode}, confidence: {result.confidence}):")
            print(f"   {result.content[:200]}...")
        else:
            print(f"❌ Not found: {args.retrieve}")
    
    if args.search:
        results = adapter.search(args.search)
        print(f"🔍 Found {len(results)} results:")
        for r in results[:5]:
            print(f"   {r.key} (score: {r.score:.2f})")
    
    if args.delete:
        success = adapter.delete(args.delete)
        print(f"{'✅' if success else '❌'} Deleted: {args.delete}")
    
    if args.exists:
        exists = adapter.exists(args.exists)
        print(f"{'✅' if exists else '❌'} Exists: {args.exists}")
    
    if args.stats:
        stats = adapter.get_stats()
        print(f"📊 Stats:")
        for k, v in stats.items():
            print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
