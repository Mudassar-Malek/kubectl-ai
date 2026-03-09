"""Conversation memory management for the agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """A single message in the conversation."""

    role: str  # "user" or "assistant"
    content: Any  # str or list of content blocks
    timestamp: datetime = field(default_factory=datetime.now)


class ConversationMemory:
    """Manages conversation history for the agent.

    Implements a sliding window with summarization support for long conversations.
    """

    def __init__(self, max_messages: int = 50):
        """Initialize conversation memory.

        Args:
            max_messages: Maximum number of messages to retain
        """
        self.messages: list[Message] = []
        self.max_messages = max_messages
        self.context_info: dict[str, Any] = {}

    def add_message(self, role: str, content: Any) -> None:
        """Add a message to the conversation history."""
        self.messages.append(Message(role=role, content=content))
        self._trim_if_needed()

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self.add_message("user", content)

    def add_assistant_message(self, content: Any) -> None:
        """Add an assistant message (can be string or content blocks)."""
        self.add_message("assistant", content)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get messages in Claude API format."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def get_last_n_messages(self, n: int) -> list[dict[str, Any]]:
        """Get the last n messages."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages[-n:]]

    def clear(self) -> None:
        """Clear all conversation history."""
        self.messages.clear()
        self.context_info.clear()

    def set_context(self, key: str, value: Any) -> None:
        """Store context information (current namespace, cluster, etc.)."""
        self.context_info[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Retrieve stored context information."""
        return self.context_info.get(key, default)

    def _trim_if_needed(self) -> None:
        """Trim old messages if we exceed the limit."""
        if len(self.messages) > self.max_messages:
            excess = len(self.messages) - self.max_messages
            self.messages = self.messages[excess:]

    @property
    def message_count(self) -> int:
        """Get the current number of messages."""
        return len(self.messages)

    def get_summary(self) -> str:
        """Get a summary of the conversation for context."""
        if not self.messages:
            return "No previous conversation."

        user_queries = [
            msg.content for msg in self.messages if msg.role == "user" and isinstance(msg.content, str)
        ]
        
        if not user_queries:
            return "No user queries in history."

        recent = user_queries[-3:] if len(user_queries) > 3 else user_queries
        return f"Recent topics: {', '.join(recent[:50] for q in recent)}"
