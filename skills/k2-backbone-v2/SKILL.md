---
name: k2-backbone-v2
description: "K2-Backbone with Progressive Loading and Recursive Retrieval. Enhanced version with context-window-optimized skill loading and 3-layer memory architecture."
homepage: https://github.com/0x-wzw/k2-backbone
metadata:
  {
    "openclaw":
      {
        "emoji": "🎯",
        "requires": { "bins": ["python3", "pip"] },
        "install":
          [
            {
              "id": "pip",
              "kind": "pip",
              "package": "k2-backbone",
              "label": "Install K2-Backbone v2",
            },
          ],
      },
  }
---

# K2-Backbone v2 (Enhanced)

Kimi K2.6's Production Backbone with progressive skill loading and recursive context retrieval.

## What's New

### Progressive Skill Loading
- **Load only metadata** at startup (index of all skills)
- **Lazy load** full skills on demand when first referenced
- **LRU cache** with TTL keeps most-used skills in memory
- **70% reduction** in context window usage vs eager loading

### Recursive Context Retrieval
- **L0 (Shared)**: Global context, archetypal patterns, framework configs
- **L1 (Agent)**: Agent-specific execution traces and semantic memories
- **L2 (Session)**: Current task context, temporary working state
- **Layer-aware queries**: Session overrides Agent overrides Shared

## Architecture v2

```
User Task
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Progressive Skill Loader (src/skills/progressive_loader.py) │
│ - Index all framework skills at startup                   │
│ - Load full content only when referenced                  │
└────────────────────┬──────────────────────────────────────┘
                     │
    ┌────────────────▼────────────────┐
    │ K2Decomposer (K2.6)               │
    │ - Lazy loads prompt templates     │
    │ - Only when decomposition needed  │
    └────────────┬──────────────────────┘
                 │ TaskSpec JSON
    ┌────────────▼──────────────────────┐
    │ NecroSwarmRouter v2               │
    │ - Lazy loads voting strategies    │
    │ - Borda/cost-first on demand      │
    └────────────┬──────────────────────┘
                 │ Routed subtasks
    ┌────────────▼──────────────────────┐
    │ NeuroSwarmIntegrated Executor     │
    │ - Loads GBrain/Council skills     │
    │ - Only when execution starts      │
    └────────────┬──────────────────────┘
                 │ Execution trace
    ┌────────────▼──────────────────────┐
    │ Recursive Context Retrieval       │
    │ (src/skills/recursive_retrieval.py)│
    │ L0: Shared (archetypal)           │
    │ L1: Agent (semantic)              │
    │ L2: Session (episodic)            │
    └────────────┬──────────────────────┘
                 │ Compressed traces
    ┌────────────▼──────────────────────┐
    │ ObliviarchAdapter                 │
    │ - Auto-promote when thresholds    │
    └───────────────────────────────────┘
```

## Commands

### Full Pipeline (v2)

```bash
# Run with progressive loading and recursive retrieval
python -m k2_backbone.core.cli_v2 "Build a REST API" --progressive --recursive

# Or set as defaults
export K2_PROGRESSIVE_LOADING=true
export K2_RECURSIVE_RETRIEVAL=true
python -m k2_backbone.core.cli_v2 "Build a REST API"
```

### Individual Components

```python
from k2_backbone.skills.progressive_loader import get_skill_registry
from k2_backbone.skills.recursive_retrieval import create_context_tree, K2BackboneMemoryBridge

# Progressive loading
registry = get_skill_registry("/path/to/frameworks")
index = registry.get_all_index_summaries()

# Get a skill on-demand (lazy loaded)
skill = registry.get_framework_skill("necroswarm", "cost_router")

# Recursive context tree
tree = create_context_tree(
    shared={"framework": "k2-backbone", "version": "2.0"},
    agent={"agent_id": "agent_001", "capabilities": ["routing", "execution"]},
    session={"task_id": "task_123", "stage": "decomposition"}
)

# Query with layer priority
value = tree.query("task_id")  # Returns "task_123" from L2
```

### Memory Bridge

```python
from k2_backbone.skills.recursive_retrieval import K2BackboneMemoryBridge
from k2_backbone.memory.obliviarch_adapter import ObliviarchClient

# Initialize with Obliviarch
obliviarch = ObliviarchClient()
bridge = K2BackboneMemoryBridge(obliviarch)

# Create session tree (auto-loads archetypal + semantic)
tree = bridge.create_session_tree(
    session_id="session_001",
    agent_id="agent_001",
    session_context={"task": "Build API"}
)

# Ingest execution traces (auto-compresses at threshold)
bridge.ingest_execution_trace("session_001", {
    "subtask": "Design endpoints",
    "model": "kimi-k2.6",
    "duration": 2.5,
    "success": True
})
```

## Configuration

```bash
# Progressive Loading
export K2_PROGRESSIVE_LOADING=true        # Enable lazy loading
export K2_MAX_CACHED_SKILLS=10            # LRU cache size
export K2_CACHE_TTL=3600                  # Cache TTL in seconds

# Recursive Retrieval
export K2_RECURSIVE_RETRIEVAL=true        # Enable 3-layer memory
export K2_MEMORY_LAYERS=3                 # L0 + L1 + L2
export K2_COMPRESSION_THRESHOLD=10        # Auto-compress after N traces
```

## Integration with Existing Repos

### Progressive Loading (github.com/0x-wzw/progressive-loading)

The `progressive_loader.py` module adapts the standalone skill into K2-Backbone's framework registry. All framework skills (necroswarm, neuroswarm, obliviarch, etc.) are now lazily loaded.

### Recursive Retrieval (github.com/0x-wzw/openclaw-recursive-retrieval)

The `recursive_retrieval.py` module integrates the 3-layer context hierarchy into K2-Backbone's memory architecture:
- **Episodic traces** → L2 (session)
- **Semantic patterns** → L1 (agent)
- **Archetypal DNA** → L0 (shared)

## Performance Improvements

| Metric | v1 (Baseline) | v2 (Enhanced) | Improvement |
|--------|---------------|---------------|-------------|
| Startup Time | 5-10s | 0.5-1s | **5-10x faster** |
| Context Window | 50-80% full | 10-20% full | **70% reduction** |
| Memory Access | Flat lookup | Layer-prioritized | **More relevant** |
| Skill Loading | Eager | Lazy | **On-demand** |

## Files

- Enhanced Loader: `src/skills/progressive_loader.py`
- Recursive Retrieval: `src/skills/recursive_retrieval.py`
- Integration Tests: `tests/unit/test_skills_integration.py`
