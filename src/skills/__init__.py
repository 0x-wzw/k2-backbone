"""
K2-Backbone Skills Package
Integrates Progressive Loading, Recursive Retrieval, and Chat Routing
"""

from .progressive_loader import (
    ProgressiveSkillLoader,
    K2BackboneSkillRegistry,
    get_skill_registry,
    Skill,
    SkillIndex,
)

from .recursive_retrieval import (
    ContextTree,
    ContextNode,
    K2BackboneMemoryBridge,
    create_context_tree,
    merge_with_k2_output,
    MemoryLayer,
    MergeStrategy,
    TraversalConfig,
)

from .chat_router import K2ChatRouter, ChatConfig, route_chat
from .integration import K2BackboneV2, create_k2_v2

__all__ = [
    "ProgressiveSkillLoader",
    "K2BackboneSkillRegistry",
    "get_skill_registry",
    "Skill",
    "SkillIndex",
    "ContextTree",
    "ContextNode",
    "K2BackboneMemoryBridge",
    "create_context_tree",
    "merge_with_k2_output",
    "MemoryLayer",
    "MergeStrategy",
    "TraversalConfig",
    "K2ChatRouter",
    "ChatConfig",
    "route_chat",
    "K2BackboneV2",
    "create_k2_v2",
]
