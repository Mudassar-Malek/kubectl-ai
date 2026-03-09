"""Command validation and safety checks for kubectl operations."""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """Risk level for kubectl commands."""

    SAFE = "safe"  # Read-only operations
    MODERATE = "moderate"  # Modifications that can be recovered
    DANGEROUS = "dangerous"  # Potentially destructive operations
    CRITICAL = "critical"  # Highly destructive, hard to recover


@dataclass
class ValidationResult:
    """Result of command validation."""

    is_valid: bool
    risk_level: RiskLevel
    requires_confirmation: bool
    message: Optional[str] = None
    sanitized_command: Optional[str] = None


class CommandValidator:
    """Validates and sanitizes kubectl commands."""

    SAFE_COMMANDS = {
        "get",
        "describe",
        "logs",
        "top",
        "explain",
        "api-resources",
        "api-versions",
        "cluster-info",
        "version",
        "config view",
        "config get-contexts",
        "config current-context",
    }

    MODERATE_COMMANDS = {
        "scale",
        "label",
        "annotate",
        "rollout status",
        "rollout history",
        "exec",
        "port-forward",
        "cp",
    }

    DANGEROUS_COMMANDS = {
        "apply",
        "create",
        "patch",
        "replace",
        "rollout restart",
        "rollout undo",
        "config use-context",
        "config set-context",
    }

    CRITICAL_COMMANDS = {
        "delete",
        "drain",
        "cordon",
        "taint",
        "edit",
    }

    BLOCKED_PATTERNS = [
        r";\s*",  # Command chaining
        r"\|\s*",  # Piping
        r"&&",  # AND operator
        r"\|\|",  # OR operator
        r"\$\(",  # Command substitution
        r"`",  # Backtick substitution
        r">\s*",  # Output redirection
        r"<\s*",  # Input redirection
    ]

    DANGEROUS_RESOURCES = {
        "namespace",
        "ns",
        "node",
        "nodes",
        "clusterrole",
        "clusterrolebinding",
        "persistentvolume",
        "pv",
    }

    def validate_command(self, command: str, safe_mode: bool = True) -> ValidationResult:
        """Validate a kubectl command for safety.

        Args:
            command: The kubectl command to validate
            safe_mode: Whether to require confirmation for dangerous ops

        Returns:
            ValidationResult with validation status and risk assessment
        """
        if not command.strip():
            return ValidationResult(
                is_valid=False,
                risk_level=RiskLevel.SAFE,
                requires_confirmation=False,
                message="Empty command",
            )

        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command):
                return ValidationResult(
                    is_valid=False,
                    risk_level=RiskLevel.CRITICAL,
                    requires_confirmation=False,
                    message=f"Blocked pattern detected: {pattern}",
                )

        risk_level = self._assess_risk(command)
        requires_confirmation = safe_mode and risk_level in (
            RiskLevel.DANGEROUS,
            RiskLevel.CRITICAL,
        )

        return ValidationResult(
            is_valid=True,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            sanitized_command=command.strip(),
        )

    def _assess_risk(self, command: str) -> RiskLevel:
        """Assess the risk level of a command."""
        command_lower = command.lower()

        for cmd in self.CRITICAL_COMMANDS:
            if cmd in command_lower:
                if any(res in command_lower for res in self.DANGEROUS_RESOURCES):
                    return RiskLevel.CRITICAL
                return RiskLevel.CRITICAL

        for cmd in self.DANGEROUS_COMMANDS:
            if cmd in command_lower:
                return RiskLevel.DANGEROUS

        for cmd in self.MODERATE_COMMANDS:
            if cmd in command_lower:
                return RiskLevel.MODERATE

        for cmd in self.SAFE_COMMANDS:
            if cmd in command_lower:
                return RiskLevel.SAFE

        return RiskLevel.MODERATE

    def validate_resource_name(self, name: str) -> bool:
        """Validate a Kubernetes resource name."""
        if not name:
            return False
        pattern = r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$"
        return bool(re.match(pattern, name)) and len(name) <= 253

    def validate_namespace(self, namespace: str) -> bool:
        """Validate a namespace name."""
        return self.validate_resource_name(namespace)

    def validate_label_selector(self, selector: str) -> bool:
        """Validate a label selector."""
        if not selector:
            return True
        pattern = r"^[a-zA-Z0-9_\-./]+(=[a-zA-Z0-9_\-./]+)?(,[a-zA-Z0-9_\-./]+(=[a-zA-Z0-9_\-./]+)?)*$"
        return bool(re.match(pattern, selector))


def get_risk_emoji(risk_level: RiskLevel) -> str:
    """Get an emoji indicator for risk level."""
    return {
        RiskLevel.SAFE: "",
        RiskLevel.MODERATE: "",
        RiskLevel.DANGEROUS: "",
        RiskLevel.CRITICAL: "",
    }.get(risk_level, "")


def get_risk_description(risk_level: RiskLevel) -> str:
    """Get a human-readable description of risk level."""
    return {
        RiskLevel.SAFE: "Read-only operation",
        RiskLevel.MODERATE: "May modify non-critical state",
        RiskLevel.DANGEROUS: "Will modify cluster resources",
        RiskLevel.CRITICAL: "Potentially destructive operation",
    }.get(risk_level, "Unknown risk")
