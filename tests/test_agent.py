"""Tests for the Kubernetes agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent.core import AgentResponse, KubernetesAgent
from src.agent.memory import ConversationMemory
from src.utils.config import Config


@pytest.fixture
def mock_config():
    return Config(
        anthropic_api_key="test-api-key",
        safe_mode=True,
        dry_run=False,
        timeout=30,
        model="claude-sonnet-4-20250514",
    )


@pytest.fixture
def mock_tools():
    return [
        {
            "name": "kubectl_get",
            "description": "Get Kubernetes resources",
            "input_schema": {
                "type": "object",
                "properties": {
                    "resource": {"type": "string"},
                },
                "required": ["resource"],
            },
        }
    ]


class TestConversationMemory:
    """Tests for ConversationMemory class."""

    def test_add_user_message(self):
        memory = ConversationMemory()
        memory.add_user_message("Hello")

        messages = memory.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_add_assistant_message(self):
        memory = ConversationMemory()
        memory.add_assistant_message("Hi there!")

        messages = memory.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"

    def test_message_trimming(self):
        memory = ConversationMemory(max_messages=3)

        for i in range(5):
            memory.add_user_message(f"Message {i}")

        assert memory.message_count == 3
        messages = memory.get_messages()
        assert messages[0]["content"] == "Message 2"

    def test_clear_memory(self):
        memory = ConversationMemory()
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi")

        memory.clear()

        assert memory.message_count == 0
        assert memory.get_messages() == []

    def test_context_storage(self):
        memory = ConversationMemory()
        memory.set_context("namespace", "production")

        assert memory.get_context("namespace") == "production"
        assert memory.get_context("missing", "default") == "default"

    def test_get_last_n_messages(self):
        memory = ConversationMemory()
        for i in range(5):
            memory.add_user_message(f"Message {i}")

        last_two = memory.get_last_n_messages(2)
        assert len(last_two) == 2
        assert last_two[0]["content"] == "Message 3"
        assert last_two[1]["content"] == "Message 4"


class TestKubernetesAgent:
    """Tests for KubernetesAgent class."""

    @pytest.fixture
    def agent(self, mock_config, mock_tools):
        tool_executor = AsyncMock(return_value="Execution result")
        return KubernetesAgent(
            config=mock_config,
            tools=mock_tools,
            tool_executor=tool_executor,
        )

    @pytest.mark.asyncio
    async def test_simple_response(self, agent):
        """Test agent with a simple end_turn response."""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [MagicMock(text="Here are your pods: nginx, redis")]

        with patch.object(agent.llm, "create_message", return_value=mock_response):
            result = await agent.run("Show me all pods")

            assert result.success
            assert "nginx" in result.text
            assert result.tool_calls_made == 0

    @pytest.mark.asyncio
    async def test_tool_use_response(self, agent):
        """Test agent with tool use."""
        tool_use_response = MagicMock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_response.content = [
            MagicMock(
                type="tool_use",
                name="kubectl_get",
                input={"resource": "pods"},
                id="tool_123",
            )
        ]

        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [MagicMock(text="Here are your pods")]

        with patch.object(
            agent.llm,
            "create_message",
            side_effect=[tool_use_response, final_response],
        ):
            result = await agent.run("Show me all pods")

            assert result.success
            assert result.tool_calls_made == 1

    @pytest.mark.asyncio
    async def test_max_iterations(self, agent):
        """Test agent stops after max iterations."""
        agent.max_iterations = 2

        tool_use_response = MagicMock()
        tool_use_response.stop_reason = "tool_use"
        tool_use_response.content = [
            MagicMock(
                type="tool_use",
                name="kubectl_get",
                input={"resource": "pods"},
                id="tool_123",
            )
        ]

        with patch.object(
            agent.llm, "create_message", return_value=tool_use_response
        ):
            result = await agent.run("Complex query")

            assert not result.success
            assert "maximum" in result.text.lower()

    @pytest.mark.asyncio
    async def test_error_handling(self, agent):
        """Test agent handles errors gracefully."""
        with patch.object(
            agent.llm,
            "create_message",
            side_effect=Exception("API Error"),
        ):
            result = await agent.run("Show me pods")

            assert not result.success
            assert "error" in result.text.lower()
            assert result.error == "API Error"

    def test_reset_conversation(self, agent):
        """Test conversation reset."""
        agent.memory.add_user_message("Hello")
        agent.memory.add_assistant_message("Hi")

        agent.reset_conversation()

        assert agent.memory.message_count == 0

    def test_extract_text(self, agent):
        """Test text extraction from content blocks."""
        content = [
            MagicMock(text="First part"),
            MagicMock(text="Second part"),
        ]

        result = agent._extract_text(content)

        assert "First part" in result
        assert "Second part" in result


class TestAgentResponse:
    """Tests for AgentResponse dataclass."""

    def test_successful_response(self):
        response = AgentResponse(
            text="Success",
            tool_calls_made=2,
            success=True,
        )

        assert response.success
        assert response.tool_calls_made == 2
        assert response.error is None

    def test_error_response(self):
        response = AgentResponse(
            text="Failed",
            success=False,
            error="Connection timeout",
        )

        assert not response.success
        assert response.error == "Connection timeout"

    def test_default_values(self):
        response = AgentResponse(text="Test")

        assert response.tool_calls_made == 0
        assert response.success is True
        assert response.error is None
