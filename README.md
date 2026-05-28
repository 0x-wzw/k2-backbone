# ⚡ K2-BACKBONE

> **Kimi K2.6's Production Backbone**
>
> K2.6 decomposes. We execute, audit, compress, and federate.

---

## What This Is

K2-BACKBONE is the convergence layer for the 0x-wzw agentic stack. It takes K2.6's task decomposition intelligence and routes it through a production-grade swarm infrastructure:

- **NecroSwarm** — Cost-optimized workforce (10-D Council, 70/30 routing)
- **NeuroSwarm** — Dual-phase brain + execution (GBrain + Council)
- **Obliviarch** — 500x memory compression (episodic → semantic → archetypal)
- **VoidTether** — Cross-framework interoperability mesh (A2A, MCP, Hermes, OpenClaw, LangGraph, CrewAI)
- **Deterministic Retrieval** — Exact-match memory with guaranteed precision
- **Memory Evolution** — Self-improving storage via access tracking

---

## The Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER TASK                                    │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│  DECOMPOSER  (Kimi K2.6 via prompt-for-decomposition)              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Input: Natural language task                              │   │
│  │  Output: Structured JSON task tree (TaskSpec schema)       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ TaskSpec JSON
┌───────────────────────────▼─────────────────────────────────────────┐
│  ROUTER  (NecroSwarm 10-D Council)                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Borda voting → model selection per subtask               │   │
│  │  Cost routing: cheap models for shallow, K2.6 for deep   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Routed subtasks
┌───────────────────────────▼─────────────────────────────────────────┐
│  EXECUTOR  (NeuroSwarm Dual-Phase)                                  │
│  ┌──────────────┐        ┌─────────────────────────────────────┐   │
│  │  GBrain       │        │  NecroSwarm Council                │   │
│  │  (WHAT)       │───────▶│  (HOW)                              │   │
│  │  • RESOLVER   │ feed   │  • Execute subtask                  │   │
│  │  • Signal Det │───────▶│  • Consensus validation             │   │
│  └──────────────┘        └─────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Results + Traces
┌───────────────────────────▼─────────────────────────────────────────┐
│  MEMORY  (Obliviarch + Deterministic Retrieval)                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Level 1: Episodic (48h raw traces)                        │   │
│  │  Level 2: Semantic (patterns, ~20x compression)            │   │
│  │  Level 3: Archetypal (behavioral DNA, ~500x compression)   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ Compressed schemas
┌───────────────────────────▼─────────────────────────────────────────┐
│  FEDERATION  (VoidTether Mesh)                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│  │ A2A  │ │ MCP  │ │Hermes│ │OpenClaw│ │Swarm │ │LangGraph│       │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Install

```bash
npm install -g k2-backbone
# or
pip install k2-backbone
```

### Decompose with K2.6, Execute with Your Stack

```bash
# 1. Set your Moonshot API key
export MOONSHOT_API_KEY="sk-..."

# 2. Decompose a task
k2 decompose "Refactor a Java matching engine for 185% throughput gain"
# → Outputs TaskSpec JSON to stdout

# 3. Execute via your swarm
k2 execute --spec task_spec.json --router necroswarm --memory obliviarch

# 4. Compress and store results
k2 ingest --output ./results/ --compress
```

### Programmatic API

```python
from k2_backbone import K2Backbone

backbone = K2Backbone(
    moonshot_key="sk-...",
    router="necroswarm",
    memory="obliviarch",
    federation="voidtether"
)

# Single call: decompose → route → execute → compress
result = backbone.run("Build a marketing site with 12 pages")

# Access structured outputs
print(result.deliverables)      # Files, code, documents
print(result.execution_log)     # Full audit trail
print(result.compressed_memory) # Obliviarch schema ID
```

---

## Repo Structure

```
k2-backbone/
├── README.md
├── LICENSE
├── package.json / pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── decomposer.md
│   ├── router.md
│   ├── executor.md
│   ├── memory.md
│   └── federation.md
├── src/
│   ├── decomposer/          # K2.6 decomposition adapter
│   │   ├── k2_client.py|ts
│   │   ├── prompt_templates/
│   │   └── task_spec_mapper.py|ts
│   ├── router/              # NecroSwarm 10-D Council integration
│   │   ├── council_client.py|ts
│   │   ├── cost_router.py|ts
│   │   └── voting/
│   ├── executor/              # NeuroSwarm dual-phase execution
│   │   ├── gbrain.py|ts
│   │   ├── dual_phase.py|ts
│   │   └── sandbox/
│   ├── memory/                # Obliviarch + Deterministic Retrieval
│   │   ├── obliviarch_client.py|ts
│   │   ├── compressor.py|ts
│   │   └── retrieval.py|ts
│   ├── federation/            # VoidTether mesh bridge
│   │   ├── voidtether_client.py|ts
│   │   ├── adapters/
│   │   └── mesh_manager.py|ts
│   └── core/                  # Shared types, schemas, config
│       ├── task_spec.schema.json
│       ├── interfaces.py|ts
│       └── config.py|ts
├── plugins/                   # Framework-specific adapters
│   ├── ruflo-k2-backbone/     # RuFlo plugin
│   ├── openclaw-k2-backbone/  # OpenClaw skill
│   └── claude-code-k2-backbone/ # Claude Code integration
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── examples/
    ├── code-refactor/         # K2.6 + NecroSwarm code optimization
    ├── research-synthesis/    # K2.6 + NeuroSwarm literature review
    └── multi-platform/        # K2.6 + VoidTether federation demo
```

---

## Integration Patterns

### Pattern A: K2.6 as Decomposer (Recommended)

K2.6 decomposes → Your swarm executes → K2.6 synthesizes

**Best for:** Complex tasks with heterogeneous subtasks, cost-sensitive workloads, audit requirements.

### Pattern B: K2.6 as Council Seat

Add `kimi-k2.6` as the 11th dimension in your 10-D Council.

**Best for:** Tasks where K2.6's coordination RL adds unique value.

### Pattern C: K2.6 Output → Long-Term Memory

K2.6 runs → Obliviarch compresses → Deterministic Retrieval serves

**Best for:** Repeated task types, building institutional knowledge.

---

## Cost Model

| Layer | Cost Driver | Optimization |
|---|---|---|
| Decomposition | K2.6 API call | Once per task, ~$0.50-2 |
| Routing | 10-D Council vote | Parallel voting, ~$0.10 |
| Execution | Subtask models | 70/30 routing (cheap models for 70% of tasks) |
| Memory | Obliviarch compression | 500x reduction = 500x cheaper storage |
| Federation | Protocol translation | Fixed per-bridge overhead |

**Typical savings vs. pure K2.6 swarm:** 60-80% for tasks with many shallow subtasks.

---

## Submodules (Your Existing Repos)

This repo uses Git submodules to track your frameworks:

```bash
git submodule add https://github.com/0x-wzw/necroswarm.git frameworks/necroswarm
git submodule add https://github.com/0x-wzw/neuroswarm.git frameworks/neuroswarm
git submodule add https://github.com/0x-wzw/obliviarch.git frameworks/obliviarch
git submodule add https://github.com/0x-wzw/voidtether.git frameworks/voidtether
git submodule add https://github.com/0x-wzw/openclaw-memory-evolution.git frameworks/memory-evolution
git submodule add https://github.com/0x-wzw/openclaw-deterministic-retrieval.git frameworks/deterministic-retrieval
```

---

## Status

| Component | Status | Submodule |
|---|---|---|
| Decomposer (K2.6 adapter) | 🟡 In Progress | — |
| Router (NecroSwarm) | ✅ Ready | `frameworks/necroswarm` |
| Executor (NeuroSwarm) | ✅ Ready | `frameworks/neuroswarm` |
| Memory (Obliviarch) | ✅ Ready | `frameworks/obliviarch` |
| Federation (VoidTether) | 🟡 v0.2.0 Web UI | `frameworks/voidtether` |
| Deterministic Retrieval | ✅ Ready | `frameworks/deterministic-retrieval` |
| Memory Evolution | ✅ Ready | `frameworks/memory-evolution` |
| RuFlo Plugin | 🟡 Scaffolded | `plugins/ruflo-k2-backbone` |
| OpenClaw Skill | ⚪ Planned | `plugins/openclaw-k2-backbone` |

---

## License

MIT — same as all 0x-wzw frameworks.

---

*Built by the Undead Collective. K2.6 feeds the swarm. The swarm remembers.*
