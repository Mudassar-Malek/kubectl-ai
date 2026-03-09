"""Core agentic AI implementation with multi-provider LLM support."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional

from rich.console import Console

from src.agent.memory import ConversationMemory
from src.agent.prompts import SYSTEM_PROMPT
from src.llm.providers import LLMProvider, get_llm_provider
from src.utils.config import Config
from src.utils.logger import get_logger


@dataclass
class AgentResponse:
    """Response from the agent."""

    text: str
    tool_calls_made: int = 0
    success: bool = True
    error: Optional[str] = None


class KubernetesAgent:
    """Agentic AI for Kubernetes operations.

    Supports multiple LLM providers:
    - Ollama (free, local) - default
    - Anthropic Claude (paid API)

    Implements a ReAct-style agent loop that can:
    - Understand natural language queries
    - Execute multiple tool calls autonomously
    - Reason about results and take follow-up actions
    - Maintain conversation context
    """

    def __init__(
        self,
        config: Config,
        tools: list[dict[str, Any]],
        tool_executor: Callable[[str, dict[str, Any]], Any],
        console: Optional[Console] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize the Kubernetes agent.

        Args:
            config: Application configuration
            tools: List of tool definitions in Claude format
            tool_executor: Function to execute tool calls
            console: Rich console for output
            llm_provider: Optional custom LLM provider (auto-detected if not provided)
        """
        self.config = config
        self.llm = llm_provider or get_llm_provider(config)
        self.tools = tools
        self.tool_executor = tool_executor
        self.memory = ConversationMemory()
        self.console = console or Console()
        self.logger = get_logger("agent")
        self.max_iterations = 10

    async def run(self, user_query: str) -> AgentResponse:
        """Process a user query through the agentic loop.

        Args:
            user_query: Natural language query from the user

        Returns:
            AgentResponse with the final text response
        """
        self.memory.add_user_message(user_query)
        messages = self.memory.get_messages()
        tool_calls_made = 0

        try:
            for iteration in range(self.max_iterations):
                self.logger.debug(f"Agent iteration {iteration + 1} using {self.llm.name}")

                response = self.llm.create_message(
                    messages=messages,
                    system=SYSTEM_PROMPT,
                    tools=self.tools,
                    max_tokens=4096,
                )

                if response.stop_reason == "end_turn":
                    final_text = self._extract_text(response.content)
                    self.memory.add_assistant_message(response.content)
                    return AgentResponse(
                        text=final_text,
                        tool_calls_made=tool_calls_made,
                        success=True,
                    )

                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = await self._execute_tool_calls(response.content)
                    tool_calls_made += len(tool_results)

                    messages.append({"role": "user", "content": tool_results})
                else:
                    self.logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                    break

            return AgentResponse(
                text="I've reached the maximum number of steps. Please try a more specific query.",
                tool_calls_made=tool_calls_made,
                success=False,
                error="max_iterations_reached",
            )

        except Exception as e:
            self.logger.error(f"Agent error: {e}")
            return AgentResponse(
                text=f"An error occurred: {str(e)}",
                tool_calls_made=tool_calls_made,
                success=False,
                error=str(e),
            )

    async def _execute_tool_calls(
        self, content: list[Any]
    ) -> list[dict[str, Any]]:
        """Execute all tool calls in the response content.

        Args:
            content: Response content containing tool use blocks

        Returns:
            List of tool result blocks for the next message
        """
        results = []

        for block in content:
            # Handle both object-style (Anthropic) and our ToolCall dataclass (Ollama)
            block_type = getattr(block, "type", None) or (
                block.get("type") if isinstance(block, dict) else None
            )

            if block_type == "tool_use":
                tool_name = getattr(block, "name", None) or block.get("name")
                tool_input = getattr(block, "input", None) or block.get("input", {})
                tool_id = getattr(block, "id", None) or block.get("id")

                self.logger.info(f"Executing tool: {tool_name}")
                self.logger.debug(f"Tool input: {tool_input}")

                try:
                    result = await self._run_tool(tool_name, tool_input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(result),
                    })
                except Exception as e:
                    self.logger.error(f"Tool execution failed: {e}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error executing {tool_name}: {str(e)}",
                        "is_error": True,
                    })

        return results

    async def _run_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Run a single tool and return its result.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if asyncio.iscoroutinefunction(self.tool_executor):
            return await self.tool_executor(name, arguments)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.tool_executor, name, arguments)

    def _extract_text(self, content: list[Any]) -> str:
        """Extract text content from response blocks.

        Args:
            content: List of content blocks

        Returns:
            Concatenated text content
        """
        text_parts = []
        for block in content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        return "\n".join(text_parts)

    def reset_conversation(self) -> None:
        """Clear conversation history and start fresh."""
        self.memory.clear()
        self.logger.info("Conversation reset")

    def get_conversation_summary(self) -> str:
        """Get a summary of the current conversation."""
        return self.memory.get_summary()
