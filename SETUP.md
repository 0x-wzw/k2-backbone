# Setup Guide

## Create the GitHub Repo

Since the GitHub PAT is a placeholder, you have two options:

### Option 1: Create via GitHub Web UI (Fastest)

1. Go to https://github.com/new
2. Owner: `0x-wzw`
3. Repository name: `k2-backbone`
4. Description: `Kimi K2.6's Production Backbone — decomposition, routing, execution, compression, federation`
5. Visibility: **Public**
6. ✅ Add README? **NO** (we already have one)
7. ✅ Add .gitignore? **NO**
8. ✅ Choose a license? **NO**
9. Click **Create repository**

Then push:
```bash
cd /home/ubuntu/.openclaw/workspace/k2-backbone
git remote set-url origin https://github.com/0x-wzw/k2-backbone.git
git push -u origin main
```

### Option 2: Create via GitHub CLI

```bash
# Install gh if needed
# https://cli.github.com/

gh auth login
cd /home/ubuntu/.openclaw/workspace/k2-backbone
gh repo create 0x-wzw/k2-backbone --public --source=. --push \
  --description "Kimi K2.6's Production Backbone"
```

### Option 3: Create via API with Valid Token

```bash
export GITHUB_PAT="ghp_your_real_token_here"
curl -X POST -H "Authorization: token $GITHUB_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "k2-backbone",
    "description": "Kimi K2.6 production backbone",
    "private": false,
    "auto_init": false
  }' \
  https://api.github.com/user/repos
```

Then push as in Option 1.

---

## After Repo Creation

### Initialize Framework Submodules

```bash
cd /home/ubuntu/.openclaw/workspace/k2-backbone
./scripts/init-submodules.sh
```

This clones all 6 frameworks into `frameworks/`:
- `necroswarm` — 10-D Council, cost routing
- `neuroswarm` — Dual-phase brain + execution
- `obliviarch` — 500x memory compression
- `voidtether` — Cross-framework mesh
- `memory-evolution` — Self-improving storage
- `deterministic-retrieval` — Exact-match retrieval

### Install Dependencies

```bash
# Python
pip install -e ".[dev]"

# TypeScript
npm install
```

### Set API Keys

```bash
export MOONSHOT_API_KEY="sk-..."        # Required for K2.6 decomposition
export OPENAI_API_KEY="sk-..."          # Optional — for council diversity
export ANTHROPIC_API_KEY="sk-ant-..."   # Optional — for council diversity
```

### Test the Decomposer

```bash
python -m k2_backbone.decomposer.k2_decomposer \
  "Build a REST API for a prediction market with 5 endpoints"
```

---

## Next Development Priorities

| Priority | Task | Owner |
|---|---|---|
| P0 | NecroSwarm router adapter | You |
| P0 | NeuroSwarm executor adapter | You |
| P1 | Obliviarch memory pipeline | You |
| P1 | VoidTether federation bridge | You |
| P1 | RuFlo plugin `ruflo-k2-backbone` | You |
| P2 | OpenClaw skill integration | You |
| P2 | Deterministic Retrieval backend | You |
| P2 | Memory Evolution hooks | You |
| P3 | Example projects (code-refactor, research-synthesis) | Community |
| P3 | E2E test suite | You |

---

## Architecture Decision Records

See `docs/architecture.md` for full architecture.

Key decisions:
1. **Prompt-for-Decomposition** — K2.6 emits JSON via `response_format`, no attempt to intercept internal swarm
2. **Two-Stage Execution** — Decomposition (K2.6) → Execution (Your stack) → Synthesis (optional K2.6)
3. **Model Independence** — K2.6 is one of many models in the 10-D Council
4. **Compression as Understanding** — All traces go through Obliviarch before long-term storage

---

*Questions? Open an issue on the repo.*
