from __future__ import annotations
"""
ScoutForge Adapter for K2-Backbone

Auto-discovers new models from HuggingFace/GitHub and updates
K2-Backbone's router with best-in-class candidates.

Usage:
    from k2_backbone.discovery.scoutforge_adapter import ScoutForgeAdapter
    
    scout = ScoutForgeAdapter()
    new_models = scout.discover(category="code", min_benchmark=75.0)
    scout.update_router(new_models)
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredModel:
    id: str
    name: str
    source: str  # "huggingface", "github", "ollama"
    params: str
    context: str
    benchmarks: Dict[str, float]
    strengths: List[str]
    discovered_at: str


class ScoutForgeAdapter:
    """
    Bridges ScoutForge model discovery into K2-Backbone routing.
    
    Keeps the router's model catalog current by:
    1. Discovering new models from HuggingFace/GitHub
    2. Benchmarking against existing models
    3. Updating router config when new SOTA emerges
    """
    
    def __init__(
        self,
        scoutforge_path: Optional[Path] = None,
        update_threshold: float = 5.0,  # Min improvement % to update
        auto_update: bool = False,
    ):
        self.scoutforge_path = scoutforge_path or Path(__file__).parent.parent.parent / "frameworks" / "scoutforge"
        self.update_threshold = update_threshold
        self.auto_update = auto_update
        
        self._discovered: Dict[str, DiscoveredModel] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        if self._initialized:
            return
        
        if not self.scoutforge_path.exists():
            logger.warning(f"ScoutForge not found at {self.scoutforge_path}")
            return
        
        self._initialized = True
        logger.info("ScoutForgeAdapter initialized")
    
    def discover(
        self,
        category: str = "all",
        min_benchmark: float = 70.0,
        limit: int = 10,
    ) -> List[DiscoveredModel]:
        """
        Discover models from ScoutForge's crawled data.
        
        Args:
            category: "code", "reasoning", "agentic", "multimodal", or "all"
            min_benchmark: Minimum benchmark score to include
            limit: Max models to return
        """
        self._ensure_initialized()
        
        # In production: Read from ScoutForge's crawled output
        # For now: simulate discovery from known sources
        discovered = []
        
        # Simulate reading from ScoutForge's model database
        models = self._load_scoutforge_models()
        
        for model in models:
            if category != "all" and category not in model.strengths:
                continue
            
            # Check if any benchmark exceeds threshold
            if any(score >= min_benchmark for score in model.benchmarks.values()):
                discovered.append(model)
        
        # Sort by highest benchmark score
        discovered.sort(key=lambda m: max(m.benchmarks.values()) if m.benchmarks else 0, reverse=True)
        
        logger.info(f"Discovered {len(discovered)} models in category '{category}'")
        return discovered[:limit]
    
    def compare_with_current(
        self,
        discovered: DiscoveredModel,
        current_models: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare discovered model with current router config.
        Returns upgrade recommendations.
        """
        recommendations = []
        
        for task_type, score in discovered.benchmarks.items():
            # Find current best for this task type
            current_best = self._find_current_best(task_type, current_models)
            
            if current_best:
                current_score = current_best.get("benchmarks", {}).get(task_type, 0)
                improvement = ((score - current_score) / max(current_score, 1)) * 100
                
                if improvement >= self.update_threshold:
                    recommendations.append({
                        "task_type": task_type,
                        "current": current_best.get("id"),
                        "current_score": current_score,
                        "discovered": discovered.id,
                        "discovered_score": score,
                        "improvement_pct": round(improvement, 1),
                        "recommendation": "upgrade",
                    })
        
        return {
            "model": discovered.id,
            "recommendations": recommendations,
            "should_update": len(recommendations) > 0,
        }
    
    def update_router(
        self,
        models: List[DiscoveredModel],
        router_config_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Update router configuration with discovered models.
        Returns summary of changes.
        """
        self._ensure_initialized()
        
        # Load current router config
        from k2_backbone.router.necroswarm_router_v2 import OLLAMA_CLOUD_MODELS, TASK_TYPE_TO_MODEL
        
        updates = []
        
        for model in models:
            comparison = self.compare_with_current(model, OLLAMA_CLOUD_MODELS)
            
            if comparison["should_update"]:
                # Update TASK_TYPE_TO_MODEL for affected task types
                for rec in comparison["recommendations"]:
                    task_type = rec["task_type"]
                    
                    if task_type in TASK_TYPE_TO_MODEL:
                        current_list = TASK_TYPE_TO_MODEL[task_type]
                        
                        # Replace if better, keep structure (primary, fallback, budget)
                        if rec["improvement_pct"] >= 10:
                            # Significant improvement: make primary
                            if model.id not in current_list:
                                current_list.insert(0, model.id)
                                if len(current_list) > 3:
                                    current_list.pop()  # Keep only top 3
                        elif rec["improvement_pct"] >= self.update_threshold:
                            # Moderate: add as fallback
                            if model.id not in current_list:
                                current_list.append(model.id)
                                if len(current_list) > 3:
                                    current_list.pop()
                        
                        updates.append({
                            "task_type": task_type,
                            "action": "updated",
                            "model": model.id,
                            "improvement": rec["improvement_pct"],
                        })
        
        logger.info(f"Router updated with {len(updates)} changes")
        
        return {
            "discovered": len(models),
            "updates": updates,
            "timestamp": datetime.now().isoformat(),
        }
    
    def run_discovery_cycle(self) -> Dict[str, Any]:
        """
        Full discovery cycle: discover → compare → update.
        """
        self._ensure_initialized()
        
        logger.info("Starting discovery cycle...")
        
        # Discover in all categories
        categories = ["code", "reasoning", "agentic", "multimodal"]
        all_discovered = []
        
        for cat in categories:
            models = self.discover(category=cat, limit=5)
            all_discovered.extend(models)
        
        # Update router
        result = self.update_router(all_discovered)
        
        return {
            "cycle": "complete",
            "discovered": result["discovered"],
            "updates": result["updates"],
            "timestamp": result["timestamp"],
        }
    
    # ==================== Helpers ====================
    
    def _load_scoutforge_models(self) -> List[DiscoveredModel]:
        """Load models from ScoutForge's crawled data"""
        # In production: Read ScoutForge's output files
        # For now: return simulated recent discoveries
        
        # Simulate: GLM-5.1 was discovered as code leader
        # Simulate: Qwen3.5 122B was discovered as reasoning leader
        
        return [
            DiscoveredModel(
                id="glm-5.1",
                name="GLM-5.1",
                source="huggingface",
                params="Flagship",
                context="Standard",
                benchmarks={"code": 58.4, "terminal": 63.5, "nl2repo": 42.7},
                strengths=["code_generation", "agentic_engineering", "terminal_tasks"],
                discovered_at="2026-05-22",
            ),
            DiscoveredModel(
                id="qwen3.5-122b",
                name="Qwen3.5 122B",
                source="huggingface",
                params="122B MoE",
                context="Standard",
                benchmarks={"reasoning": 95.3, "math": 100, "mmlu": 87.8},
                strengths=["reasoning", "math", "multilingual", "research"],
                discovered_at="2026-05-22",
            ),
            DiscoveredModel(
                id="nemotron-3-super",
                name="Nemotron-3-Super",
                source="huggingface",
                params="120B (12B active)",
                context="Standard",
                benchmarks={"multi_agent": 60.47, "ruler": 96.3, "mmlu": 83.73},
                strengths=["multi_agent", "efficiency", "IT_automation"],
                discovered_at="2026-05-20",
            ),
            DiscoveredModel(
                id="devstral-small-2",
                name="Devstral Small 2",
                source="huggingface",
                params="24B",
                context="Standard",
                benchmarks={"swe": 65.8, "terminal": 32.0},
                strengths=["code_review", "tool_use", "SWE"],
                discovered_at="2026-05-18",
            ),
        ]
    
    def _find_current_best(self, task_type: str, current_models: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find current best model for a task type"""
        # Map task type to known benchmark key
        benchmark_keys = {
            "code": "SWE-Bench-Pro",
            "reasoning": "AIME-2026",
            "agentic": "Agents",
            "multimodal": "MMLU-Pro",
        }
        
        key = benchmark_keys.get(task_type, task_type)
        best = None
        best_score = 0
        
        for model_id, model in current_models.items():
            score = model.benchmarks.get(key, 0)
            if score > best_score:
                best_score = score
                best = {"id": model_id, "benchmarks": {key: score}}
        
        return best
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ScoutForge Discovery Adapter")
    parser.add_argument("--discover", action="store_true", help="Run discovery")
    parser.add_argument("--category", default="all", choices=["all", "code", "reasoning", "agentic", "multimodal"])
    parser.add_argument("--update", action="store_true", help="Update router")
    parser.add_argument("--cycle", action="store_true", help="Full discovery cycle")
    args = parser.parse_args()
    
    adapter = ScoutForgeAdapter()
    
    if args.cycle:
        result = adapter.run_discovery_cycle()
        print(f"✅ Discovery cycle: {result['discovered']} models, {len(result['updates'])} updates")
        for u in result['updates']:
            print(f"   {u['task_type']}: {u['model']} (+{u['improvement']}%)")
    elif args.discover:
        models = adapter.discover(category=args.category)
        print(f"🔍 Discovered {len(models)} models in '{args.category}':")
        for m in models:
            best_score = max(m.benchmarks.values()) if m.benchmarks else 0
            print(f"   {m.id} ({m.source}): {best_score:.1f} — {', '.join(m.strengths[:2])}")
    elif args.update:
        models = adapter.discover(category="all")
        result = adapter.update_router(models)
        print(f"🔄 Updated router: {len(result['updates'])} changes")


if __name__ == "__main__":
    main()
