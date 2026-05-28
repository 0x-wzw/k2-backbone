# K2-Backbone vs. Nexys

## Executive Summary

**Nexys** (your earlier work) was the **analysis + architecture phase** — it identified the problem (7 siloed frameworks, 1/21 compatibility) and designed the solution (adapter pattern + unified interfaces). It never shipped implementation.

**K2-Backbone** (this repo) is the **execution phase** — it builds on Nexys's architecture but adds K2.6 integration, production-ready adapters, and a unified CLI. It ships working code.

---

## What Nexys Did

**Status:** Analysis complete, implementation never started

| Deliverable | Status | Location |
|---|---|---|
| Framework analysis (7 frameworks) | ✅ Complete | `FRAMEWORK_ANALYSIS.md` |
| Adapter architecture design | ✅ Complete | `ADAPTER_ARCHITECTURE.md` |
| Unified interface specification | ✅ Complete | `IAgentService`, `IMemoryService`, `IWorkflowService` |
| Adapter stubs (7 files) | ⚪ Scaffolded, empty | `unified_platform/adapters/*.py` |
| Validation tools | ✅ Complete | `validate-frameworks.sh`, `test-integration.py` |
| Integration results | ✅ Complete | `integration-results/` |

**Key finding:** 1/21 framework pairs connect natively. 20/21 need adapters.

**Nexys architecture:**
```
User API
    │
    ▼
Unified Services (IAgentService, IMemoryService, IWorkflowService)
    │
    ▼
Adapter Layer (7 adapters — stubs only)
    │
    ▼
Frameworks (unchanged)
```

---

## What K2-Backbone Does

**Status:** MVP shipped, 4 working adapters

| Component | Status | File |
|---|---|---|
| Decomposer (K2.6 adapter) | ✅ Working | `src/decomposer/k2_decomposer.py` |
| Router (10-D Council) | ✅ Working | `src/router/necroswarm_router.py` |
| Executor (NeuroSwarm dual-phase) | ✅ Working | `src/executor/neuroswarm_executor.py` |
| AutoMon Bridge | ✅ Working | `src/bridge/automon_bridge.py` |
| Memory (Obliviarch) | 🟡 Stub | `frameworks/obliviarch/` |
| Federation (VoidTether) | 🟡 Stub | `frameworks/voidtether/` |
| Deterministic Retrieval | 🟡 Stub | `frameworks/deterministic-retrieval/` |
| Memory Evolution | 🟡 Stub | `frameworks/memory-evolution/` |

**K2-Backbone architecture:**
```
User Task
    │
    ▼
K2Decomposer (prompts K2.6 for JSON)
    │
    ▼
NecroSwarmRouter (Borda voting, 10-D Council)
    │
    ▼
NeuroSwarmExecutor (GBrain validate + NecroSwarm execute)
    │
    ▼
ObliviarchMemory (compression — stub)
    │
    ▼
VoidTetherFederation (cross-platform — stub)
```

---

## Detailed Comparison

### Architecture Layer

| Aspect | Nexys | K2-Backbone |
|---|---|---|
| **Design pattern** | Adapter pattern | Adapter + Pipeline pattern |
| **Interfaces** | `IAgentService`, `IMemoryService`, `IWorkflowService` | `Decomposer`, `Router`, `Executor`, `Memory`, `Federation` |
| **Service registry** | Planned (`service_registry.py`) | Not yet — direct imports |
| **Health monitoring** | Planned (`adapter_manager.py`) | Not yet — basic retry logic |
| **Plugin system** | Not addressed | RuFlo plugin scaffolded |

### Adapter Implementation

| Adapter | Nexys | K2-Backbone |
|---|---|---|
| NecroSwarm | ⚪ Empty stub | ✅ Full router with Borda voting |
| NeuroSwarm | ⚪ Empty stub | ✅ Dual-phase executor (GBrain + Council) |
| Obliviarch | ⚪ Empty stub | 🟡 Submodule only (compression not wired) |
| VoidTether | ⚪ Empty stub | 🟡 Submodule only (mesh not wired) |
| Namespace | ⚪ Empty stub | Not yet — URI resolver not integrated |
| Memory Evolution | ⚪ Empty stub | Not yet — self-improving not wired |
| Deterministic Retrieval | ⚪ Empty stub | Not yet — exact-match not wired |

### K2.6 Integration

| Aspect | Nexys | K2-Backbone |
|---|---|---|
| **K2.6 awareness** | None — predates K2.6 | Core feature — prompt-for-decomposition |
| **Decomposition** | Not addressed | `K2Decomposer` with JSON schema output |
| **TaskSpec** | Not addressed | Full JSON Schema with 12 subtask types |
| **Cost model** | Generic | K2.6-specific + AutoMon merged |

### Cost Tracking

| Aspect | Nexys | K2-Backbone |
|---|---|---|
| **Cost awareness** | None | Unified tracker (AutoMon + K2-Backbone) |
| **Savings calculation** | Not addressed | 45% AutoMon + per-subtask allocation |
| **Budget enforcement** | Not addressed | Budget fallback in router |

### CLI / User Interface

| Aspect | Nexys | K2-Backbone |
|---|---|---|
| **CLI** | Not addressed | `k2 run "task"` — unified pipeline |
| **API** | Designed (`IAgentService`) | Python classes + JSON Schema |
| **Web UI** | Not addressed | Not yet — could reuse VoidTether v0.2.0 |

---

## What Nexys Got Right (and K2-Backbone Preserves)

1. **Adapter pattern is correct** — Don't rewrite frameworks, translate between them
2. **Unified interfaces are necessary** — `IAgentService` → `Decomposer` + `Router` + `Executor`
3. **Framework inventory was thorough** — 7 frameworks, 21 pairs analyzed
4. **Incremental migration path** — Build adapters one by one

## What Nexys Missed (and K2-Backbone Adds)

1. **K2.6 integration** — The market shifted; K2.6 is now the decomposition standard
2. **Production code** — Analysis without execution doesn't ship
3. **Cost optimization** — Per-subtask model assignment beats fixed tiers
4. **AutoMon bridge** — Existing systems need migration path, not replacement
5. **Memory compression** — Obliviarch's 500x is a differentiator

---

## Migration Path: Nexys → K2-Backbone

**Option A: Archive Nexys, continue K2-Backbone** (Recommended)
- Nexys served its purpose as architecture analysis
- K2-Backbone implements the vision with K2.6 focus
- Add Nexys as a submodule for reference

**Option B: Merge repos**
- Port Nexys's `IAgentService` interfaces into K2-Backbone's `interfaces.py`
- Use Nexys's adapter stubs as starting points
- Keep Nexys's validation tools

**Option C: Backport K2-Backbone into Nexys**
- Rename Nexys → K2-Backbone
- Replace empty adapter stubs with working code
- Add K2.6 decomposition on top

---

## Recommendation

**Archive Nexys. K2-Backbone is the successor.**

Nexys was the blueprint. K2-Backbone is the building. The architecture decisions in Nexys (adapter pattern, unified interfaces, incremental migration) are all preserved and extended in K2-Backbone.

The key additions in K2-Backbone:
- **K2.6 decomposition** — The new market reality
- **Working adapters** — 4 implemented vs 7 stubs
- **Unified cost tracking** — AutoMon + per-subtask
- **Production CLI** — `k2 run` ships today

---

## Code Comparison

### Nexys: Adapter Stub (Empty)
```python
# unified_platform/adapters/necroswarm_adapter.py
class NecroSwarmAdapter(IAgentService):
    """Adapter for NecroSwarm workforce framework"""
    
    async def create_agent(self, config: AgentConfig) -> Agent:
        pass  # Not implemented
    
    async def dispatch_task(self, agent_id: str, task: Task) -> TaskResult:
        pass  # Not implemented
```

### K2-Backbone: Working Router
```python
# src/router/necroswarm_router.py
class NecroSwarmRouter:
    """Routes TaskSpec subtasks to council members via Borda voting"""
    
    def route(self, task_spec: dict) -> dict:
        for subtask in task_spec["subtasks"]:
            candidates = self._get_candidates(subtask["type"])
            scores = self._score_borda(subtask, candidates)
            winner = max(scores, key=scores.get)
            subtask["assigned_model"] = winner
        return task_spec
```

---

## Next Steps

1. **Archive Nexys** — Add deprecation notice pointing to K2-Backbone
2. **Port remaining adapters** — Namespace, Memory Evolution, Deterministic Retrieval
3. **Add service registry** — Nexys's `service_registry.py` design
4. **Add health monitoring** — Nexys's `adapter_manager.py` design

**Nexys was the question. K2-Backbone is the answer.**
