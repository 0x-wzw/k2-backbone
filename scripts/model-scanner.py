#!/usr/bin/env python3
"""
Model Scanner — Ollama Cloud Best-in-Class Tracker

Scans ollama.com/search?c=cloud for new/better cloud models.
Compares with current dimension_map.py and auto-updates only
when a clearly superior replacement is found.

Strategy: preserve human-curated assignments by default.
Auto-update only when:
  - A model in the same SLOT (e.g. Qwen 3.5 → Qwen 4.0) gets a major version bump
  - A new model for the same dimension beats the current on pulls (2x+), recency (< 30d)
  - A model family releases a larger/faster variant that clearly outclasses the current

Designed to run as a daily cron job. Auto-commits to GitHub only with actual changes.
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

# ── Paths ──────────────────────────────────────────────────────────────

K2_ROOT = Path(__file__).resolve().parent.parent
DIMENSION_MAP_PATH = K2_ROOT.parent / "model-routing-table" / "model_routing_table" / "table.py"
STATE_FILE = K2_ROOT / ".model-scanner-state.json"
LOG_FILE = Path.home() / ".k2-model-scanner.log"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
SEARCH_URL = "https://ollama.com/search?c=cloud&page={page}"
MODEL_URL = "https://ollama.com/library/{slug}"


# ── Current gold-standard assignments (human-curated) ─────────────────

# These are the known best-in-class as of the last manual audit.
# The scanner preserves these unless a clearly better model appears.
CURRENT_MAP = {
    "D1_synthesis":    "kimi-k2.6:cloud",
    "D2_deep_reason":  "qwen3.5:122b:cloud",
    "D3_code":         "glm-5.1:cloud",
    "D4_vision":       "qwen3-vl:235b:cloud",
    "D5_strategy":     "qwen3.5:397b:cloud",
    "D6_analysis":     "gemma4:26b:cloud",
    "D7_general":      "deepseek-v4-flash:cloud",
    "D8_verification": "nemotron-3-ultra:cloud",
    "D9_research":     "minimax-m3:cloud",
    "D10_think":       "deepseek-v4-pro:cloud",
}

CURRENT_FALLBACK = {
    "D1_synthesis":    ["deepseek-v4-pro:cloud", "glm-5.1:cloud"],
    "D2_deep_reason":  ["kimi-k2.6:cloud", "glm-5.1:cloud"],
    "D3_code":         ["qwen3.5:122b:cloud", "deepseek-v4-flash:cloud"],
    "D4_vision":       [],
    "D5_strategy":     ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud"],
    "D6_analysis":     ["glm-5.1:cloud", "deepseek-v4-flash:cloud"],
    "D7_general":      ["qwen3.5:122b:cloud", "minimax-m3:cloud"],
    "D8_verification": ["deepseek-v4-pro:cloud", "gemma4:26b:cloud"],
    "D9_research":     ["kimi-k2.6:cloud", "deepseek-v4-pro:cloud"],
    "D10_think":       ["kimi-k2.6:cloud", "qwen3.5:397b:cloud"],
}

DESCRIPTIONS = {
    "D1_synthesis":    "Converge perspectives into coherent whole",
    "D2_deep_reason":  "Analyze deeply, find hidden implications",
    "D3_code":         "Generate, review, verify code",
    "D4_vision":       "See and interpret visual information",
    "D5_strategy":     "Plan strategically, weigh trade-offs",
    "D6_analysis":     "Break down complex systems quantitatively",
    "D7_general":      "Fast general-purpose reasoning",
    "D8_verification": "Fact-check, accuracy gate",
    "D9_research":     "Gather and synthesize information",
    "D10_think":       "Slow, thorough, second-order reasoning",
}

# ── Upgrade Rules ──────────────────────────────────────────────────────

# Each dimension has rules describing what models belong to it and
# what would constitute an upgrade.
#
# "slugs": model families that belong in this dimension
# "size_variants": for family-based models, the specific size:tag to use
# "upgrade_from": if a new slug appears that's a known successor, flag it

UPGRADE_RULES: dict[str, dict[str, Any]] = {
    "D1_synthesis": {
        "slugs": ["kimi-k2.6", "kimi-k2.5", "kimi"],
        "size_variant": None,  # single variant model
        "upgrade_signal": "kimi-k3",  # future successor
    },
    "D2_deep_reason": {
        "slugs": ["qwen3.5", "qwen3", "deepseek-v4", "deepseek-v3"],
        "size_variant": "122b",
        "upgrade_signal": ("qwen4", "deepseek-v5"),
    },
    "D3_code": {
        "slugs": ["glm-5.1", "glm-5", "glm-6", "qwen3-coder"],
        "size_variant": None,
        "upgrade_signal": ("glm-6", "qwen4-coder"),
        "min_pulls": 500_000,
    },
    "D4_vision": {
        "slugs": ["qwen3-vl", "qwen4-vl", "gemma4"],
        "size_variant": "235b",
        "required_tags": ["vision"],
    },
    "D5_strategy": {
        "slugs": ["qwen3.5", "qwen3", "deepseek-v4", "deepseek-v3"],
        "size_variant": "397b",
        "upgrade_signal": ("qwen4:500b", "qwen4:700b"),
    },
    "D6_analysis": {
        "slugs": ["gemma4", "gemma5", "gemma"],
        "size_variant": "26b",
        "upgrade_signal": ("gemma5", "gemma-5"),
    },
    "D7_general": {
        "slugs": ["deepseek-v4-flash", "deepseek-v5-flash", "deepseek-v4-flash"],
        "upgrade_signal": ("deepseek-v5-flash",),
    },
    "D8_verification": {
        "slugs": ["nemotron-3", "nemotron-4", "nemotron"],
        "size_variant": "ultra",
        "upgrade_signal": ("nemotron-4-ultra",),
    },
    "D9_research": {
        "slugs": ["minimax-m3", "minimax-m4", "minimax"],
        "size_variant": None,
        "upgrade_signal": ("minimax-m4",),
    },
    "D10_think": {
        "slugs": ["deepseek-v4-pro", "deepseek-v5-pro", "deepseek-v4"],
        "upgrade_signal": ("deepseek-v5-pro",),
    },
}


def parse_pulls(s: str) -> int:
    s = s.replace(",", "").strip()
    if s.endswith("M"):
        return int(float(s[:-1]) * 1_000_000)
    if s.endswith("K"):
        return int(float(s[:-1]) * 1_000)
    try:
        return int(float(s))
    except ValueError:
        return 0


def cloud_slug(slug: str) -> str:
    """Map a family slug to its :cloud variant reference."""
    exceptions = {
        "qwen3.5":          "qwen3.5:122b:cloud",
        "qwen3-vl":         "qwen3-vl:235b:cloud",
        "gemma4":           "gemma4:26b:cloud",
        "nemotron-3-ultra": "nemotron-3-ultra:cloud",
        "nemotron-3-super": "nemotron-3-super:cloud",
        "nemotron-3-nano":  "nemotron-3-nano:cloud",
        "minimax-m3":       "minimax-m3:cloud",
        "minimax-m2.7":     "minimax-m2.7:cloud",
        "minimax-m2.5":     "minimax-m2.5:cloud",
        "deepseek-v4-pro":  "deepseek-v4-pro:cloud",
        "deepseek-v4-flash":"deepseek-v4-flash:cloud",
        "glm-5.1":          "glm-5.1:cloud",
        "glm-5":            "glm-5:cloud",
        "kimi-k2.6":        "kimi-k2.6:cloud",
        "kimi-k2.5":        "kimi-k2.5:cloud",
        "gemini-3-flash-preview": "gemini-3-flash-preview:cloud",
        "qwen3-coder-next": "qwen3-coder-next:cloud",
        "gpt-oss":          "gpt-oss:cloud",
        "qwen3.5:122b":     "qwen3.5:122b:cloud",
        "qwen3.5:397b":     "qwen3.5:397b:cloud",
        "qwen3-vl:235b":    "qwen3-vl:235b:cloud",
        "gemma4:26b":       "gemma4:26b:cloud",
        "gemma4:12b":       "gemma4:12b:cloud",
    }
    return exceptions.get(slug, f"{slug}:cloud")


# ── Fetching ───────────────────────────────────────────────────────────

def fetch(url: str) -> str | None:
    try:
        with urlopen(Request(url, headers=HEADERS), timeout=15) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        log(f"  ⚠️  Fetch error: {e}")
        return None


def scrape_models() -> list[dict[str, Any]]:
    """Scrape all cloud models from ollama.com/search?c=cloud."""
    all_models: list[dict[str, Any]] = []
    seen: set[str] = set()

    for page in (1, 2):
        html = fetch(SEARCH_URL.format(page=page))
        if not html:
            break

        pattern = r'<a href="/library/([^"]+)" class="group w-full">(.*?)</a>'
        for slug, block in re.findall(pattern, html, re.DOTALL):
            slug = slug.split("?")[0]
            if slug in seen:
                continue
            seen.add(slug)

            pm = re.search(r'<span x-test-pull-count>([^<]+)</span>', block)
            pulls = parse_pulls(pm.group(1)) if pm else 0

            tags = re.findall(r'<span x-test-capability[^>]*>([^<]+)</span>', block)

            dm = re.search(r'<p class="max-w-lg[^"]*">([^<]+)</p>', block)
            desc = dm.group(1).strip() if dm else ""

            am = re.search(r'<span x-test-updated>([^<]+)</span>', block)
            days_ago = 999
            if am:
                m = re.search(r'(\d+)\s*(day|week|month|year)s?\s*ago', am.group(1), re.I)
                if m:
                    n, unit = int(m.group(1)), m.group(2).lower()
                    days_ago = n * {"day": 1, "week": 7, "month": 30, "year": 365}.get(unit, 30)

            all_models.append({
                "slug": slug,
                "pulls": pulls,
                "tags": [t.lower() for t in tags],
                "desc": desc,
                "days_ago": days_ago,
            })

    return all_models


# ── Upgrade Detection (the core logic) ─────────────────────────────────

def detect_upgrades(
    models: list[dict[str, Any]],
) -> list[tuple[str, str, str, str]]:
    """
    For each dimension, check if a better model has appeared.
    
    Returns list of (dimension, current_slug, new_slug, reason).
    Returns empty list when current assignments are still optimal.
    """
    changes: list[tuple[str, str, str, str]] = []

    for dim, rules in UPGRADE_RULES.items():
        current_cloud = CURRENT_MAP[dim]
        current_family = current_cloud.split(":")[0]

        # Find all models that belong to the accepted slug families for this dim
        candidates: list[dict[str, Any]] = []
        for m in models:
            slug = m["slug"]
            # Check if this model belongs to any accepted family
            for fam in rules.get("slugs", []):
                if slug.startswith(fam) or fam.startswith(slug):
                    candidates.append(m)
                    break

        if not candidates:
            continue

        # Get data for current model
        current_data = None
        for m in models:
            if cloud_slug(m["slug"]) == current_cloud or m["slug"] == current_family:
                current_data = m
                break

        # Check for upgrade signals (known successor patterns)
        new_best = None
        reason = ""

        for m in candidates:
            m_cloud = cloud_slug(m["slug"])

            # Skip if same as current
            if m_cloud == current_cloud or m["slug"] == current_family:
                continue

            # Check required tags (e.g. vision)
            if rules.get("required_tags"):
                has = all(t in m.get("tags", []) for t in rules["required_tags"])
                if not has:
                    continue

            # Check min pulls
            min_p = rules.get("min_pulls", 0)
            if m["pulls"] < min_p:
                continue

            # Is this a successor model?
            sig = rules.get("upgrade_signal")
            if sig:
                signals = sig if isinstance(sig, tuple) else (sig,)
                for s in signals:
                    if s in m["slug"]:
                        new_best = m
                        diff = ""
                        if current_data:
                            pull_diff = m["pulls"] - current_data["pulls"]
                            day_diff = current_data["days_ago"] - m["days_ago"]
                            if pull_diff > 0:
                                diff += f"+{pull_diff:,} pulls"
                            if day_diff > 0:
                                diff += f", {day_diff}d newer"
                        reason = f"Successor model: {m['slug']} ({diff})" if diff else f"Successor model: {m['slug']}"
                        break

            # If an upgrade signal was found, take it immediately
            if new_best:
                break

            # No explicit successor, but check if it's a variant within the same family
            # that has significantly more pulls *and* is newer
            size = rules.get("size_variant")
            if size:
                # Only consider models with this size variant
                if size in m["slug"] and m["slug"] != current_family:
                    if current_data and m["pulls"] > current_data["pulls"] * 2 and m["days_ago"] < current_data["days_ago"]:
                        new_best = m
                        reason = f"{size} variant with {m['pulls']:,} pulls (2x+ current)"
                        break

        if new_best:
            new_cloud = cloud_slug(new_best["slug"])
            if new_cloud != current_cloud:
                changes.append((dim, current_cloud, new_cloud, reason))
                log(f"  🔄 {dim}: {current_cloud} → {new_cloud} — {reason}")

        if not new_best:
            log(f"  ✅ {dim}: {current_cloud} is still best fit")

    return changes


# ── Writer ──────────────────────────────────────────────────────────────

def write_dimension_map(changes: list[tuple[str, str, str, str]]) -> None:
    """Write updated dimension_map.py, preserving unchanged assignments."""
    dim_map = dict(CURRENT_MAP)
    for dim, _, new_slug, _ in changes:
        dim_map[dim] = new_slug

    lines = [
        '"""',
        "NEUROSWARM Swarm — Dimension Map",
        "",
        f"Auto-generated by model-scanner on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.",
        "",
        "The 10-Dimension council configuration. Each dimension maps to a",
        "specific cognitive capability and a specific model in Ollama Cloud.",
        "",
        "When a model in a dimension refuses or errors, NEUROSWARM routes",
        "to an adjacent dimension's model, NOT a flat list. This preserves",
        "the cognitive diversity of the council.",
        '"""',
        "",
        "# Updated by model-scanner based on ollama.com/search?c=cloud",
        "DIMENSION_MAP = {",
    ]
    for dim in CURRENT_MAP:
        model = dim_map[dim]
        desc = DESCRIPTIONS.get(dim, "")
        lines.append(f'    "{dim}":    "{model}",           # {desc}')
    lines.append("}")
    lines.append("")

    lines.append("# Dimension-aware fallback chains")
    lines.append("DIMENSION_FALLBACK = {")
    for dim in CURRENT_FALLBACK:
        fallbacks = CURRENT_FALLBACK[dim]
        lines.append(f'    "{dim}":    {json.dumps(fallbacks)},')
    lines.append("}")
    lines.append("")

    lines.append("# Dimension descriptions for documentation")
    lines.append("DIMENSION_DESCRIPTIONS = {")
    for dim, desc in DESCRIPTIONS.items():
        lines.append(f'    "{dim}":    "{desc}",')
    lines.append("}")
    lines.append("")

    lines.append("# Brain/swarm phase config")
    lines.append('BRAIN_PHASE_DIMENSIONS = ["D1_synthesis", "D2_deep_reason", "D5_strategy", "D6_analysis", "D7_general", "D8_verification", "D9_research"]')
    lines.append("SWARM_PHASE_DIMENSIONS = list(DIMENSION_MAP.keys())")
    lines.append("")

    DIMENSION_MAP_PATH.write_text("\n".join(lines) + "\n")


# ── Logging ────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ── Main ───────────────────────────────────────────────────────────────

def scan(do_commit: bool = False, do_push: bool = True) -> dict[str, Any]:
    log("🔍 Scanning Ollama Cloud for best-in-class models...")
    log(f"   Dimension map: {DIMENSION_MAP_PATH}")

    models = scrape_models()
    log(f"📦 Found {len(models)} cloud models")

    changes = detect_upgrades(models)

    if not changes:
        log("✅ No dimension reassignments needed")
        return {"scanned": len(models), "changes": []}

    write_dimension_map(changes)
    log(f"💾 Updated {DIMENSION_MAP_PATH}")

    # Save state
    state = {
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "models_scanned": len(models),
        "changes": [(d, o, n) for d, o, n, _ in changes],
    }
    STATE_FILE.write_text(json.dumps(state, indent=2))

    # Git commit + push
    if do_commit:
        try:
            subprocess.run(["git", "add", "-A"], cwd=K2_ROOT, check=True, capture_output=True)
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            change_summary = "; ".join(f"{d}: {o}→{n}" for d, o, n, _ in changes)
            msg = f"chore: auto-update dimension map ({date_str})\n\n{change_summary}"
            subprocess.run(["git", "commit", "-m", msg], cwd=K2_ROOT, check=True, capture_output=True)

            if do_push:
                subprocess.run(["git", "push", "origin", "main"], cwd=K2_ROOT, check=True, capture_output=True)
                log("🚀 Pushed to GitHub")
        except subprocess.CalledProcessError as e:
            log(f"⚠️  Git error: {e.stderr.decode()}")

    return {"scanned": len(models), "changes": changes}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ollama Cloud model scanner")
    parser.add_argument("--commit", action="store_true", help="Auto-commit changes")
    parser.add_argument("--no-push", action="store_true", help="Commit but don't push")
    args = parser.parse_args()

    result = scan(do_commit=args.commit, do_push=not args.no_push)
    n = len(result["changes"])
    if n:
        print(f"\n{'='*40}")
        print(f"{n} dimension(s) updated:")
        for d, o, n_slug, _ in result["changes"]:
            print(f"  {d}: {o} → {n_slug}")
    else:
        print(f"\n✅ No changes. {result['scanned']} models scanned.")