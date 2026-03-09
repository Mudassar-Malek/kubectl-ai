"""Output parsing and formatting for kubectl results."""

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

import yaml


@dataclass
class ParsedOutput:
    """Parsed kubectl output."""

    raw: str
    formatted: str
    data: Optional[Any] = None
    is_error: bool = False
    error_type: Optional[str] = None


class OutputParser:
    """Parses and formats kubectl command output."""

    ERROR_PATTERNS = {
        r"error:": "general_error",
        r"Error from server": "server_error",
        r"NotFound": "not_found",
        r"Forbidden": "forbidden",
        r"Unable to connect": "connection_error",
        r"no matches for kind": "invalid_resource",
        r"the server doesn't have a resource type": "invalid_resource",
        r"timeout": "timeout",
    }

    def parse(self, output: str, output_format: Optional[str] = None) -> ParsedOutput:
        """Parse kubectl output.

        Args:
            output: Raw command output
            output_format: Expected format (json, yaml, or table)

        Returns:
            ParsedOutput with formatted data
        """
        if not output.strip():
            return ParsedOutput(
                raw=output,
                formatted="No output returned.",
                is_error=False,
            )

        error_type = self._detect_error(output)
        if error_type:
            return ParsedOutput(
                raw=output,
                formatted=self._format_error(output),
                is_error=True,
                error_type=error_type,
            )

        if output_format == "json":
            return self._parse_json(output)
        elif output_format == "yaml":
            return self._parse_yaml(output)
        else:
            return self._parse_table(output)

    def _detect_error(self, output: str) -> Optional[str]:
        """Detect if output contains an error."""
        for pattern, error_type in self.ERROR_PATTERNS.items():
            if re.search(pattern, output, re.IGNORECASE):
                return error_type
        return None

    def _format_error(self, output: str) -> str:
        """Format error output for display."""
        lines = output.strip().split("\n")
        formatted_lines = []
        for line in lines:
            if any(re.search(p, line, re.IGNORECASE) for p in self.ERROR_PATTERNS):
                formatted_lines.append(f"[ERROR] {line}")
            else:
                formatted_lines.append(line)
        return "\n".join(formatted_lines)

    def _parse_json(self, output: str) -> ParsedOutput:
        """Parse JSON output."""
        try:
            data = json.loads(output)
            formatted = json.dumps(data, indent=2)
            return ParsedOutput(
                raw=output,
                formatted=formatted,
                data=data,
            )
        except json.JSONDecodeError as e:
            return ParsedOutput(
                raw=output,
                formatted=f"Failed to parse JSON: {e}\n{output}",
                is_error=True,
                error_type="parse_error",
            )

    def _parse_yaml(self, output: str) -> ParsedOutput:
        """Parse YAML output."""
        try:
            data = yaml.safe_load(output)
            formatted = yaml.dump(data, default_flow_style=False)
            return ParsedOutput(
                raw=output,
                formatted=formatted,
                data=data,
            )
        except yaml.YAMLError as e:
            return ParsedOutput(
                raw=output,
                formatted=f"Failed to parse YAML: {e}\n{output}",
                is_error=True,
                error_type="parse_error",
            )

    def _parse_table(self, output: str) -> ParsedOutput:
        """Parse table output (default kubectl format)."""
        lines = output.strip().split("\n")
        if not lines:
            return ParsedOutput(raw=output, formatted=output)

        formatted_lines = [lines[0]]
        formatted_lines.append("-" * len(lines[0]))
        formatted_lines.extend(lines[1:])

        return ParsedOutput(
            raw=output,
            formatted="\n".join(formatted_lines),
        )

    def extract_resource_status(self, output: str, resource_type: str) -> dict[str, Any]:
        """Extract status information from kubectl get output."""
        status = {
            "resource_type": resource_type,
            "items": [],
            "summary": {},
        }

        lines = output.strip().split("\n")
        if len(lines) < 2:
            return status

        headers = lines[0].split()
        for line in lines[1:]:
            values = line.split()
            if len(values) >= len(headers):
                item = dict(zip(headers, values))
                status["items"].append(item)

        if resource_type in ("pods", "pod"):
            status["summary"] = self._summarize_pods(status["items"])
        elif resource_type in ("deployments", "deployment", "deploy"):
            status["summary"] = self._summarize_deployments(status["items"])

        return status

    def _summarize_pods(self, items: list[dict]) -> dict[str, int]:
        """Summarize pod statuses."""
        summary = {"total": len(items), "running": 0, "pending": 0, "failed": 0, "other": 0}
        for item in items:
            status = item.get("STATUS", "").lower()
            if status == "running":
                summary["running"] += 1
            elif status == "pending":
                summary["pending"] += 1
            elif status in ("failed", "error", "crashloopbackoff"):
                summary["failed"] += 1
            else:
                summary["other"] += 1
        return summary

    def _summarize_deployments(self, items: list[dict]) -> dict[str, int]:
        """Summarize deployment statuses."""
        summary = {"total": len(items), "healthy": 0, "degraded": 0}
        for item in items:
            ready = item.get("READY", "0/0")
            if "/" in ready:
                current, desired = ready.split("/")
                if current == desired and int(current) > 0:
                    summary["healthy"] += 1
                else:
                    summary["degraded"] += 1
        return summary


def format_resource_table(data: list[dict], columns: Optional[list[str]] = None) -> str:
    """Format a list of resources as a table."""
    if not data:
        return "No resources found."

    if columns is None:
        columns = list(data[0].keys())

    col_widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            val = str(row.get(col, ""))
            col_widths[col] = max(col_widths[col], len(val))

    header = "  ".join(col.upper().ljust(col_widths[col]) for col in columns)
    separator = "  ".join("-" * col_widths[col] for col in columns)
    rows = []
    for row in data:
        row_str = "  ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in columns)
        rows.append(row_str)

    return "\n".join([header, separator] + rows)
