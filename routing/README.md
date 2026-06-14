# Model Routing Table

Single source of truth for K2 Swarm model routing.

**10-D Council assignments, cost tables, capability matrices, and fallback chains.**

All model changes go here. Downstream repos (`k2-backbone`, `neuroswarm`, Hermes Agent skill) import from this package.

## Quick Start

```python
from model_routing_table import DIMENSION_MAP, DIMENSION_FALLBACK, MODEL_COST_USD

# Current best-in-class models
print(DIMENSION_MAP["D3_code"])  # → glm-5.1:cloud

# Fallback chain for coding
print(DIMENSION_FALLBACK["D3_code"])  # → ["qwen3.5:122b:cloud", "deepseek-v4-flash:cloud"]

# Cost per 1K output tokens
print(MODEL_COST_USD["kimi-k2.6:cloud"])  # → 3.00
```

## Install

```bash
pip install git+https://github.com/0x-wzw/model-routing-table.git
```

## Updating Models

Only `model_routing_table/table.py` needs editing to update the 10-D council. All downstream repos pick up changes automatically on next pip install / git pull.

## Model Scanner

Weekly cron at `k2-backbone/scripts/model-scanner.py` scans Ollama Cloud for new models and auto-updates this table when successors are detected.
---

## Related Repositories

| Repository | Purpose |
|------------|---------|
| [**agentic-workforce**](https://github.com/0x-wzw/agentic-workforce) | Multi-agent orchestration protocols — message envelopes, boundary enforcement, convergence detection, resolver system |
| [k2-backbone](https://github.com/0x-wzw/k2-backbone) | Task decomposition and 10-D Council routing |
| [neuroswarm](https://github.com/0x-wzw/neuroswarm) | Parallel swarm execution engine |
