"""
Unit tests for K2-Backbone skill integrations
Progressive Loading + Recursive Retrieval
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from skills.progressive_loader import (
    ProgressiveSkillLoader,
    K2BackboneSkillRegistry,
    get_skill_registry,
    Skill,
    SkillIndex
)
from skills.recursive_retrieval import (
    ContextTree,
    K2BackboneMemoryBridge,
    create_context_tree,
    merge_with_k2_output,
    MemoryLayer,
    MergeStrategy,
    TraversalConfig
)


class TestProgressiveSkillLoader:
    """Test progressive skill loading."""
    
    @pytest.fixture
    def mock_skills_dir(self):
        """Create a temporary directory with mock skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            
            # Create mock skills
            for skill_name in ["security-scanner", "cost-router", "api-builder"]:
                skill_dir = skills_dir / skill_name
                skill_dir.mkdir()
                
                skill_md = skill_dir / "SKILL.md"
                skill_md.write_text(f"""---
name: {skill_name}
description: "Test skill: {skill_name}"
version: "1.0.0"
keywords: [test, {skill_name}]
---

# {skill_name}

This is a test skill for {skill_name}.
""")
            
            yield skills_dir
    
    def test_index_loading(self, mock_skills_dir):
        """Test that only metadata is loaded at startup."""
        loader = ProgressiveSkillLoader(mock_skills_dir)
        
        assert len(loader.index) == 3
        assert "security-scanner" in loader.index
        
        # Verify only metadata, not content
        idx = loader.index["security-scanner"]
        assert idx.name == "security-scanner"
        assert "Test skill" in idx.description
        assert idx.size > 0
        assert not hasattr(idx, 'content') or not isinstance(getattr(idx, 'content', None), str)
    
    def test_lazy_loading(self, mock_skills_dir):
        """Test that full skills are loaded on demand."""
        loader = ProgressiveSkillLoader(mock_skills_dir, max_cached=2)
        
        # Initially empty cache
        assert len(loader.cache) == 0
        
        # Load first skill
        skill = loader.get_skill("security-scanner")
        assert skill is not None
        assert "# security-scanner" in skill.content
        assert len(loader.cache) == 1
        
        # Load second skill
        skill2 = loader.get_skill("cost-router")
        assert skill2 is not None
        assert len(loader.cache) == 2
        
        # Load third skill (should evict first)
        skill3 = loader.get_skill("api-builder")
        assert skill3 is not None
        assert len(loader.cache) == 2  # Max cache size
        assert "security-scanner" not in loader.cache  # Evicted
    
    def test_lru_eviction(self, mock_skills_dir):
        """Test LRU eviction behavior."""
        loader = ProgressiveSkillLoader(mock_skills_dir, max_cached=2)
        
        # Load skills
        loader.get_skill("security-scanner")
        loader.get_skill("cost-router")
        
        # Access first skill (makes it recently used)
        loader.get_skill("security-scanner")
        
        # Load third skill (should evict cost-router)
        loader.get_skill("api-builder")
        
        assert "security-scanner" in loader.cache
        assert "cost-router" not in loader.cache
    
    def test_search(self, mock_skills_dir):
        """Test skill search by keyword."""
        loader = ProgressiveSkillLoader(mock_skills_dir)
        
        results = loader.search("security")
        assert len(results) == 1
        assert results[0].name == "security-scanner"
        
        results = loader.search("test")
        assert len(results) == 3  # All skills have 'test' keyword
    
    def test_cache_ttl(self, mock_skills_dir):
        """Test TTL-based eviction."""
        loader = ProgressiveSkillLoader(mock_skills_dir, cache_ttl=0)
        
        # Load skill with 0 TTL
        skill = loader.get_skill("security-scanner")
        assert skill is not None
        
        # Access again (should be expired and reloaded)
        skill2 = loader.get_skill("security-scanner")
        assert skill2 is not None
        # Should be a different instance (reloaded)
        assert skill is not skill2


class TestRecursiveRetrieval:
    """Test recursive context retrieval."""
    
    def test_layer_priority(self):
        """Test that higher layers override lower layers."""
        tree = ContextTree(
            shared_memory={"config": "shared_value"},
            agent_memory={"config": "agent_value"},
            session_memory={"config": "session_value"}
        )
        
        # Session (L2) should override all
        assert tree.query("config") == "session_value"
    
    def test_merge_strategies(self):
        """Test different merge strategies."""
        tree = ContextTree(
            shared_memory={"tags": ["shared"]},
            agent_memory={"tags": ["agent"]},
            session_memory={"tags": ["session"]}
        )
        
        # Overlay: highest priority wins
        overlay = tree.get_merged_context(TraversalConfig(merge_strategy=MergeStrategy.OVERLAY))
        assert overlay["tags"] == ["session"]
        
        # Combine: merge lists
        combine = tree.get_merged_context(TraversalConfig(merge_strategy=MergeStrategy.COMBINE))
        assert set(combine["tags"]) == {"shared", "agent", "session"}
    
    def test_traversal_depth(self):
        """Test max depth filtering."""
        tree = ContextTree(
            shared_memory={
                "level1": {
                    "level2": {
                        "level3": "deep_value"
                    }
                }
            }
        )
        
        # Depth 2 should exclude level3
        shallow = tree.traverse(config=TraversalConfig(max_depth=2))
        assert "level1.level2.level3" not in shallow
        
        # Depth 3 should include it
        deep = tree.traverse(config=TraversalConfig(max_depth=3))
        assert "level1.level2.level3" in deep
    
    def test_update_session(self):
        """Test updating session context."""
        tree = ContextTree(session_memory={"stage": "initial"})
        
        tree.update_session({"stage": "running", "progress": 50})
        
        assert tree.query("stage") == "running"
        assert tree.query("progress") == 50
    
    def test_serialization(self):
        """Test round-trip serialization."""
        tree = ContextTree(
            shared_memory={"key": "value"},
            agent_id="agent_001",
            session_id="session_001"
        )
        
        # Serialize
        data = tree.to_dict()
        assert data["agent_id"] == "agent_001"
        assert "nodes" in data
        
        # Deserialize
        tree2 = ContextTree.from_dict(data)
        assert tree2.agent_id == "agent_001"
        assert tree2.query("key") == "value"


class TestK2BackboneMemoryBridge:
    """Test K2-Backbone memory bridge."""
    
    def test_create_session_tree(self):
        """Test creating session tree with memory layers."""
        bridge = K2BackboneMemoryBridge()
        
        tree = bridge.create_session_tree(
            session_id="session_001",
            agent_id="agent_001",
            session_context={"task": "Build API"}
        )
        
        assert tree is not None
        assert tree.session_id == "session_001"
        assert tree.agent_id == "agent_001"
        assert tree.query("task") == "Build API"
    
    def test_ingest_execution_trace(self):
        """Test ingesting execution traces."""
        bridge = K2BackboneMemoryBridge()
        
        # Create tree
        bridge.create_session_tree(
            session_id="session_001",
            agent_id="agent_001"
        )
        
        # Ingest trace
        bridge.ingest_execution_trace("session_001", {
            "subtask": "Design endpoints",
            "success": True
        })
        
        tree = bridge.get_tree("session_001")
        trace_keys = [k for k in tree.nodes.keys() if k.startswith("trace_")]
        assert len(trace_keys) == 1


class TestIntegration:
    """Integration tests: Progressive Loading + Recursive Retrieval."""
    
    def test_skill_with_context_tree(self, mock_skills_dir):
        """Test that loaded skills can interact with context trees."""
        # Setup
        loader = ProgressiveSkillLoader(mock_skills_dir)
        tree = create_context_tree(
            shared={"framework": "k2-backbone"},
            session={"task": "Test integration"}
        )
        
        # Load a skill
        skill = loader.get_skill("security-scanner")
        assert skill is not None
        
        # Merge skill metadata into context tree
        tree = merge_with_k2_output(
            tree,
            {"loaded_skill": skill.index.name, "version": skill.index.version},
            layer=MemoryLayer.SESSION
        )
        
        assert tree.query("loaded_skill") == "security-scanner"
    
    def test_registry_with_multiple_frameworks(self):
        """Test skill registry with multiple framework directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            frameworks_dir = Path(tmpdir)
            
            # Create framework directories with skills
            for fw_name in ["necroswarm", "neuroswarm"]:
                fw_dir = frameworks_dir / fw_name / "skills"
                fw_dir.mkdir(parents=True)
                
                skill_dir = fw_dir / f"{fw_name}_router"
                skill_dir.mkdir()
                
                skill_md = skill_dir / "SKILL.md"
                skill_md.write_text(f"""---
name: {fw_name}_router
description: "Router for {fw_name}"
version: "1.0.0"
---

# {fw_name} Router
""")
            
            registry = K2BackboneSkillRegistry(frameworks_dir)
            
            assert "necroswarm" in registry.loaders
            assert "neuroswarm" in registry.loaders
            
            # Load skills from different frameworks
            skill1 = registry.get_framework_skill("necroswarm", "necroswarm_router")
            assert skill1 is not None
            
            skill2 = registry.get_framework_skill("neuroswarm", "neuroswarm_router")
            assert skill2 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
