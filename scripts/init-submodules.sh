#!/usr/bin/env bash
# init-submodules.sh
# Initialize all framework submodules for k2-backbone

set -e

echo "🔗 K2-BACKBONE: Initializing framework submodules"
echo ""

REPOS=(
    "necroswarm:https://github.com/0x-wzw/necroswarm.git"
    "neuroswarm:https://github.com/0x-wzw/neuroswarm.git"
    "obliviarch:https://github.com/0x-wzw/obliviarch.git"
    "voidtether:https://github.com/0x-wzw/voidtether.git"
    "memory-evolution:https://github.com/0x-wzw/openclaw-memory-evolution.git"
    "deterministic-retrieval:https://github.com/0x-wzw/openclaw-deterministic-retrieval.git"
)

mkdir -p frameworks

for entry in "${REPOS[@]}"; do
    name="${entry%%:*}"
    url="${entry#*:}"
    path="frameworks/$name"

    if [ -d "$path/.git" ]; then
        echo "  ✅ $name already cloned"
        (cd "$path" && git pull --ff-only 2>/dev/null || echo "     (could not update)")
    else
        echo "  📦 Cloning $name..."
        git submodule add "$url" "$path" 2>/dev/null || \
            git clone --depth 1 "$url" "$path"
    fi
done

echo ""
echo "✅ All frameworks ready in frameworks/"
echo ""
echo "Next steps:"
echo "  1. pip install -e .[dev]"
echo "  2. export MOONSHOT_API_KEY=sk-..."
echo "  3. python -m k2_backbone.decomposer.k2_decomposer 'Your task here'"
