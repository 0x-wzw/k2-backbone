# ruflo-k2-backbone

> **Kimi K2.6's Production Backbone as a RuFlo Skill**

## What It Is

A RuFlo plugin that deploys the full K2-Backbone pipeline:

```
K2.6 Decomposition → 10-D Council Routing → NeuroSwarm Execution → Obliviarch Compression
```

## Installation

```bash
# From ruflo plugin marketplace (when published)
ruflo plugin install k2-backbone

# Or from local source
cd plugins/ruflo-k2-backbone
npm install
npm run build
ruflo plugin install ./
```

## Configuration

Set your Moonshot API key:

```bash
export MOONSHOT_API_KEY="sk-..."
```

Or configure via ruflo:

```bash
ruflo config set k2-backbone.moonshotApiKey "sk-..."
ruflo config set k2-backbone.enableNeuroswarm true
ruflo config set k2-backbone.enableObliviarch true
```

## Commands

### Full Pipeline

```bash
# Run complete pipeline: decompose → route → execute → compress
ruflo k2-run "Build a REST API for a prediction market with 5 endpoints"

# Output:
# {
#   "taskId": "k2_...",
#   "status": "completed",
#   "pipeline": {
#     "decomposition": { "subtasks": 5 },
#     "routing": { "models": ["kimi-k2.6", "claude-opus-4"], "cost": 2.45 },
#     "execution": { "completed": 5, "failed": 0 },
#     "compression": { "schemaId": "obliviarch_..." }
#   }
# }
```

### Individual Steps

```bash
# Step 1: Decompose with K2.6
ruflo k2-decompose "Refactor Java matching engine for 185% throughput"

# Step 2: Route through 10-D Council
ruflo k2-route --spec task_123

# Step 3: Execute with NeuroSwarm
ruflo k2-execute --spec task_123

# Step 4: Compress via Obliviarch
ruflo k2-compress --trace task_123
```

### Query Compressed Memories

```bash
# Search across all compression levels
ruflo k2-query "java optimization patterns"

# Output:
# {
#   "query": "java optimization patterns",
#   "results": [
#     { "taskId": "k2_...", "schemaId": "...", "score": 0.95, "level": "episodic" },
#     { "taskId": "k2_...", "schemaId": "...", "score": 0.87, "level": "semantic" }
#   ]
# }
```

### Cost Tracking

```bash
# Get unified cost report (AutoMon + K2-Backbone)
ruflo k2-cost

# Output:
# {
#   "totalExecutions": 42,
#   "naiveEstimate": 126.00,
#   "actualCost": 45.50,
#   "savingsPercent": 63.9,
#   "autoMonStyle": {
#     "t1Tasks": 0,
#     "t2Tasks": 12,
#     "t3Tasks": 30,
#     "estimatedSavings": 63.9
#   }
# }
```

### Pipeline Status

```bash
# Check all component health
ruflo k2-status

# Output:
# {
#   "plugin": "k2-backbone",
#   "neuroswarm": "enabled",
#   "obliviarch": "enabled",
#   "components": {
#     "decomposer": "✅ K2.6 adapter",
#     "router": "✅ 10-D Council",
#     "executor": "✅ NeuroSwarm",
#     "memory": "✅ Obliviarch",
#     "bridge": "✅ AutoMon"
#   }
# }
```

## Architecture

```
User Command (ruflo k2-*)
    │
    ▼
┌─────────────────────────────────────┐
│  K2BackbonePlugin                     │
│  (RuFlo Plugin Interface)             │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Python Adapters (via subprocess)     │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ │
│  │K2Decomp │ │NecroSwrm│ │NeuroSwm│ │
│  └────┬────┘ └────┬────┘ └───┬────┘ │
│       │           │          │      │
│  ┌────┴───────────┴──────────┴────┐ │
│  │        Obliviarch              │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Integration with Other RuFlo Plugins

| Plugin | Integration Point |
|---|---|
| `ruflo-neuroswarm` | Executor dual-phase enhancement |
| `ruflo-obliviarch` | Memory compression backend |
| `ruflo-openclaw-bridge` | OpenClaw session spawning |
| `ruflo-cost-tracker` | Unified cost aggregation |
| `ruflo-federation` | Cross-platform result bridging |

## Development

```bash
# Build
npm run build

# Test
npm test

# Lint
npx eslint src/**/*.ts
```

## License

MIT — same as K2-Backbone
