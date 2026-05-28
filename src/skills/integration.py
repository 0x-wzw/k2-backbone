"""
K2-Backbone v2 Integration Module

Provides unified interface for Progressive Loading + Recursive Retrieval
"""

from pathlib import Path
from typing import Optional, Dict, Any

from skills.progressive_loader import ProgressiveSkillLoader, K2BackboneSkillRegistry
from skills.recursive_retrieval import ContextTree, K2BackboneMemoryBridge, create_context_tree


class K2BackboneV2:
    """Enhanced K2-Backbone with progressive loading and recursive retrieval.
    
    Usage:
        backbone = K2BackboneV2(
            frameworks_dir="/path/to/frameworks",
            enable_progressive=True,
            enable_recursive=True
        )
        
        # Skills are lazily loaded
        skill = backbone.get_skill("necroswarm", "cost_router")
        
        # Context is retrieved from 3 layers
        tree = backbone.create_session("session_001", "agent_001")
        value = tree.query("task_id")
    """
    
    def __init__(
        self,
        frameworks_dir: Optional[Path] = None,
        enable_progressive: bool = True,
        enable_recursive: bool = True,
        obliviarch_client=None
    ):
        """Initialize enhanced K2-Backbone.
        
        Args:
            frameworks_dir: Path to frameworks/ directory
            enable_progressive: Enable progressive skill loading
            enable_recursive: Enable recursive context retrieval
            obliviarch_client: Optional Obliviarch compression client
        """
        self.enable_progressive = enable_progressive
        self.enable_recursive = enable_recursive
        
        # Progressive loading
        self.skill_registry = None
        if enable_progressive:
            self.skill_registry = K2BackboneSkillRegistry(frameworks_dir)
        
        # Recursive retrieval
        self.memory_bridge = None
        if enable_recursive:
            self.memory_bridge = K2BackboneMemoryBridge(obliviarch_client)
    
    def get_skill(self, framework: str, skill_name: str):
        """Get a skill from a framework (lazily loaded)."""
        if not self.skill_registry:
            raise RuntimeError("Progressive loading not enabled")
        
        return self.skill_registry.get_framework_skill(framework, skill_name)
    
    def create_session(
        self,
        session_id: str,
        agent_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
        agent_context: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> ContextTree:
        """Create a session context tree with 3-layer memory.
        
        If recursive retrieval is enabled, automatically loads archetypal
        and semantic layers from Obliviarch (if available).
        """
        if not self.memory_bridge:
            # Fallback to basic context tree
            return create_context_tree(
                shared=shared_context,
                agent=agent_context,
                session=session_context
            )
        
        return self.memory_bridge.create_session_tree(
            session_id=session_id,
            agent_id=agent_id,
            shared_context=shared_context,
            agent_context=agent_context,
            session_context=session_context
        )
    
    def ingest_trace(self, session_id: str, trace: Dict[str, Any]):
        """Ingest an execution trace into session memory."""
        if not self.memory_bridge:
            raise RuntimeError("Recursive retrieval not enabled")
        
        self.memory_bridge.ingest_execution_trace(session_id, trace)


# Convenience factory
def create_k2_v2(
    frameworks_dir: Optional[str] = None,
    **kwargs
) -> K2BackboneV2:
    """Factory function to create K2-Backbone v2 instance."""
    fw_dir = Path(frameworks_dir) if frameworks_dir else None
    return K2BackboneV2(frameworks_dir=fw_dir, **kwargs)
