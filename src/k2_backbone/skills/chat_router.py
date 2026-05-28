"""
K2-Backbone Chat Router

Routes chat/conversation tasks to the configured T0 chat model.
Default: deepseek-v4-flash (fast, cost-efficient, 1M context)
"""

import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from k2_backbone.skills.recursive_retrieval import ContextTree, MemoryLayer


@dataclass
class ChatConfig:
    """Configuration for chat routing."""
    model: str = "deepseek-v4-flash"
    context_size: int = 1000000  # 1M tokens
    max_history: int = 50  # Messages to keep
    temperature: float = 0.7
    fallback_model: str = "kimi-k2.6"
    cost_per_1m: float = 0.60


class K2ChatRouter:
    """Routes chat tasks to the appropriate model with context management.
    
    Usage:
        router = K2ChatRouter()
        response = router.chat("Hello, how are you?", session_id="sess_001")
    """
    
    def __init__(self, config: Optional[ChatConfig] = None):
        """Initialize chat router.
        
        Args:
            config: Chat configuration. Defaults to deepseek-v4-flash T0.
        """
        self.config = config or ChatConfig()
        
        # Allow override from environment
        env_model = os.getenv("K2_CHAT_MODEL")
        if env_model:
            self.config.model = env_model
        
        # Session history store
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
    
    def chat(
        self,
        message: str,
        session_id: str,
        system_prompt: Optional[str] = None,
        context_tree: Optional[ContextTree] = None
    ) -> Dict[str, Any]:
        """Process a chat message and return response.
        
        Args:
            message: User message
            session_id: Session identifier for history
            system_prompt: Optional system prompt
            context_tree: Optional context tree for layer-aware retrieval
        
        Returns:
            Dict with response, model used, tokens, cost
        """
        # Initialize session history
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        # Get context from tree if available
        context = {}
        if context_tree:
            context = {
                "agent_id": context_tree.agent_id,
                "session_context": context_tree.get_merged_context()
            }
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add history
        messages.extend(self.sessions[session_id])
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Determine model (with fallback logic)
        model = self._select_model(messages)
        
        # Here you would call the actual model API
        # For now, return the routing decision
        result = {
            "model": model,
            "messages": messages,
            "context": context,
            "session_id": session_id,
            "estimated_tokens": self._estimate_tokens(messages),
            "estimated_cost": self._estimate_cost(messages, model),
            "status": "routed",
        }
        
        # Store in history
        self.sessions[session_id].append({"role": "user", "content": message})
        
        return result
    
    def _select_model(self, messages: List[Dict[str, str]]) -> str:
        """Select model based on message complexity and context."""
        # Check if we need fallback (e.g., context too long)
        total_length = sum(len(m["content"]) for m in messages)
        
        # If approaching context limit, use fallback with larger context
        if total_length > self.config.context_size * 0.8:
            return self.config.fallback_model
        
        return self.config.model
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        total_chars = sum(len(m["content"]) for m in messages)
        return total_chars // 4
    
    def _estimate_cost(self, messages: List[Dict[str, str]], model: str) -> float:
        """Estimate cost in USD."""
        tokens = self._estimate_tokens(messages)
        # Cost per 1M tokens
        cost_per_1m = self.config.cost_per_1m if model == self.config.model else 3.0
        return (tokens / 1_000_000) * cost_per_1m
    
    def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get chat history for a session."""
        return self.sessions.get(session_id, [])
    
    def clear_session(self, session_id: str):
        """Clear chat history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "active_sessions": len(self.sessions),
            "default_model": self.config.model,
            "fallback_model": self.config.fallback_model,
            "context_size": self.config.context_size,
            "total_messages": sum(len(h) for h in self.sessions.values()),
        }


# Convenience function for quick chat routing
def route_chat(
    message: str,
    session_id: str = "default",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Quick chat routing function.
    
    Usage:
        result = route_chat("Hello", session_id="sess_001")
        print(result["model"])  # deepseek-v4-flash
    """
    config = ChatConfig(model=model) if model else None
    router = K2ChatRouter(config)
    return router.chat(message, session_id)
