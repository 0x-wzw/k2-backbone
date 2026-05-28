"""
K2-Backbone v2 Integration Module

Provides unified interface for Progressive Loading + Recursive Retrieval + Chat Routing
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

from k2_backbone.skills.progressive_loader import ProgressiveSkillLoader, K2BackboneSkillRegistry
from k2_backbone.skills.recursive_retrieval import ContextTree, K2BackboneMemoryBridge, create_context_tree
from k2_backbone.skills.chat_router import K2ChatRouter, ChatConfig


class K2BackboneV2:
    """Enhanced K2-Backbone with progressive loading, recursive retrieval, and chat routing.
    
    Usage:
        backbone = K2BackboneV2(
            frameworks_dir="/path/to/frameworks",
            enable_progressive=True,
            enable_recursive=True,
            chat_model="deepseek-v4-flash"  # T0 chat model
        )
        
        # Chat with T0 model
        response = backbone.chat("Hello", session_id="sess_001")
        
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
        enable_chat: bool = True,
        chat_model: Optional[str] = None,
        obliviarch_client=None
    ):
        """Initialize enhanced K2-Backbone.
        
        Args:
            frameworks_dir: Path to frameworks/ directory
            enable_progressive: Enable progressive skill loading
            enable_recursive: Enable recursive context retrieval
            enable_chat: Enable chat routing
            chat_model: T0 chat model (default: deepseek-v4-flash)
            obliviarch_client: Optional Obliviarch compression client
        """
        self.enable_progressive = enable_progressive
        self.enable_recursive = enable_recursive
        self.enable_chat = enable_chat
        
        # Progressive loading
        self.skill_registry = None
        if enable_progressive:
            self.skill_registry = K2BackboneSkillRegistry(frameworks_dir)
        
        # Recursive retrieval
        self.memory_bridge = None
        if enable_recursive:
            self.memory_bridge = K2BackboneMemoryBridge(obliviarch_client)
        
        # Chat routing (T0: deepseek-v4-flash)
        self.chat_router = None
        if enable_chat:
            # Use environment or provided model, default to deepseek-v4-flash
            model = chat_model or os.getenv("K2_CHAT_MODEL", "deepseek-v4-flash")
            config = ChatConfig(model=model)
            self.chat_router = K2ChatRouter(config)
    
    def chat(
        self,
        message: str,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
        context_tree: Optional[ContextTree] = None
    ) -> Dict[str, Any]:
        """Chat with the T0 model (default: deepseek-v4-flash).
        
        Args:
            message: User message
            session_id: Session identifier
            system_prompt: Optional system prompt
            context_tree: Optional context tree for layer-aware context
        
        Returns:
            Response dict with model, messages, cost estimate
        """
        if not self.chat_router:
            raise RuntimeError("Chat routing not enabled")
        
        return self.chat_router.chat(
            message=message,
            session_id=session_id,
            system_prompt=system_prompt,
            context_tree=context_tree
        )
    
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
    
    def get_chat_stats(self) -> Dict[str, Any]:
        """Get chat router statistics."""
        if not self.chat_router:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "t0_model": self.chat_router.config.model,
            **self.chat_router.get_stats()
        }


# Convenience factory
def create_k2_v2(
    frameworks_dir: Optional[str] = None,
    chat_model: Optional[str] = None,
    **kwargs
) -> K2BackboneV2:
    """Factory function to create K2-Backbone v2 instance.
    
    Args:
        frameworks_dir: Path to frameworks directory
        chat_model: T0 chat model (default: deepseek-v4-flash)
        **kwargs: Additional arguments for K2BackboneV2
    
    Returns:
        Configured K2BackboneV2 instance
    """
    fw_dir = Path(frameworks_dir) if frameworks_dir else None
    return K2BackboneV2(
        frameworks_dir=fw_dir,
        chat_model=chat_model,
        **kwargs
    )
