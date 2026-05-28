# Architecture

## Design Principles

1. **K2.6 is a decomposer, not an executor.** Its swarm intelligence is RL-trained for task breakdown. Our stack is engineered for cost-optimized, auditable execution.

2. **Every decision is logged.** The 10-D Council votes on every model assignment. Every trace is compressed by Obliviarch. Every federation handshake is recorded.

3. **Model independence is non-negotiable.** K2.6 is one of many models in the mesh. The swarm survives if any single provider fails.

4. **Compression is understanding.** Raw logs are hoarding. Obliviarch's 500x reduction with better recall is the memory strategy.

---

## Component Interactions

### Decomposition Flow

```
User Task
    │
    ▼
┌─────────────────────────────┐
│  K2Decomposer               │
│  • Prompts K2.6 for JSON    │
│  • Validates against schema │
│  • Maps to TaskSpec         │
└──────────────┬──────────────┘
               │ TaskSpec JSON
               ▼
┌─────────────────────────────┐
│  TaskSpecValidator          │
│  • JSON Schema validation   │
│  • Dependency cycle check   │
│  • Budget sanity check      │
└──────────────┬──────────────┘
               │ Validated TaskSpec
               ▼
┌─────────────────────────────┐
│  NecroSwarmRouter           │
│  • Loads 10-D Council       │
│  • Runs Borda voting        │
│  • Assigns models           │
└──────────────┬──────────────┘
               │ Routed subtasks
               ▼
┌─────────────────────────────┐
│  NeuroSwarmExecutor         │
│  • GBrain validates plan    │
│  • Council executes           │
│  • Results collected          │
└──────────────┬──────────────┘
               │ Results + Traces
               ▼
┌─────────────────────────────┐
│  ObliviarchMemory           │
│  • Compress traces          │
│  • Extract schemas          │
│  • Update archetypes        │
└──────────────┬──────────────┘
               │ Compressed schemas
               ▼
┌─────────────────────────────┐
│  VoidTetherFederation       │
│  • Bridge to other systems  │
│  • Sync memory shards       │
│  • Human-in-the-loop gates  │
└─────────────────────────────┘
```

### Federation Flow

```
K2.6 Swarm (on Kimi.com) ──► VoidTether Mesh ──► Your NecroSwarm
        │                           │                    │
        │                           ▼                    │
        │                    ┌──────────────┐            │
        │                    │  Tether Hub  │            │
        │                    │  (FastAPI)   │            │
        │                    └──────┬───────┘            │
        │                           │                    │
        ▼                           ▼                    ▼
   [Black Box]              [Protocol Translation]  [Your Stack]
   Subtask list             A2A ↔ MCP ↔ Hermes     Audit + Execute
   (via prompt)             ↔ OpenClaw ↔ Swarm     + Compress
```

---

## Data Flow

### TaskSpec Lifecycle

1. **Creation** — K2Decomposer produces raw TaskSpec
2. **Validation** — Schema + dependency + budget checks
3. **Enrichment** — GBrain adds context, RESOLVER maps skills
4. **Routing** — 10-D Council assigns models per subtask
5. **Execution** — NeuroSwarm dual-phase (plan → execute)
6. **Validation** — Success criteria checked per subtask
7. **Compression** — Obliviarch ingests traces
8. **Retrieval** — Deterministic Retrieval serves exact-match queries
9. **Evolution** — Memory Evolution updates access patterns

---

## Integration Patterns Detail

### Pattern A: K2.6 as Decomposer

**Use when:**
- Task complexity > 5 subtasks
- Cost sensitivity is high
- Audit trail is required
- Heterogeneous model routing is beneficial

**Flow:**
```python
# 1. Decompose
spec = k2_decomposer.decompose(task)

# 2. Route
routed = necroswarm.route(spec)

# 3. Execute
results = neuroswarm.execute(routed)

# 4. Synthesize (optional: back to K2.6)
synthesis = k2_client.synthesize(results)

# 5. Remember
schema_id = obliviarch.ingest(task, results, synthesis)
```

### Pattern B: K2.6 as Council Seat

**Use when:**
- Task decomposition quality is critical
- K2.6's RL coordination adds unique value
- Council diversity is preferred over single-model

**Flow:**
```python
# Add K2.6 as dimension 11
council = TenDCouncil()
council.add_member(K2Seat(vote_power=1.0, specialization="coordination"))

# Run vote — K2.6 participates in model selection
winner = council.vote(proposals, task_context)
```

### Pattern C: K2.6 Output → Memory

**Use when:**
- K2.6 runs are frequent
- Building institutional knowledge
- Repeated task types

**Flow:**
```python
# K2.6 runs (user does this on kimi.com)
raw_output = user_provides_output()

# Ingest
compressor = ObliviarchCompressor()
schema = compressor.ingest(
    source="k2_6_swarm",
    task=task_description,
    raw_output=raw_output
)

# Now retrievable
dna = deterministic_retrieval.query("java matching engine optimization")
# → Returns archetype: PERFORMANCE-OPTIMIZATION-JAVA
```

---

## Failure Modes

| Failure | Detection | Recovery |
|---|---|---|
| K2.6 decomposition invalid | Schema validator | Retry with stricter prompt |
| Council hung vote | Timeout + quorum check | Fallback to cost router |
| Subtask failure | Success criteria miss | Re-queue with different model |
| Obliviarch compression error | Size check | Fallback to raw storage |
| VoidTether bridge down | Health check | Queue for retry, alert human |
| Budget exceeded | Real-time tracker | Halt + report partial results |

---

## Security

- API keys: Per-provider rotation, never committed
- Task isolation: Each subtask runs in sandboxed context
- Memory encryption: At-rest for episodic, not needed for archetypal (already abstract)
- Audit logs: Append-only, signed
- Human gates: Configurable approval points in federation

---

## Performance Targets

| Metric | Target |
|---|---|
| Decomposition latency | < 5s for tasks < 20 subtasks |
| Council voting | < 2s parallel |
| Subtask routing | < 100ms |
| Obliviarch compression | < 1s per trace |
| Deterministic retrieval | < 50ms p99 |
| End-to-end (simple task) | < 30s |
| End-to-end (complex task) | < 10 min |

---

*Next: See `docs/decomposer.md` for K2.6 integration details.*
