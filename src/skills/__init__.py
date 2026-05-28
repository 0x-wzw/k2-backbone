"""
K2-Backbone Skills Package
Integrates Progressive Loading and Recursive Retrieval
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
]
