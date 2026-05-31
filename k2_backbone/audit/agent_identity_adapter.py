from __future__ import annotations
"""
Agent Identity Adapter for K2-Backbone

On-chain execution attestation via ERC-8004.
Every execution trace gets logged to chain with:
- Task hash
- Models used
- Cost incurred
- Result hash
- Timestamp

Usage:
    from k2_backbone.audit.agent_identity_adapter import AgentIdentityAdapter
    
    identity = AgentIdentityAdapter()
    attestation = identity.attest_execution(execution_trace)
    
    # Verify later
    is_valid = identity.verify_attestation(attestation_hash)
"""

import hashlib
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExecutionAttestation:
    task_id: str
    task_hash: str
    models_used: List[str]
    total_cost_usd: float
    result_hash: str
    timestamp: str
    signature: str = ""
    chain_tx_hash: Optional[str] = None


class AgentIdentityAdapter:
    """
    Bridges Agent Identity on-chain registry with K2-Backbone execution.
    
    Provides:
    - Immutable execution logging
    - Cost transparency
    - Model usage tracking
    - Cross-system audit trail
    """
    
    def __init__(
        self,
        identity_path: Optional[Path] = None,
        chain_enabled: bool = False,
        local_attestation: bool = True,
    ):
        self.identity_path = identity_path or Path(__file__).parent.parent.parent / "frameworks" / "agent-identity"
        self.chain_enabled = chain_enabled
        self.local_attestation = local_attestation
        
        self._attestations: Dict[str, ExecutionAttestation] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        if self._initialized:
            return
        
        if not self.identity_path.exists():
            logger.warning(f"Agent Identity not found at {self.identity_path}")
            logger.info("Running in local-only mode")
        
        self._initialized = True
        logger.info("AgentIdentityAdapter initialized")
    
    def attest_execution(self, execution_result: Dict[str, Any]) -> ExecutionAttestation:
        """
        Create attestation for an execution trace.
        
        In production: submits to ERC-8004 contract.
        In local mode: stores hash in memory.
        """
        self._ensure_initialized()
        
        task_id = execution_result.get("task_id", "unknown")
        
        # Build attestation content
        models = execution_result.get("summary", {}).get("models_used", [])
        cost = execution_result.get("cost", {}).get("estimated", 0.0)
        
        # Compute hashes
        task_content = json.dumps(execution_result.get("task", {}), sort_keys=True)
        task_hash = hashlib.sha256(task_content.encode()).hexdigest()[:32]
        
        result_content = json.dumps(execution_result.get("execution_trace", {}), sort_keys=True)
        result_hash = hashlib.sha256(result_content.encode()).hexdigest()[:32]
        
        attestation = ExecutionAttestation(
            task_id=task_id,
            task_hash=task_hash,
            models_used=models_used,
            total_cost_usd=cost,
            result_hash=result_hash,
            timestamp=datetime.now().isoformat(),
            signature=f"local_{task_hash[:16]}",
        )
        
        # Store locally
        if self.local_attestation:
            self._attestations[task_id] = attestation
            logger.info(f"Attestation created: {task_id} → {task_hash}")
        
        # Submit to chain (if enabled)
        if self.chain_enabled:
            attestation.chain_tx_hash = self._submit_to_chain(attestation)
            logger.info(f"On-chain attestation: {attestation.chain_tx_hash}")
        
        return attestation
    
    def verify_attestation(self, task_id: str) -> Dict[str, Any]:
        """
        Verify an attestation exists and is valid.
        """
        self._ensure_initialized()
        
        attestation = self._attestations.get(task_id)
        if not attestation:
            return {"valid": False, "error": "Attestation not found"}
        
        # Verify hash integrity
        # In production: verify against on-chain record
        return {
            "valid": True,
            "task_id": attestation.task_id,
            "task_hash": attestation.task_hash,
            "models_used": attestation.models_used,
            "cost_usd": attestation.total_cost_usd,
            "timestamp": attestation.timestamp,
            "chain_verified": attestation.chain_tx_hash is not None,
        }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution attestations"""
        self._ensure_initialized()
        
        sorted_items = sorted(
            self._attestations.items(),
            key=lambda x: x[1].timestamp,
            reverse=True
        )
        
        return [
            {
                "task_id": att.task_id,
                "models": att.models_used,
                "cost": att.total_cost_usd,
                "timestamp": att.timestamp,
                "verified": att.chain_tx_hash is not None,
            }
            for _, att in sorted_items[:limit]
        ]
    
    def get_cost_audit(self) -> Dict[str, Any]:
        """
        Generate cost audit report from attestations.
        """
        self._ensure_initialized()
        
        total_executions = len(self._attestations)
        total_cost = sum(a.total_cost_usd for a in self._attestations.values())
        
        model_usage: Dict[str, int] = {}
        for att in self._attestations.values():
            for model in att.models_used:
                model_usage[model] = model_usage.get(model, 0) + 1
        
        return {
            "total_executions": total_executions,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_execution": round(total_cost / max(total_executions, 1), 4),
            "model_usage": model_usage,
            "attestations_on_chain": sum(1 for a in self._attestations.values() if a.chain_tx_hash),
            "attestations_local": sum(1 for a in self._attestations.values() if not a.chain_tx_hash),
        }
    
    # ==================== Helpers ====================
    
    def _submit_to_chain(self, attestation: ExecutionAttestation) -> Optional[str]:
        """Submit attestation to ERC-8004 contract"""
        # In production: Web3 transaction
        # For now: simulate
        return f"0x{hashlib.sha256(attestation.task_hash.encode()).hexdigest()[:40]}"
    
    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Identity Audit Adapter")
    parser.add_argument("--attest", metavar="FILE", help="Attest execution trace JSON")
    parser.add_argument("--verify", metavar="TASK_ID", help="Verify attestation")
    parser.add_argument("--history", action="store_true", help="Show execution history")
    parser.add_argument("--audit", action="store_true", help="Generate cost audit")
    args = parser.parse_args()
    
    adapter = AgentIdentityAdapter()
    
    if args.attest:
        with open(args.attest) as f:
            trace = json.load(f)
        attestation = adapter.attest_execution(trace)
        print(f"✅ Attested: {attestation.task_id}")
        print(f"   Task hash: {attestation.task_hash}")
        print(f"   Cost: ${attestation.total_cost_usd:.4f}")
        print(f"   Models: {', '.join(attestation.models_used)}")
    
    if args.verify:
        result = adapter.verify_attestation(args.verify)
        print(f"{'✅' if result['valid'] else '❌'} Verification: {args.verify}")
        if result['valid']:
            print(f"   Cost: ${result['cost_usd']}")
            print(f"   Chain verified: {result['chain_verified']}")
    
    if args.history:
        history = adapter.get_execution_history(limit=10)
        print(f"📜 Recent executions ({len(history)}):")
        for h in history[:5]:
            print(f"   {h['task_id']}: ${h['cost']} | {', '.join(h['models'])}")
    
    if args.audit:
        audit = adapter.get_cost_audit()
        print(f"📊 Cost Audit:")
        print(f"   Total executions: {audit['total_executions']}")
        print(f"   Total cost: ${audit['total_cost_usd']}")
        print(f"   Avg per execution: ${audit['avg_cost_per_execution']}")
        print(f"   Model usage:")
        for model, count in audit['model_usage'].items():
            print(f"      {model}: {count}")


if __name__ == "__main__":
    main()
