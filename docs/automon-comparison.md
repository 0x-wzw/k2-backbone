# K2-Backbone vs. AutoMon-Time-Minimal

## Quick Summary

| | AutoMon-Time-Minimal | K2-Backbone |
|---|---|---|
| **Purpose** | Minimal self-healing system for 98% automation | Production-grade K2.6 integration for your agentic stack |
| **Philosophy** | Radical simplification (15 skills → 5) | Strategic convergence (7 frameworks → 1 backbone) |
| **Cost strategy** | Tier routing (T1/T2/T3) with 45% savings | 10-D Council voting with 70/30 routing + budget fallback |
| **Orchestration** | Priority queue + chat-native operations | K2.6 decomposition → dual-phase execution |
| **Memory** | Queue-driven episodic indexing | Obliviarch 500x compression (episodic → semantic → archetypal) |
| **Federation** | Cross-repo webhooks | VoidTether mesh (A2A, MCP, Hermes, OpenClaw, LangGraph, CrewAI) |
| **Recovery** | T1→T2→T3→T4 failover chain | Council retry + circuit breakers |
| **Status** | ✅ Production (98% automation) | 🟡 MVP (decomposer + router + executor scaffolded) |

---

## Architecture Comparison

### AutoMon-Time-Minimal

```
User Input
    │
    ▼
┌─────────────────────┐
│ Priority Queue Engine│
│ (P0-P4 classification)│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐     ┌──────────────┐
│ Chat Interface      │────▶│ CostRouter   │
│ (October + Z)       │     │ (T1/T2/T3)   │
└─────────────────────┘     └──────┬───────┘
                                   │
                          ┌────────┴────────┐
                          │ Self-Healing    │
                          │ Infrastructure  │
                          └─────────────────┘
```

**5 core skills:**
1. Core Orchestrator (single routing point)
2. Cost Router (tier-based, 45% savings)
3. Security Scanner (credential validation)
4. Memory Manager (queue-driven indexing)
5. System Monitor (self-healing)

### K2-Backbone

```
User Task
    │
    ▼
┌─────────────────────┐
│ K2Decomposer        │
│ (K2.6 JSON prompt)   │
└──────┬──────────────┘
       │ TaskSpec JSON
       ▼
┌─────────────────────┐
│ NecroSwarmRouter     │
│ (10-D Council vote)  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ NeuroSwarmExecutor   │
│ (GBrain + NecroSwarm)│
└──────┬──────────────┘
       │ Results + Traces
       ▼
┌─────────────────────┐     ┌──────────────┐
│ ObliviarchMemory    │────▶│ VoidTether   │
│ (500x compression)  │     │ (cross-mesh) │
└─────────────────────┘     └──────────────┘
```

**6 adapters + 6 framework submodules:**
1. Decomposer (K2.6 adapter)
2. Router (10-D Council)
3. Executor (dual-phase)
4. Memory (Obliviarch)
5. Federation (VoidTether)
6. Retrieval (Deterministic)

---

## Cost Router Comparison

### AutoMon: OASIS v2 CostRouter

| Tier | Models | Cost/1M | Context | Use For |
|---|---|---|---|---|
| T1 | kimi-k2.5, mistral-large-3 | $3.00 | 262K | Complex architecture, deep research |
| T2 | deepseek-v3.2, glm-5 | $1.50 | 128K | Research synthesis, code review |
| T3 | phi3, glm-5 | $0.50 | 64K | Filtering, formatting, classification |
| T4 | (fallback) | $0.10 | 32K | Emergency only |

**Routing:** Task type → tier → cheapest model in tier
**Savings:** 45% via tier downgrade for simple tasks
**Integration:** `sessionsSpawnWithRouting(task, { requestedTier: 'T3' })`

### K2-Backbone: NecroSwarmRouter

| Dimension | Model | Vote Power | Cost/1K | Specialization |
|---|---|---|---|---|
| Kimi | K2.6 | 3 | $3.00 | Coordination, analysis, optimization |
| Claude | Opus 4 | 3 | $3.75 | Code generation, writing, architecture |
| DeepSeek | V3.2 | 2 | $0.50 | Research, data processing |
| GLM | GLM-5 | 2 | $0.30 | Visualization, synthesis |
| Qwen | 2.5 | 1 | $0.10 | Testing, execution, fallback |

**Routing:** Subtask type → Borda vote (capability × tier × 1/cost) → winner
**Strategies:** `borda`, `cost_first`, `quality_first`
**Savings:** 70/30 routing (70% of tasks to cheap models, 30% to premium)
**Budget fallback:** Auto-downgrades if running over budget

---

## What AutoMon Does Better

1. **Production maturity** — Already achieving 98% automation, battle-tested
2. **Simplicity** — 5 skills vs. 6 adapters + 6 submodules
3. **Self-healing** — Active config repair, model failover, memory rebuild
4. **Queue-driven** — No calendar triggers, no human-time anchors
5. **Priority classification** — P0-P4 automatic routing

## What K2-Backbone Does Better

1. **K2.6 integration** — Leverages Moonshot's RL-trained decomposition
2. **Model heterogeneity** — 5+ providers, not locked to one ecosystem
3. **Memory compression** — Obliviarch 500x vs. episodic indexing
4. **Cross-platform** — VoidTether bridges A2A, MCP, Hermes, LangGraph, CrewAI
5. **Auditability** — Every council vote logged, every trace compressible
6. **Cost control** — Per-subtask budget allocation with fallback

---

## Integration Path: Merge, Not Replace

**The move:** Make K2-Backbone the **skill #6** in AutoMon's minimal sufficient system.

```
AutoMon-Time-Minimal (5 skills)
    │
    ├── Core Orchestrator
    ├── Cost Router (OASIS v2)
    ├── Security Scanner
    ├── Memory Manager
    ├── System Monitor
    │
    └── NEW: K2-Backbone Bridge (skill #6)
            │
            ├── Decomposer (K2.6 for complex tasks)
            ├── Router (10-D Council for model diversity)
            ├── Executor (NeuroSwarm for dual-phase)
            ├── Memory (Obliviarch for compression)
            └── Federation (VoidTether for cross-platform)
```

**When to use AutoMon's CostRouter:** Simple tasks, P2-P4 priority, need speed
**When to use K2-Backbone:** Complex tasks, need decomposition, cross-platform, audit trail

---

## Code Comparison: Router Implementation

### AutoMon: OASIS v2 (TypeScript)
```typescript
// tier-based routing with fixed rules
function routeTask(task: string, requestedTier?: Tier): ModelConfig {
    const tier = requestedTier || classifyTask(task);
    const models = TIER_CONFIGS[tier].models;
    return selectCheapest(models);
}
```

### K2-Backbone: NecroSwarmRouter (Python)
```python
# Borda voting with composite scoring
def route_task(subtask: dict) -> RoutingDecision:
    candidates = get_candidates(subtask["type"])
    scores = {}
    for cid in candidates:
        capability = CAPABILITY_MATRIX[cid][task_family]
        cost_score = 1.0 / COST_PER_1K[cid]
        composite = capability * tier_weight * cost_score
        scores[cid] = composite
    winner = max(scores, key=scores.get)
    return RoutingDecision(...)
```

---

## Recommendation

**Don't replace AutoMon. Augment it.**

AutoMon is your operational backbone — minimal, self-healing, 98% automated.
K2-Backbone is your strategic capability layer — for the 2% of tasks that need K2.6 decomposition, cross-platform federation, or institutional memory.

**Immediate action:**
1. Keep AutoMon running as-is
2. Add K2-Backbone as a submodule to AutoMon
3. Wire AutoMon's Core Orchestrator to call K2-Backbone for tasks classified as "complex" (P1 with >5 subtasks)
4. Let AutoMon handle simple tasks (P2-P4), K2-Backbone handle complex ones (P0-P1 with decomposition)

**Result:** 98% automation for simple tasks + K2.6-powered decomposition for complex ones, all under AutoMon's queue-driven, self-healing umbrella.
