"""LLM Provider base class and factory."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.utils.config import Config


class ProviderType(Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: list[Any]
    stop_reason: str
    model: str
    usage: Optional[dict] = None


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class TextContent:
    """Represents text content from the LLM."""

    text: str
    type: str = "text"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def create_message(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Create a message/completion from the LLM.

        Args:
            messages: Conversation history
            system: System prompt
            tools: Tool definitions
            max_tokens: Maximum tokens in response

        Returns:
            Standardized LLMResponse
        """
        pass

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Check if the provider is available and configured.

        Returns:
            Tuple of (is_available, message)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get provider name."""
        pass


def get_llm_provider(config: Config) -> LLMProvider:
    """Factory function to get the appropriate LLM provider.

    Args:
        config: Application configuration

    Returns:
        Configured LLM provider instance
    """
    provider_type = ProviderType(config.llm_provider.lower())

    if provider_type == ProviderType.OLLAMA:
        from src.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            model=config.model,
            base_url=config.ollama_base_url,
        )
    elif provider_type == ProviderType.ANTHROPIC:
        from src.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=config.model,
        )
    else:
        raise ValueError(f"Unknown provider: {config.llm_provider}")
