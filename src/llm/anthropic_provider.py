"""Anthropic Claude LLM provider."""

from typing import Any

from src.llm.providers import LLMProvider, LLMResponse
from src.utils.logger import get_logger


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider for premium API access."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (claude-sonnet-4-20250514, etc.)
        """
        self.api_key = api_key
        self.model = model
        self.logger = get_logger("anthropic")
        self._client = None

    @property
    def client(self):
        """Lazy load the Anthropic client."""
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self.api_key)
        return self._client

    @property
    def name(self) -> str:
        return f"Anthropic ({self.model})"

    def is_available(self) -> tuple[bool, str]:
        """Check if Anthropic API is configured."""
        if not self.api_key:
            return False, "ANTHROPIC_API_KEY not set"

        if not self.api_key.startswith("sk-ant-"):
            return False, "Invalid Anthropic API key format"

        return True, f"Anthropic ready with model {self.model}"

    def create_message(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Create a message using Claude API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )

        return LLMResponse(
            content=response.content,
            stop_reason=response.stop_reason,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
