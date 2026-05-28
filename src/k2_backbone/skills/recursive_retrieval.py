"""
K2-Backbone Recursive Context Retrieval
Integrates https://github.com/0x-wzw/openclaw-recursive-retrieval into K2-Backbone
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import time


class MemoryLayer(Enum):
    """Memory hierarchy layers."""
    SHARED = "shared"      # L0: Global context (all agents)
    AGENT = "agent"        # L1: Agent-specific memory
    SESSION = "session"    # L2: Session-local working context


class MergeStrategy(Enum):
    """How to merge values across layers."""
    OVERLAY = "overlay"    # Higher layers override lower
    COMBINE = "combine"    # Merge lists/sets, override scalars
    APPEND = "append"      # Always append to lists


@dataclass
class TraversalConfig:
    """Configuration for context tree traversal."""
    max_depth: int = 3
    min_relevance: float = 0.5
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    merge_strategy: MergeStrategy = MergeStrategy.OVERLAY
    include_metadata: bool = True


@dataclass
class ContextNode:
    """A node in the context tree."""
    key: str
    value: Any
    layer: MemoryLayer
    relevance: float = 1.0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    source: Optional[str] = None
    
    @property
    def priority(self) -> int:
        """Layer priority: higher = more specific."""
        return {
            MemoryLayer.SHARED: 0,
            MemoryLayer.AGENT: 1,
            MemoryLayer.SESSION: 2
        }[self.layer]


class ContextTree:
    """Hierarchical context tree with layer-aware traversal.
    
    Integrates with K2-Backbone's memory architecture:
    - L0 (Shared): Global task patterns, framework configs
    - L1 (Agent): Agent-specific execution traces
    - L2 (Session): Current task context, temporary state
    """
    
    def __init__(
        self,
        shared_memory: Optional[Dict[str, Any]] = None,
        agent_memory: Optional[Dict[str, Any]] = None,
        session_memory: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Initialize context tree from three memory layers.
        
        Args:
            shared_memory: L0 - Global/shared context
            agent_memory: L1 - Agent-specific context
            session_memory: L2 - Session-local context
            agent_id: Identifier for the agent
            session_id: Identifier for the session
        """
        self.agent_id = agent_id or "default"
        self.session_id = session_id or "default"
        self.nodes: Dict[str, ContextNode] = {}
        
        # Build tree from layers (lowest priority first)
        if shared_memory:
            self._ingest_layer(shared_memory, MemoryLayer.SHARED)
        if agent_memory:
            self._ingest_layer(agent_memory, MemoryLayer.AGENT)
        if session_memory:
            self._ingest_layer(session_memory, MemoryLayer.SESSION)
    
    def _ingest_layer(self, data: Dict[str, Any], layer: MemoryLayer, prefix: str = ""):
        """Recursively ingest a memory layer."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self._ingest_layer(value, layer, full_key)
            else:
                self.nodes[full_key] = ContextNode(
                    key=full_key,
                    value=value,
                    layer=layer,
                    source=f"{layer.value}:{self.agent_id if layer == MemoryLayer.AGENT else self.session_id}"
                )
    
    def query(self, key: str, config: Optional[TraversalConfig] = None) -> Optional[Any]:
        """Query a key with layer priority (session > agent > shared).
        
        Returns the value from the highest-priority layer that has this key.
        """
        config = config or TraversalConfig()
        
        # Find all nodes matching this key
        matching_nodes = [
            node for node in self.nodes.values()
            if node.key == key or node.key.endswith(f".{key}")
        ]
        
        if not matching_nodes:
            return None
        
        # Sort by priority (highest first), then by relevance
        matching_nodes.sort(key=lambda n: (-n.priority, -n.relevance))
        
        best_node = matching_nodes[0]
        best_node.access_count += 1
        best_node.last_accessed = time.time()
        
        return best_node.value
    
    def query_all(self, key: str, config: Optional[TraversalConfig] = None) -> List[ContextNode]:
        """Query all values for a key across all layers."""
        config = config or TraversalConfig()
        
        matching_nodes = [
            node for node in self.nodes.values()
            if node.key == key or node.key.endswith(f".{key}")
        ]
        
        # Sort by priority (highest first)
        matching_nodes.sort(key=lambda n: (-n.priority, -n.relevance))
        
        return matching_nodes
    
    def get_merged_context(self, config: Optional[TraversalConfig] = None) -> Dict[str, Any]:
        """Get fully merged context tree.
        
        Higher layers override lower layers by default (overlay strategy).
        """
        config = config or TraversalConfig()
        
        result: Dict[str, Any] = {}
        
        # Group nodes by base key (without dot notation)
        base_keys: Dict[str, List[ContextNode]] = {}
        for node in self.nodes.values():
            base_key = node.key.split(".")[-1]
            if base_key not in base_keys:
                base_keys[base_key] = []
            base_keys[base_key].append(node)
        
        # Merge by priority
        for base_key, nodes in base_keys.items():
            nodes.sort(key=lambda n: (-n.priority, -n.relevance))
            
            if config.merge_strategy == MergeStrategy.OVERLAY:
                # Highest priority wins
                result[base_key] = nodes[0].value
            elif config.merge_strategy == MergeStrategy.COMBINE:
                # Merge if lists, override if scalars
                values = [n.value for n in nodes]
                if all(isinstance(v, list) for v in values):
                    combined = []
                    for v in values:
                        combined.extend(v)
                    result[base_key] = list(set(combined))
                else:
                    result[base_key] = nodes[0].value
            elif config.merge_strategy == MergeStrategy.APPEND:
                # Always append to list
                values = [n.value for n in nodes]
                if all(isinstance(v, list) for v in values):
                    combined = []
                    for v in values:
                        combined.extend(v)
                    result[base_key] = combined
                else:
                    result[base_key] = [n.value for n in nodes]
        
        return result
    
    def traverse(self, prefix: str = "", config: Optional[TraversalConfig] = None) -> Dict[str, Any]:
        """Traverse tree with depth limit and filtering."""
        config = config or TraversalConfig()
        
        result = {}
        depth = prefix.count(".") if prefix else 0
        
        if depth >= config.max_depth:
            return result
        
        for node in self.nodes.values():
            if prefix and not node.key.startswith(prefix):
                continue
            
            if node.relevance < config.min_relevance:
                continue
            
            # Apply include/exclude patterns
            if config.include_patterns:
                if not any(self._match_pattern(node.key, p) for p in config.include_patterns):
                    continue
            
            if config.exclude_patterns:
                if any(self._match_pattern(node.key, p) for p in config.exclude_patterns):
                    continue
            
            result[node.key] = {
                "value": node.value,
                "layer": node.layer.value,
                "relevance": node.relevance,
                "access_count": node.access_count,
                "source": node.source
            }
        
        return result
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Match key against glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def update_session(self, updates: Dict[str, Any]):
        """Update session-level context (L2)."""
        self._ingest_layer(updates, MemoryLayer.SESSION)
    
    def update_agent(self, updates: Dict[str, Any]):
        """Update agent-level context (L1)."""
        self._ingest_layer(updates, MemoryLayer.AGENT)
    
    def update_shared(self, updates: Dict[str, Any]):
        """Update shared context (L0)."""
        self._ingest_layer(updates, MemoryLayer.SHARED)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize tree to dictionary."""
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "nodes": {
                key: {
                    "value": node.value,
                    "layer": node.layer.value,
                    "relevance": node.relevance,
                    "access_count": node.access_count,
                    "last_accessed": node.last_accessed,
                    "source": node.source
                }
                for key, node in self.nodes.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextTree":
        """Deserialize tree from dictionary."""
        tree = cls(
            agent_id=data.get("agent_id", "default"),
            session_id=data.get("session_id", "default")
        )
        
        for key, node_data in data.get("nodes", {}).items():
            layer = MemoryLayer(node_data.get("layer", "shared"))
            tree.nodes[key] = ContextNode(
                key=key,
                value=node_data["value"],
                layer=layer,
                relevance=node_data.get("relevance", 1.0),
                access_count=node_data.get("access_count", 0),
                last_accessed=node_data.get("last_accessed", time.time()),
                source=node_data.get("source")
            )
        
        return tree


class K2BackboneMemoryBridge:
    """Bridge between K2-Backbone and recursive retrieval.
    
    Integrates with Obliviarch compression levels:
    - Episodic (L2): Raw execution traces from current session
    - Semantic (L1): Compressed patterns from agent history
    - Archetypal (L0): Behavioral DNA, shared across all agents
    """
    
    def __init__(self, obliviarch_client=None):
        """Initialize with optional Obliviarch client.
        
        Args:
            obliviarch_client: Obliviarch compression client instance
        """
        self.obliviarch = obliviarch_client
        self.trees: Dict[str, ContextTree] = {}  # session_id -> tree
    
    def create_session_tree(
        self,
        session_id: str,
        agent_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
        agent_context: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> ContextTree:
        """Create a new context tree for a session.
        
        If Obliviarch is available, loads archetypal patterns (L0)
        and semantic memories (L1) automatically.
        """
        # Try to load from Obliviarch if available
        archetypal = shared_context or {}
        semantic = agent_context or {}
        
        if self.obliviarch:
            try:
                # Load archetypal patterns (L0)
                archetypal_data = self.obliviarch.query_archetypal(agent_id=agent_id)
                if archetypal_data:
                    archetypal.update(archetypal_data)
                
                # Load semantic memories (L1)
                semantic_data = self.obliviarch.query_semantic(agent_id=agent_id)
                if semantic_data:
                    semantic.update(semantic_data)
            except Exception as e:
                print(f"K2MemoryBridge: Obliviarch load failed ({e}), using defaults")
        
        tree = ContextTree(
            shared_memory=archetypal,
            agent_memory=semantic,
            session_memory=session_context or {},
            agent_id=agent_id,
            session_id=session_id
        )
        
        self.trees[session_id] = tree
        return tree
    
    def get_tree(self, session_id: str) -> Optional[ContextTree]:
        """Get existing context tree for session."""
        return self.trees.get(session_id)
    
    def ingest_execution_trace(
        self,
        session_id: str,
        trace: Dict[str, Any],
        auto_compress: bool = True
    ):
        """Ingest an execution trace into session memory.
        
        If auto_compress is True and Obliviarch is available,
        triggers compression when episodic threshold is reached.
        """
        tree = self.trees.get(session_id)
        if not tree:
            print(f"K2MemoryBridge: No tree for session {session_id}")
            return
        
        # Update session memory with trace
        tree.update_session({
            f"trace_{int(time.time())}": trace
        })
        
        # Trigger compression if needed
        if auto_compress and self.obliviarch:
            self._maybe_compress(session_id, tree)
    
    def _maybe_compress(self, session_id: str, tree: ContextTree):
        """Compress episodic traces to semantic if threshold reached."""
        # Count episodic traces
        trace_count = sum(
            1 for key in tree.nodes.keys()
            if key.startswith("trace_") and tree.nodes[key].layer == MemoryLayer.SESSION
        )
        
        # Compress when we have enough traces (threshold: 10)
        if trace_count >= 10:
            traces = [
                tree.nodes[key].value
                for key in tree.nodes.keys()
                if key.startswith("trace_") and tree.nodes[key].layer == MemoryLayer.SESSION
            ]
            
            try:
                compressed = self.obliviarch.compress_episodic(traces)
                tree.update_agent({
                    f"pattern_{hashlib.md5(str(traces).encode()).hexdigest()[:8]}": compressed
                })
                
                # Clear episodic traces (they're now compressed)
                keys_to_remove = [
                    key for key in tree.nodes.keys()
                    if key.startswith("trace_") and tree.nodes[key].layer == MemoryLayer.SESSION
                ]
                for key in keys_to_remove:
                    del tree.nodes[key]
                
                print(f"K2MemoryBridge: Compressed {trace_count} traces for session {session_id}")
            except Exception as e:
                print(f"K2MemoryBridge: Compression failed ({e})")


# Convenience functions for K2-Backbone integration

def create_context_tree(
    shared: Optional[Dict[str, Any]] = None,
    agent: Optional[Dict[str, Any]] = None,
    session: Optional[Dict[str, Any]] = None
) -> ContextTree:
    """Create a context tree with standard K2-Backbone layers."""
    return ContextTree(
        shared_memory=shared,
        agent_memory=agent,
        session_memory=session
    )


def merge_with_k2_output(
    tree: ContextTree,
    k2_output: Dict[str, Any],
    layer: MemoryLayer = MemoryLayer.SESSION
) -> ContextTree:
    """Merge K2.6 decomposition output into context tree.
    
    Typical usage:
    - TaskSpec JSON → L2 (session)
    - Execution results → L1 (agent) after completion
    - Patterns → L0 (shared) after compression
    """
    if layer == MemoryLayer.SHARED:
        tree.update_shared(k2_output)
    elif layer == MemoryLayer.AGENT:
        tree.update_agent(k2_output)
    else:
        tree.update_session(k2_output)
    
    return tree
