from __future__ import annotations
"""
OpenClaw Namespace Adapter for K2-Backbone

Bridges openclaw:// URI resolution into K2-Backbone's router,
memory pipeline, and task execution.

Every TaskSpec task_id becomes a canonical openclaw:// URI:
  openclaw://tasks/k2-backbone/{task_id}
  openclaw://memory/episodic/{task_id}
  openclaw://memory/semantic/{pattern}
  openclaw://memory/archetypal/{archetype}

Usage:
    from k2_backbone.namespaces.openclaw_namespace_adapter import NamespaceRouterAdapter
    
    ns = NamespaceRouterAdapter()
    
    # Resolve task to canonical path
    path = ns.resolve_task("k2_1234567890")
    
    # Resolve memory layer
    episodic = ns.resolve_memory("k2_1234567890", level="episodic")
    semantic = ns.resolve_memory("performance-java", level="semantic")
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# Add openclaw-namespace to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "frameworks" / "openclaw-namespace"))

try:
    from namespace import NamespaceResolver, URIParser, register_handler
    from namespace import NAMESPACE_HANDLERS
    NAMESPACE_AVAILABLE = True
except ImportError:
    logger.warning("openclaw-namespace not available, using fallback")
    NAMESPACE_AVAILABLE = False


class NamespaceRouterAdapter:
    """
    Bridges OpenClaw namespace resolution with K2-Backbone pipeline.
    
    Provides:
    - Canonical URIs for all K2-Backbone entities (tasks, memories, traces)
    - Deterministic path resolution for storage and retrieval
    - Namespace registration for K2-Backbone-specific resources
    """
    
    def __init__(
        self,
        base_path: Optional[Path] = None,
        workspace: str = "k2-backbone",
    ):
        self.base_path = base_path or Path.home() / ".openclaw" / "workspace"
        self.workspace = workspace
        self._resolver: Optional[Any] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize namespace resolver with K2-Backbone handlers"""
        if self._initialized:
            return
        
        if NAMESPACE_AVAILABLE:
            self._resolver = NamespaceResolver(base_path=self.base_path)
            self._register_k2_handlers()
        else:
            logger.warning("Using fallback namespace resolution")
        
        self._initialized = True
        logger.info(f"NamespaceRouterAdapter initialized (workspace: {self.workspace})")
    
    def _register_k2_handlers(self) -> None:
        """Register K2-Backbone-specific namespace handlers"""
        if not NAMESPACE_AVAILABLE:
            return
        
        @register_handler("k2")
        def _handle_k2(base_path: Path, parsed: Any) -> Path:
            """
            Handle k2:// URIs for K2-Backbone entities
            
            Format: openclaw://k2/{entity}/{id}
            
            Examples:
                openclaw://k2/tasks/k2_1234567890 → taskspec JSON
                openclaw://k2/routed/k2_1234567890 → routed spec
                openclaw://k2/traces/k2_1234567890 → execution trace
                openclaw://k2/costs/k2_1234567890 → cost record
            """
            if not parsed.path_parts:
                return base_path / self.workspace
            
            entity = parsed.path_parts[0]
            
            if entity == "tasks" and len(parsed.path_parts) >= 2:
                task_id = parsed.path_parts[1]
                return base_path / self.workspace / "tasks" / f"{task_id}.json"
            
            elif entity == "routed" and len(parsed.path_parts) >= 2:
                task_id = parsed.path_parts[1]
                return base_path / self.workspace / "routed" / f"{task_id}.json"
            
            elif entity == "traces" and len(parsed.path_parts) >= 2:
                task_id = parsed.path_parts[1]
                return base_path / self.workspace / "traces" / f"{task_id}.json"
            
            elif entity == "costs" and len(parsed.path_parts) >= 2:
                task_id = parsed.path_parts[1]
                return base_path / self.workspace / "costs" / f"{task_id}.json"
            
            elif entity == "schemas" and len(parsed.path_parts) >= 2:
                schema_id = parsed.path_parts[1]
                return base_path / self.workspace / "schemas" / f"{schema_id}.json"
            
            # Default
            subpath = "/".join(parsed.path_parts)
            return base_path / self.workspace / f"{subpath}.json"
        
        @register_handler("obliviarch")
        def _handle_obliviarch(base_path: Path, parsed: Any) -> Path:
            """
            Handle obliviarch:// URIs for memory compression
            
            Format: openclaw://obliviarch/{level}/{id}
            
            Examples:
                openclaw://obliviarch/episodic/k2_1234567890
                openclaw://obliviarch/semantic/performance-java
                openclaw://obliviarch/archetypal/code-optimization
            """
            if not parsed.path_parts:
                return base_path / self.workspace / ".obliviarch"
            
            level = parsed.path_parts[0]
            
            if level in ["episodic", "semantic", "archetypal"] and len(parsed.path_parts) >= 2:
                memory_id = parsed.path_parts[1]
                return base_path / self.workspace / ".obliviarch" / level / f"{memory_id}.json"
            
            return base_path / self.workspace / ".obliviarch" / level
        
        @register_handler("council")
        def _handle_council(base_path: Path, parsed: Any) -> Path:
            """
            Handle council:// URIs for 10-D Council records
            
            Format: openclaw://council/{dimension}/{date}
            
            Examples:
                openclaw://council/votes/2026-05-28 → daily vote log
                openclaw://council/models/kimi-k2.6 → model performance
            """
            if not parsed.path_parts:
                return base_path / self.workspace / "council"
            
            record_type = parsed.path_parts[0]
            
            if record_type == "votes" and len(parsed.path_parts) >= 2:
                date = parsed.path_parts[1]
                return base_path / self.workspace / "council" / "votes" / f"{date}.jsonl"
            
            elif record_type == "models" and len(parsed.path_parts) >= 2:
                model_id = parsed.path_parts[1]
                return base_path / self.workspace / "council" / "models" / f"{model_id}.json"
            
            return base_path / self.workspace / "council" / record_type
    
    # ==================== Task Resolution ====================
    
    def resolve_task(self, task_id: str) -> Path:
        """Resolve a task ID to canonical filesystem path"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://k2/tasks/{task_id}")
        
        return self.base_path / self.workspace / "tasks" / f"{task_id}.json"
    
    def resolve_routed(self, task_id: str) -> Path:
        """Resolve routed spec path"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://k2/routed/{task_id}")
        
        return self.base_path / self.workspace / "routed" / f"{task_id}.json"
    
    def resolve_trace(self, task_id: str) -> Path:
        """Resolve execution trace path"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://k2/traces/{task_id}")
        
        return self.base_path / self.workspace / "traces" / f"{task_id}.json"
    
    def resolve_cost(self, task_id: str) -> Path:
        """Resolve cost record path"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://k2/costs/{task_id}")
        
        return self.base_path / self.workspace / "costs" / f"{task_id}.json"
    
    # ==================== Memory Resolution ====================
    
    def resolve_memory(
        self,
        memory_id: str,
        level: str = "episodic",
    ) -> Path:
        """
        Resolve memory to canonical path.
        
        Args:
            memory_id: Task ID or pattern name
            level: "episodic", "semantic", or "archetypal"
        """
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://obliviarch/{level}/{memory_id}")
        
        return self.base_path / self.workspace / ".obliviarch" / level / f"{memory_id}.json"
    
    def resolve_schema(self, schema_id: str) -> Path:
        """Resolve compressed schema path"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://k2/schemas/{schema_id}")
        
        return self.base_path / self.workspace / "schemas" / f"{schema_id}.json"
    
    # ==================== Council Resolution ====================
    
    def resolve_council_vote(self, date: Optional[str] = None) -> Path:
        """Resolve council vote log path"""
        self._ensure_initialized()
        
        date = date or datetime.now().strftime("%Y-%m-%d")
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://council/votes/{date}")
        
        return self.base_path / self.workspace / "council" / "votes" / f"{date}.jsonl"
    
    def resolve_model_record(self, model_id: str) -> Path:
        """Resolve model performance record path"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(f"openclaw://council/models/{model_id}")
        
        return self.base_path / self.workspace / "council" / "models" / f"{model_id}.json"
    
    # ==================== Generic Resolution ====================
    
    def resolve(self, uri: str) -> Path:
        """Resolve any openclaw:// URI"""
        self._ensure_initialized()
        
        if self._resolver:
            return self._resolver.resolve(uri)
        
        # Fallback: simple path construction
        if uri.startswith("openclaw://"):
            path_part = uri.replace("openclaw://", "")
            return self.base_path / self.workspace / path_part
        
        return Path(uri)
    
    def resolve_str(self, uri: str) -> str:
        """Resolve URI and return as string"""
        return str(self.resolve(uri))
    
    def parse(self, uri: str) -> Dict[str, Any]:
        """Parse URI into components"""
        self._ensure_initialized()
        
        if NAMESPACE_AVAILABLE and self._resolver:
            from namespace import URIParser
            parsed = URIParser.parse(uri)
            return {
                "raw": parsed.raw,
                "namespace": parsed.namespace,
                "path_parts": parsed.path_parts,
                "resource_type": parsed.resource_type,
                "resource_id": parsed.resource_id,
                "query": parsed.query,
                "fragment": parsed.fragment,
            }
        
        # Fallback
        parts = uri.replace("openclaw://", "").split("/")
        return {
            "raw": uri,
            "namespace": parts[0] if parts else "",
            "path_parts": parts[1:] if len(parts) > 1 else [],
            "resource_type": parts[1] if len(parts) > 1 else "",
            "resource_id": parts[2] if len(parts) > 2 else None,
        }
    
    # ==================== Utility ====================
    
    def ensure_directories(self) -> None:
        """Create all K2-Backbone namespace directories"""
        dirs = [
            self.base_path / self.workspace / "tasks",
            self.base_path / self.workspace / "routed",
            self.base_path / self.workspace / "traces",
            self.base_path / self.workspace / "costs",
            self.base_path / self.workspace / "schemas",
            self.base_path / self.workspace / ".obliviarch" / "episodic",
            self.base_path / self.workspace / ".obliviarch" / "semantic",
            self.base_path / self.workspace / ".obliviarch" / "archetypal",
            self.base_path / self.workspace / "council" / "votes",
            self.base_path / self.workspace / "council" / "models",
        ]
        
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Ensured {len(dirs)} namespace directories")
    
    def get_registered_namespaces(self) -> Dict[str, str]:
        """Get all registered namespace handlers"""
        self._ensure_initialized()
        
        if NAMESPACE_AVAILABLE:
            return {
                ns: (handler.__doc__ or "").strip().split("\n")[0]
                for ns, handler in NAMESPACE_HANDLERS.items()
            }
        
        return {
            "k2": "K2-Backbone entities (tasks, traces, costs)",
            "obliviarch": "Memory compression layers",
            "council": "10-D Council records",
        }
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="K2-Backbone Namespace Router")
    parser.add_argument("--resolve", metavar="URI", help="Resolve URI to path")
    parser.add_argument("--parse", metavar="URI", help="Parse URI components")
    parser.add_argument("--task", metavar="TASK_ID", help="Resolve task path")
    parser.add_argument("--memory", metavar="MEMORY_ID", help="Resolve memory path")
    parser.add_argument("--level", default="episodic", choices=["episodic", "semantic", "archetypal"])
    parser.add_argument("--setup", action="store_true", help="Create namespace directories")
    parser.add_argument("--list", action="store_true", help="List registered namespaces")
    args = parser.parse_args()
    
    adapter = NamespaceRouterAdapter()
    
    if args.setup:
        adapter.ensure_directories()
        print("✅ Namespace directories created")
    
    if args.list:
        namespaces = adapter.get_registered_namespaces()
        print("Registered Namespaces:")
        for ns, desc in namespaces.items():
            print(f"  {ns:15} - {desc}")
    
    if args.resolve:
        path = adapter.resolve(args.resolve)
        print(f"{args.resolve} → {path}")
    
    if args.parse:
        parsed = adapter.parse(args.parse)
        print(f"URI: {parsed['raw']}")
        print(f"Namespace: {parsed['namespace']}")
        print(f"Path Parts: {parsed['path_parts']}")
        print(f"Resource Type: {parsed.get('resource_type', '')}")
        print(f"Resource ID: {parsed.get('resource_id', '')}")
    
    if args.task:
        path = adapter.resolve_task(args.task)
        print(f"Task {args.task} → {path}")
    
    if args.memory:
        path = adapter.resolve_memory(args.memory, level=args.level)
        print(f"Memory {args.memory} ({args.level}) → {path}")


if __name__ == "__main__":
    main()
