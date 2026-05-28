# K2-Backbone vs. NeuroSwarm

## Executive Summary

**NeuroSwarm** is a **standalone dual-phase system** (GBrain + NecroSwarm) with deep implementations — it ships as a Python package with executable skills.

**K2-Backbone's executor** is a **lightweight adapter** that implements the same dual-phase concept (GBrain validate + NecroSwarm execute) but plugs into a broader pipeline (K2.6 decomposition, AutoMon bridge, Obliviarch memory).

**The relationship:** K2-Backbone's executor is a **simplified, pipeline-integrated version** of NeuroSwarm's core concept. NeuroSwarm is the deep implementation; K2-Backbone is the broad integration.

---

## Architecture Comparison

### NeuroSwarm (Standalone System)

```
neuroswarm/
├── brain/              # 🧠 WHAT phase (deep implementation)
│   ├── resolver.py     # 35+ intent patterns
│   ├── signal_detector.py  # Always-on entity extraction
│   ├── brain_first.py  # Memory-first lookup
│   ├── enrichment.py   # Tier-based entity compounding
│   └── knowledge_store.py  # RRF hybrid search
├── swarm/              # ☠️ HOW phase (deep implementation)
│   ├── council.py      # 10-D council deliberation
│   ├── pre_spawn.py    # 3-question spawn gate
│   ├── refusal_routing.py  # Dimension-aware fallback
│   ├── sparring.py     # Human-agent challenge mode
│   └── dimension_map.py    # D1-D10 model config
└── bridge/             # 🌉 Context feed
    └── context_feed.py
```

**Key feature:** Skills are **fat markdown** (thin harness, fat skills philosophy).

### K2-Backbone Executor (Pipeline Adapter)

```
k2-backbone/src/executor/
└── neuroswarm_executor.py   # Lightweight dual-phase adapter
```

**Key feature:** Plugs into broader pipeline — receives TaskSpec from K2.6, outputs to Obliviarch.

---

## Component Comparison

### Phase 1: WHAT (Brain / Validator)

| Component | NeuroSwarm (Deep) | K2-Backbone (Light) |
|---|---|---|
| **Intent resolution** | `resolver.py` — 35+ patterns, skill dispatch table | `GBrainValidator.validate()` — dependency cycle check, budget sanity |
| **Memory check** | `brain_first.py` — PGLite/Postgres RRF search | Context dict passed from pipeline |
| **Signal detection** | `signal_detector.py` — always-on entity extraction | Not implemented (pipeline assumption: task already clear) |
| **Enrichment** | `enrichment.py` — Tier 1/2/3 entity compounding | Not implemented (K2.6 decomposition provides context) |
| **Knowledge store** | `knowledge_store.py` — hybrid vector + keyword search | Delegated to Obliviarch + Deterministic Retrieval |

**Verdict:** NeuroSwarm's brain is **feature-rich** — it has its own memory system, entity extraction, and enrichment. K2-Backbone's validator is **minimal** — it assumes the heavy lifting (intent, context, decomposition) was done upstream by K2.6.

### Phase 2: HOW (Swarm / Executor)

| Component | NeuroSwarm (Deep) | K2-Backbone (Light) |
|---|---|---|
| **Council** | `council.py` — 10-D deliberation with dimension-aware voting | `NecroSwarmRouter.route()` — Borda voting with cost optimization |
| **Pre-spawn** | `pre_spawn.py` — 3-question gate (complexity? parallel? tokens?) | `GBrainValidator._validate()` — basic dependency/budget checks |
| **Fallback** | `refusal_routing.py` — dimension-aware model fallback chains | Router retry with cheapest model |
| **Sparring** | `sparring.py` — human challenges, agent drives | Not implemented (batch mode assumption) |
| **Dimension map** | `dimension_map.py` — D1-D10 configuration | Inline `COUNCIL_CONFIG` dict |

**Verdict:** NeuroSwarm's swarm is **interaction-rich** — it has sparring mode, refusal routing, and pre-spawn gates for interactive use. K2-Backbone's executor is **batch-optimized** — it parallelizes subtasks and retries on failure, assuming non-interactive execution.

---

## Philosophy Comparison

### NeuroSwarm: Thin Harness, Fat Skills

> "The bottleneck is never the model's intelligence. The bottleneck is whether the model understands your schema." — Garry Tan

- Skills are **fat markdown documents** encoding entire workflows
- Runtime is **thin** — just dispatches to skills
- Intelligence lives in **skills**, not infrastructure
- **Hermes Agent** integration: skills live in `~/.hermes/skills/`

### K2-Backbone: Broad Pipeline, Thin Adapters

> "K2.6 decomposes. We execute, audit, compress, and federate."

- Adapters are **thin** — just translate between formats
- Intelligence lives in **models** (K2.6, 10-D Council)
- Runtime is **rich** — full pipeline with memory, federation, cost tracking
- **RuFlo plugin** integration: adapters live in `plugins/ruflo-k2-backbone/`

---

## Code Comparison

### NeuroSwarm: Full Dispatcher

```python
# neuroswarm/dispatcher.py
class NeuroSwarmDispatcher:
    def dispatch(self, query: str, context: str = "") -> dict:
        # Phase 1: Brain resolves intent
        brain_result = self.resolve_intent(query)
        
        # Phase 2: Swarm deliberates
        complexity = brain_result["primary"]["complexity"]
        if complexity == "SIMPLE":
            return direct_execution(brain_result)
        elif complexity == "MODERATE":
            seats = ["D7_general", "D9_research"]
            verdict = self.council.deliberate(query, seats=seats, ...)
            return {"approach": "quick_council", "verdict": verdict}
        else:  # COMPLEX
            seats = ["D1_synthesis", "D2_deep_reason", "D5_strategy"]
            verdict = self.council.deliberate(query, seats=seats, ...)
            return {"approach": "full_council", "verdict": verdict}
```

### K2-Backbone: Lightweight Executor

```python
# src/executor/neuroswarm_executor.py
class NeuroSwarmExecutor:
    def run(self, routed_spec: dict) -> dict:
        # Phase 1: Validate plan
        is_valid, warnings = self.validator.validate(routed_spec)
        
        # Phase 2: Execute subtasks
        trace = self.executor.execute(routed_spec)
        
        return {
            "status": "completed",
            "execution_trace": trace.to_dict(),
            "summary": {...},
        }
```

**Key difference:**
- NeuroSwarm's dispatcher is **interactive** — it resolves intent, detects signals, then decides council size
- K2-Backbone's executor is **batch** — it validates a pre-decomposed TaskSpec, then executes in parallel

---

## Integration Strategy

### Option A: Use NeuroSwarm as-is (Standalone)

Keep NeuroSwarm as your primary agent system. K2-Backbone is a separate tool for K2.6-specific tasks.

**Pros:** Full NeuroSwarm feature set (sparring, signal detection, enrichment)
**Cons:** Two separate systems to maintain

### Option B: Replace K2-Backbone Executor with NeuroSwarm (Recommended)

Swap `src/executor/neuroswarm_executor.py` for NeuroSwarm's full dispatcher.

```python
# In k2_backbone/core/cli.py:
from neuroswarm.dispatcher import NeuroSwarmDispatcher

class K2Backbone:
    def __init__(self):
        self.decomposer = K2Decomposer(...)  # K2.6 decomposition
        self.router = NecroSwarmRouter(...)  # 10-D Council voting
        self.executor = NeuroSwarmDispatcher(...)  # ← Full NeuroSwarm
        self.memory = ObliviarchAdapter(...)  # Compression
```

**Pros:** Get NeuroSwarm's full power + K2-Backbone's pipeline
**Cons:** Adds dependency on NeuroSwarm package

### Option C: Merge Concepts (Hybrid)

Keep K2-Backbone's lightweight executor for batch tasks, use NeuroSwarm for interactive tasks.

```python
if task_mode == "interactive":
    executor = NeuroSwarmDispatcher()
else:  # batch
    executor = NeuroSwarmExecutor()  # K2-Backbone lightweight
```

---

## Recommendation

**Go with Option B: Wire NeuroSwarm's dispatcher into K2-Backbone's executor slot.**

Rationale:
1. NeuroSwarm is **deeper** — it has signal detection, enrichment, sparring
2. K2-Backbone is **broader** — it has K2.6, AutoMon bridge, Obliviarch
3. **Merge at the executor level** — keep K2-Backbone's pipeline, swap in NeuroSwarm's dispatch

This gives you:
- K2.6 decomposition (unique to K2-Backbone)
- NeuroSwarm's full dual-phase execution (deep, interactive)
- Obliviarch compression (unique to K2-Backbone)
- AutoMon bridge (unique to K2-Backbone)
- Unified cost tracking (unique to K2-Backbone)

**The result:** NeuroSwarm's brain + swarm inside K2-Backbone's pipeline.

---

## Next Steps

1. **Add NeuroSwarm as submodule** to K2-Backbone
2. **Replace** `src/executor/neuroswarm_executor.py` with NeuroSwarm's `dispatcher.py`
3. **Wire** NeuroSwarm's brain context into K2-Backbone's pipeline
4. **Keep** K2-Backbone's router (cost-optimized) as pre-filter before NeuroSwarm's council

**Nexys asked the question. K2-Backbone builds the bridge. NeuroSwarm provides the brain.**
