"""Ollama LLM provider - Free, local LLM support."""

import json
import re
import uuid
from typing import Any, Optional

import requests

from src.llm.providers import LLMProvider, LLMResponse, TextContent, ToolCall
from src.utils.logger import get_logger


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference.

    Supports running models like Llama 3, Mistral, Qwen, etc. locally
    with no API key required.
    
    Uses a prompt-based approach for tool calling that works reliably
    with all models.
    """

    RECOMMENDED_MODELS = [
        "llama3.1:8b",
        "llama3.2:3b",
        "mistral:7b",
        "qwen2.5:7b",
        "gemma2:9b",
    ]

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
    ):
        """Initialize Ollama provider."""
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.logger = get_logger("ollama")

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    def is_available(self) -> tuple[bool, str]:
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False, f"Ollama server returned status {response.status_code}"

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            model_base = self.model.split(":")[0]
            if not any(model_base in name for name in model_names):
                return False, (
                    f"Model '{self.model}' not found. "
                    f"Run: ollama pull {self.model}"
                )

            return True, f"Ollama ready with model {self.model}"

        except requests.ConnectionError:
            return False, (
                "Cannot connect to Ollama. "
                "Start it with: ollama serve"
            )
        except Exception as e:
            return False, f"Ollama error: {str(e)}"

    def create_message(
        self,
        messages: list[dict[str, Any]],
        system: str,
        tools: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Create a message using Ollama's chat API."""
        
        # Build enhanced system prompt with tool instructions
        enhanced_system = self._build_system_with_tools(system, tools)
        
        # Convert messages to Ollama format
        ollama_messages = self._convert_messages(messages)

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": enhanced_system}] + ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
            },
        }

        self.logger.debug(f"Ollama request to {self.model}")

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            return self._parse_response(result, tools)
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ollama request failed: {e}")
            raise

    def _build_system_with_tools(self, system: str, tools: list[dict[str, Any]]) -> str:
        """Build system prompt with tool calling instructions."""
        tool_descriptions = []
        for tool in tools:
            params = tool.get("input_schema", {}).get("properties", {})
            required = tool.get("input_schema", {}).get("required", [])
            param_strs = []
            for name, info in params.items():
                req = "(required)" if name in required else "(optional)"
                param_strs.append(f"    - {name}: {info.get('description', '')} {req}")
            
            tool_descriptions.append(
                f"- {tool['name']}: {tool['description']}\n" + 
                "  Parameters:\n" + "\n".join(param_strs)
            )

        tool_section = """

## Available Tools

You have access to the following tools to interact with Kubernetes:

""" + "\n\n".join(tool_descriptions) + """

## How to Use Tools

CRITICAL: You MUST use tools to get real data. NEVER make up or invent Kubernetes data.

When asked about pods, deployments, services, or ANY Kubernetes resources:
1. ALWAYS call a tool first to get REAL data
2. NEVER invent pod names, statuses, or any cluster information
3. If you don't call a tool, you are LYING to the user

Respond with ONLY a JSON block in this exact format:
```json
{"tool": "tool_name", "arguments": {"param1": "value1", "param2": "value2"}}
```

RULES:
1. Use ONLY ONE tool call per response
2. The JSON must be valid and properly formatted
3. After seeing tool results, show the ACTUAL results to the user - do NOT make up data
4. NEVER invent fake pod names like "my-nginx" or "example-pod"

Example - when user asks "show me all pods":
```json
{"tool": "kubectl_get", "arguments": {"resource": "pods"}}
```
"""
        return system + tool_section

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert messages to Ollama format."""
        ollama_messages = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                ollama_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle structured content
                text_parts = []
                
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_result":
                            # Format tool results clearly
                            tool_content = block.get("content", "")
                            text_parts.append(f"Tool Result:\n{tool_content}")
                        elif block.get("type") == "tool_use":
                            # Show what tool was called
                            name = block.get("name", "")
                            args = block.get("input", {})
                            text_parts.append(f'```json\n{{"tool": "{name}", "arguments": {json.dumps(args)}}}\n```')
                    elif hasattr(block, "type"):
                        if block.type == "text":
                            text_parts.append(block.text)
                        elif block.type == "tool_use":
                            text_parts.append(f'```json\n{{"tool": "{block.name}", "arguments": {json.dumps(block.input)}}}\n```')

                if text_parts:
                    combined = "\n\n".join(text_parts)
                    ollama_messages.append({"role": role, "content": combined})

        return ollama_messages

    def _parse_response(self, result: dict[str, Any], tools: list[dict[str, Any]]) -> LLMResponse:
        """Parse Ollama response into standardized format."""
        message = result.get("message", {})
        text_content = message.get("content", "")
        content_list = []
        stop_reason = "end_turn"

        # Try to extract tool call from the response
        tool_call = self._extract_tool_call(text_content, tools)
        
        if tool_call:
            content_list.append(tool_call)
            stop_reason = "tool_use"
        else:
            # Clean up the response (remove any partial JSON blocks)
            clean_text = self._clean_response(text_content)
            content_list.append(TextContent(text=clean_text))

        return LLMResponse(
            content=content_list,
            stop_reason=stop_reason,
            model=self.model,
            usage=result.get("usage"),
        )

    def _extract_tool_call(self, text: str, tools: list[dict[str, Any]]) -> Optional[ToolCall]:
        """Extract tool call from response text."""
        tool_names = {t["name"] for t in tools}

        # Look for JSON blocks
        patterns = [
            r'```json\s*(\{[^`]+\})\s*```',
            r'```\s*(\{[^`]+\})\s*```',
            r'(\{"tool":\s*"[^"]+",\s*"arguments":\s*\{[^}]+\}\})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    tool_name = data.get("tool")
                    arguments = data.get("arguments", {})
                    
                    if tool_name and tool_name in tool_names:
                        return ToolCall(
                            id=str(uuid.uuid4()),
                            name=tool_name,
                            input=arguments,
                        )
                except json.JSONDecodeError:
                    continue

        return None

    def _clean_response(self, text: str) -> str:
        """Clean up response text by removing incomplete JSON blocks."""
        # Remove any JSON code blocks that might be partial tool calls
        text = re.sub(r'```json\s*\{[^`]*$', '', text, flags=re.DOTALL)
        text = re.sub(r'```\s*\{[^`]*$', '', text, flags=re.DOTALL)
        return text.strip()
