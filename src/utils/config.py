"""Configuration management for K8s IntelliBot."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # LLM Provider settings
    llm_provider: str = "ollama"  # "ollama" (free) or "anthropic" (paid)
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    model: str = ""  # Auto-set based on provider

    # Bot settings
    safe_mode: bool = True
    dry_run: bool = False
    confirm_commands: bool = False  # Show command and ask approval before executing
    timeout: int = 30
    log_level: str = "INFO"
    kubeconfig: str = field(default_factory=lambda: str(Path.home() / ".kube" / "config"))

    # Slack configuration (optional)
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None

    def __post_init__(self):
        """Set default model based on provider if not specified."""
        if not self.model:
            if self.llm_provider == "ollama":
                self.model = "llama3.1:8b"
            else:
                self.model = "claude-sonnet-4-20250514"

    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file. If not provided,
                     looks for .env in current directory.
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Determine default provider based on available keys
        default_provider = "ollama"
        if os.getenv("ANTHROPIC_API_KEY"):
            default_provider = "anthropic"

        return cls(
            llm_provider=os.getenv("LLM_PROVIDER", default_provider).lower(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("K8S_BOT_MODEL", ""),
            safe_mode=os.getenv("K8S_BOT_SAFE_MODE", "true").lower() == "true",
            dry_run=os.getenv("K8S_BOT_DRY_RUN", "false").lower() == "true",
            confirm_commands=os.getenv("K8S_BOT_CONFIRM_COMMANDS", "false").lower() == "true",
            timeout=int(os.getenv("K8S_BOT_TIMEOUT", "30")),
            log_level=os.getenv("K8S_BOT_LOG_LEVEL", "INFO").upper(),
            kubeconfig=os.getenv("KUBECONFIG", str(Path.home() / ".kube" / "config")),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
            slack_app_token=os.getenv("SLACK_APP_TOKEN"),
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET"),
        )

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Validate provider-specific requirements
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic provider")

        if not Path(os.path.expanduser(self.kubeconfig)).exists():
            errors.append(f"Kubeconfig not found at: {self.kubeconfig}")

        if self.timeout < 1:
            errors.append("K8S_BOT_TIMEOUT must be at least 1 second")

        return errors

    @property
    def has_slack_config(self) -> bool:
        """Check if Slack integration is configured."""
        return bool(self.slack_bot_token and self.slack_app_token)

    @property
    def is_using_ollama(self) -> bool:
        """Check if using Ollama (free local LLM)."""
        return self.llm_provider == "ollama"
