"""
Unit tests for K2-Backbone Chat Router
"""

import pytest
import os
from unittest.mock import patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from skills.chat_router import K2ChatRouter, ChatConfig, route_chat


class TestChatRouter:
    """Test chat router functionality."""
    
    def test_default_config(self):
        """Test default configuration uses deepseek-v4-flash."""
        router = K2ChatRouter()
        assert router.config.model == "deepseek-v4-flash"
        assert router.config.context_size == 1000000
        assert router.config.cost_per_1m == 0.60
    
    def test_custom_config(self):
        """Test custom model configuration."""
        config = ChatConfig(model="kimi-k2.6", cost_per_1m=3.0)
        router = K2ChatRouter(config)
        assert router.config.model == "kimi-k2.6"
    
    def test_env_override(self):
        """Test environment variable override."""
        with patch.dict(os.environ, {"K2_CHAT_MODEL": "qwen3.5-122b"}):
            router = K2ChatRouter()
            assert router.config.model == "qwen3.5-122b"
    
    def test_chat_routing(self):
        """Test basic chat routing."""
        router = K2ChatRouter()
        result = router.chat("Hello", session_id="test_001")
        
        assert result["model"] == "deepseek-v4-flash"
        assert result["session_id"] == "test_001"
        assert result["status"] == "routed"
        assert "estimated_tokens" in result
        assert "estimated_cost" in result
    
    def test_chat_history(self):
        """Test session history tracking."""
        router = K2ChatRouter()
        
        # Send multiple messages
        router.chat("Hello", session_id="test_history")
        router.chat("How are you?", session_id="test_history")
        
        history = router.get_session_history("test_history")
        assert len(history) == 2
        assert history[0]["content"] == "Hello"
        assert history[1]["content"] == "How are you?"
    
    def test_session_isolation(self):
        """Test that sessions are isolated."""
        router = K2ChatRouter()
        
        router.chat("Hello A", session_id="session_a")
        router.chat("Hello B", session_id="session_b")
        
        history_a = router.get_session_history("session_a")
        history_b = router.get_session_history("session_b")
        
        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0]["content"] == "Hello A"
        assert history_b[0]["content"] == "Hello B"
    
    def test_clear_session(self):
        """Test clearing session history."""
        router = K2ChatRouter()
        
        router.chat("Hello", session_id="clear_test")
        assert len(router.get_session_history("clear_test")) == 1
        
        router.clear_session("clear_test")
        assert len(router.get_session_history("clear_test")) == 0
    
    def test_system_prompt(self):
        """Test system prompt inclusion."""
        router = K2ChatRouter()
        result = router.chat(
            "Hello",
            session_id="system_test",
            system_prompt="You are a helpful assistant."
        )
        
        messages = result["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
    
    def test_fallback_selection(self):
        """Test fallback model selection for long context."""
        config = ChatConfig(model="deepseek-v4-flash", context_size=1000)
        router = K2ChatRouter(config)
        
        # Create messages that exceed 80% of context
        long_messages = [{"role": "user", "content": "x" * 900}]
        model = router._select_model(long_messages)
        
        # Should fallback to kimi-k2.6
        assert model == "kimi-k2.6"
    
    def test_cost_estimation(self):
        """Test cost estimation."""
        router = K2ChatRouter()
        messages = [{"role": "user", "content": "Hello world"}]  # 11 chars
        
        tokens = router._estimate_tokens(messages)
        assert tokens == 2  # 11 // 4 = 2
        
        cost = router._estimate_cost(messages, "deepseek-v4-flash")
        expected_cost = (2 / 1_000_000) * 0.60
        assert cost == expected_cost
    
    def test_stats(self):
        """Test statistics gathering."""
        router = K2ChatRouter()
        
        router.chat("Hello", session_id="stats_1")
        router.chat("World", session_id="stats_2")
        
        stats = router.get_stats()
        assert stats["active_sessions"] == 2
        assert stats["default_model"] == "deepseek-v4-flash"
        assert stats["total_messages"] == 2
    
    def test_convenience_function(self):
        """Test the route_chat convenience function."""
        result = route_chat("Hello", session_id="convenience_test")
        
        assert result["model"] == "deepseek-v4-flash"
        assert result["session_id"] == "convenience_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
