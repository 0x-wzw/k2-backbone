"""
K2-Backbone Progressive Skill Loader
Integrates https://github.com/0x-wzw/progressive-loading into K2-Backbone
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import OrderedDict
import hashlib


@dataclass
class SkillIndex:
    """Lightweight skill metadata for indexing."""
    name: str
    description: str
    version: str
    keywords: List[str]
    triggers: List[str]
    size: int
    path: Path
    hash: str = ""
    last_loaded: Optional[float] = None


@dataclass
class Skill:
    """Full loaded skill with content and metadata."""
    index: SkillIndex
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class ProgressiveSkillLoader:
    """Load skills on-demand to optimize context window.
    
    Integration point: K2-Backbone uses this for all framework skill loading,
    keeping only metadata in context and loading full skills when needed.
    """
    
    def __init__(
        self,
        skills_dir: Path,
        max_cached: int = 10,
        cache_ttl: int = 3600,
        index_only_at_startup: bool = True
    ):
        self.skills_dir = Path(skills_dir)
        self.max_cached = max_cached
        self.cache_ttl = cache_ttl
        self.index_only_at_startup = index_only_at_startup
        
        # Index: always in memory (lightweight)
        self.index: Dict[str, SkillIndex] = {}
        
        # Cache: LRU with TTL eviction
        self.cache: OrderedDict[str, Skill] = OrderedDict()
        
        # Load index
        self._load_index()
    
    def _load_index(self):
        """Load only skill metadata at startup."""
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
                
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            
            metadata = self._parse_metadata(skill_md)
            self.index[metadata.name] = metadata
        
        print(f"ProgressiveLoader: Indexed {len(self.index)} skills (full content NOT loaded)")
    
    def _parse_metadata(self, skill_md: Path) -> SkillIndex:
        """Parse only YAML frontmatter from SKILL.md."""
        content = skill_md.read_text()
        
        # Extract frontmatter between --- markers
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                frontmatter = content[3:end].strip()
                # Parse simple key: value pairs
                metadata = {}
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip('"')
                
                size = len(content)
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                return SkillIndex(
                    name=metadata.get("name", skill_md.parent.name),
                    description=metadata.get("description", ""),
                    version=metadata.get("version", "0.0.0"),
                    keywords=metadata.get("keywords", "").strip("[]").replace(" ", "").split(",") if metadata.get("keywords") else [],
                    triggers=[],
                    size=size,
                    path=skill_md.parent,
                    hash=content_hash
                )
        
        return SkillIndex(
            name=skill_dir.name,
            description="",
            version="0.0.0",
            keywords=[],
            triggers=[],
            size=len(content),
            path=skill_md.parent
        )
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """Lazy load skill on demand with LRU cache."""
        # Check cache first
        if name in self.cache:
            skill = self.cache.pop(name)  # Remove to re-add at end (LRU)
            
            # Check TTL
            if time.time() - skill.last_accessed > self.cache_ttl:
                print(f"ProgressiveLoader: Skill '{name}' expired, reloading")
                skill = self._load_full_skill(self.index[name])
            else:
                skill.last_accessed = time.time()
                skill.usage_count += 1
            
            self.cache[name] = skill
            return skill
        
        # Load from index
        if name not in self.index:
            print(f"ProgressiveLoader: Skill '{name}' not found in index")
            return None
        
        # Enforce max cache size (LRU eviction)
        if len(self.cache) >= self.max_cached:
            self._evict_lru()
        
        # Load full skill
        skill = self._load_full_skill(self.index[name])
        self.cache[name] = skill
        
        print(f"ProgressiveLoader: Loaded '{name}' ({skill.index.size} chars) | Cache: {len(self.cache)}/{self.max_cached}")
        return skill
    
    def _load_full_skill(self, index: SkillIndex) -> Skill:
        """Load full skill content from disk."""
        skill_md = index.path / "SKILL.md"
        content = skill_md.read_text()
        
        return Skill(
            index=index,
            content=content,
            last_accessed=time.time()
        )
    
    def _evict_lru(self):
        """Remove least recently used skill from cache."""
        if not self.cache:
            return
        
        lru_name, lru_skill = self.cache.popitem(last=False)
        print(f"ProgressiveLoader: Evicted '{lru_name}' (used {lru_skill.usage_count}x)")
    
    def search(self, query: str) -> List[SkillIndex]:
        """Search index by keyword or name."""
        query_lower = query.lower()
        results = []
        
        for name, idx in self.index.items():
            if query_lower in name.lower():
                results.append(idx)
                continue
            
            for keyword in idx.keywords:
                if query_lower in keyword.lower():
                    results.append(idx)
                    break
        
        return results
    
    def get_index_summary(self) -> Dict[str, Any]:
        """Get compact index summary for context window."""
        return {
            "total_skills": len(self.index),
            "cached_skills": len(self.cache),
            "max_cache": self.max_cached,
            "cache_ttl": self.cache_ttl,
            "skills": [
                {
                    "name": idx.name,
                    "description": idx.description[:50] + "..." if len(idx.description) > 50 else idx.description,
                    "size": idx.size,
                    "keywords": idx.keywords[:5]
                }
                for idx in self.index.values()
            ]
        }


class K2BackboneSkillRegistry:
    """K2-Backbone integration: Uses progressive loading for framework skills.
    
    This registry replaces eager skill loading in K2-Backbone components
    (decomposer, router, executor, memory) with on-demand loading.
    """
    
    def __init__(self, frameworks_dir: Optional[Path] = None):
        """Initialize with frameworks directory.
        
        Args:
            frameworks_dir: Path to frameworks/ directory (with submodules)
                            Defaults to k2-backbone/frameworks/
        """
        if frameworks_dir is None:
            # Default to k2-backbone/frameworks
            self.frameworks_dir = Path(__file__).parent.parent.parent / "frameworks"
        else:
            self.frameworks_dir = Path(frameworks_dir)
        
        # Create progressive loader for each framework
        self.loaders: Dict[str, ProgressiveSkillLoader] = {}
        
        if self.frameworks_dir.exists():
            for fw_dir in self.frameworks_dir.iterdir():
                if fw_dir.is_dir() and (fw_dir / "skills").exists():
                    self.loaders[fw_dir.name] = ProgressiveSkillLoader(
                        fw_dir / "skills",
                        max_cached=5
                    )
    
    def get_framework_skill(self, framework: str, skill_name: str) -> Optional[Skill]:
        """Get a skill from a specific framework."""
        if framework not in self.loaders:
            print(f"K2SkillRegistry: Framework '{framework}' not found")
            return None
        
        return self.loaders[framework].get_skill(skill_name)
    
    def get_all_index_summaries(self) -> Dict[str, Any]:
        """Get compact summaries of all frameworks for context window."""
        return {
            fw: loader.get_index_summary()
            for fw, loader in self.loaders.items()
        }


# Singleton instance for K2-Backbone
_skill_registry: Optional[K2BackboneSkillRegistry] = None


def get_skill_registry(frameworks_dir: Optional[Path] = None) -> K2BackboneSkillRegistry:
    """Get or create singleton skill registry."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = K2BackboneSkillRegistry(frameworks_dir)
    return _skill_registry
