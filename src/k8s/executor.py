"""Safe kubectl command execution with validation and timeout handling."""

import asyncio
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from src.k8s.parser import OutputParser, ParsedOutput
from src.k8s.validators import CommandValidator, RiskLevel, ValidationResult
from src.utils.config import Config
from src.utils.logger import get_logger


@dataclass
class ExecutionResult:
    """Result of a kubectl command execution."""

    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = 0
    execution_time_ms: int = 0
    command: str = ""
    was_dry_run: bool = False
    parsed: Optional[ParsedOutput] = None
    validation: Optional[ValidationResult] = None


@dataclass
class ConfirmationRequest:
    """Request for user confirmation before executing dangerous commands."""

    command: str
    risk_level: RiskLevel
    description: str
    resources_affected: list[str] = field(default_factory=list)


class KubectlExecutor:
    """Executes kubectl commands with safety guardrails.

    Features:
    - Command validation and sanitization
    - Risk assessment and confirmation for dangerous operations
    - Timeout handling
    - Dry-run support
    - Output parsing
    """

    def __init__(
        self,
        config: Config,
        confirmation_handler: Optional[Callable[[ConfirmationRequest], bool]] = None,
    ):
        """Initialize the executor.

        Args:
            config: Application configuration
            confirmation_handler: Callback for confirming dangerous operations
        """
        self.config = config
        self.validator = CommandValidator()
        self.parser = OutputParser()
        self.logger = get_logger("executor")
        self.confirmation_handler = confirmation_handler or self._default_confirmation
        self._pending_confirmation: Optional[ConfirmationRequest] = None

    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        dry_run: Optional[bool] = None,
        skip_validation: bool = False,
        output_format: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute a kubectl command safely.

        Args:
            command: The kubectl command (without 'kubectl' prefix)
            timeout: Command timeout in seconds (defaults to config)
            dry_run: Force dry-run mode
            skip_validation: Skip validation (not recommended)
            output_format: Expected output format for parsing

        Returns:
            ExecutionResult with output and status
        """
        timeout = timeout or self.config.timeout
        dry_run = dry_run if dry_run is not None else self.config.dry_run

        if not skip_validation:
            validation = self.validator.validate_command(command, self.config.safe_mode)
            if not validation.is_valid:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=validation.message,
                    command=command,
                    validation=validation,
                )

            if validation.requires_confirmation:
                confirmed = await self._request_confirmation(command, validation.risk_level)
                if not confirmed:
                    return ExecutionResult(
                        success=False,
                        output="",
                        error="Operation cancelled by user",
                        command=command,
                        validation=validation,
                    )
        else:
            validation = None

        full_command = self._build_command(command, dry_run)
        
        # Pre-hook: Show command and ask for approval if enabled
        if self.config.confirm_commands:
            confirmed = await self._request_command_approval(full_command)
            if not confirmed:
                return ExecutionResult(
                    success=False,
                    output="",
                    error="Command not approved by user",
                    command=full_command,
                    validation=validation,
                )
        self.logger.debug(f"Executing: {full_command}")

        start_time = datetime.now()
        try:
            result = await self._run_subprocess(full_command, timeout)
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            parsed = self.parser.parse(result.output, output_format)

            return ExecutionResult(
                success=result.exit_code == 0,
                output=result.output,
                error=result.error if result.exit_code != 0 else None,
                exit_code=result.exit_code,
                execution_time_ms=execution_time,
                command=full_command,
                was_dry_run=dry_run,
                parsed=parsed,
                validation=validation,
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout} seconds",
                command=full_command,
                validation=validation,
            )
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                command=full_command,
                validation=validation,
            )

    def _build_command(self, command: str, dry_run: bool) -> str:
        """Build the full kubectl command."""
        parts = ["kubectl"]

        kubeconfig = os.path.expanduser(self.config.kubeconfig)
        if kubeconfig and os.path.exists(kubeconfig):
            parts.append(f"--kubeconfig={kubeconfig}")

        parts.append(command)

        if dry_run and not any(x in command for x in ["get", "describe", "logs", "explain"]):
            if "apply" in command or "create" in command:
                parts.append("--dry-run=client")
            elif "delete" in command:
                parts.append("--dry-run=client")

        return " ".join(parts)

    async def _run_subprocess(self, command: str, timeout: int) -> "SubprocessResult":
        """Run a subprocess with timeout."""
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            return SubprocessResult(
                output=stdout.decode("utf-8", errors="replace"),
                error=stderr.decode("utf-8", errors="replace") if stderr else None,
                exit_code=process.returncode or 0,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise

    async def _request_confirmation(self, command: str, risk_level: RiskLevel) -> bool:
        """Request user confirmation for dangerous operations."""
        request = ConfirmationRequest(
            command=command,
            risk_level=risk_level,
            description=f"This {risk_level.value} operation requires confirmation",
        )
        self._pending_confirmation = request

        if asyncio.iscoroutinefunction(self.confirmation_handler):
            return await self.confirmation_handler(request)
        return self.confirmation_handler(request)

    async def _request_command_approval(self, full_command: str) -> bool:
        """Show command to user and request approval before execution.
        
        This is the pre-hook that displays the exact command and asks for approval.
        """
        request = ConfirmationRequest(
            command=full_command,
            risk_level=RiskLevel.SAFE,
            description="Command to execute",
        )
        
        if asyncio.iscoroutinefunction(self.confirmation_handler):
            return await self.confirmation_handler(request)
        return self.confirmation_handler(request)

    def _default_confirmation(self, request: ConfirmationRequest) -> bool:
        """Default confirmation handler - always returns True in non-interactive mode."""
        self.logger.warning(f"Auto-confirming {request.risk_level.value} operation: {request.command}")
        return True

    def set_confirmation_handler(self, handler: Callable[[ConfirmationRequest], bool]) -> None:
        """Set a custom confirmation handler."""
        self.confirmation_handler = handler


@dataclass
class SubprocessResult:
    """Result from subprocess execution."""

    output: str
    error: Optional[str]
    exit_code: int


class ToolExecutor:
    """Executes kubectl tools called by the agent."""

    def __init__(self, kubectl_executor: KubectlExecutor, context_manager: Any):
        """Initialize the tool executor.

        Args:
            kubectl_executor: KubectlExecutor instance
            context_manager: ContextManager instance
        """
        self.kubectl = kubectl_executor
        self.context_manager = context_manager
        self.logger = get_logger("tool_executor")

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return its result.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            String result for the agent
        """
        handler = getattr(self, f"_handle_{tool_name}", None)
        if handler is None:
            return f"Unknown tool: {tool_name}"

        try:
            return await handler(arguments)
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_name} - {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def _handle_kubectl_get(self, args: dict) -> str:
        resource = args["resource"]
        name = args.get("name", "")
        namespace = args.get("namespace", "")
        selector = args.get("selector", "")
        output = args.get("output", "")

        cmd_parts = ["get", resource]
        if name:
            cmd_parts.append(name)
        if namespace == "all":
            cmd_parts.append("--all-namespaces")
        elif namespace:
            cmd_parts.extend(["-n", namespace])
        if selector:
            cmd_parts.extend(["-l", selector])
        if output:
            cmd_parts.extend(["-o", output])

        result = await self.kubectl.execute(" ".join(cmd_parts), output_format=output or None)
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_describe(self, args: dict) -> str:
        resource = args["resource"]
        name = args["name"]
        namespace = args.get("namespace", "")

        cmd_parts = ["describe", resource, name]
        if namespace:
            cmd_parts.extend(["-n", namespace])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_logs(self, args: dict) -> str:
        pod = args["pod"]
        namespace = args.get("namespace", "")
        container = args.get("container", "")
        tail = args.get("tail", 100)
        since = args.get("since", "")
        previous = args.get("previous", False)

        cmd_parts = ["logs", pod]
        if namespace:
            cmd_parts.extend(["-n", namespace])
        if container:
            cmd_parts.extend(["-c", container])
        cmd_parts.extend(["--tail", str(tail)])
        if since:
            cmd_parts.extend(["--since", since])
        if previous:
            cmd_parts.append("--previous")

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_get_events(self, args: dict) -> str:
        namespace = args.get("namespace", "")
        field_selector = args.get("field_selector", "")

        cmd_parts = ["get", "events", "--sort-by=.lastTimestamp"]
        if namespace == "all":
            cmd_parts.append("--all-namespaces")
        elif namespace:
            cmd_parts.extend(["-n", namespace])
        if field_selector:
            cmd_parts.extend(["--field-selector", field_selector])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_top(self, args: dict) -> str:
        resource = args["resource"]
        namespace = args.get("namespace", "")
        name = args.get("name", "")

        cmd_parts = ["top", resource]
        if name:
            cmd_parts.append(name)
        if namespace == "all" and resource == "pods":
            cmd_parts.append("--all-namespaces")
        elif namespace:
            cmd_parts.extend(["-n", namespace])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_scale(self, args: dict) -> str:
        resource = args["resource"]
        name = args["name"]
        replicas = args["replicas"]
        namespace = args.get("namespace", "")

        cmd_parts = ["scale", f"{resource}/{name}", f"--replicas={replicas}"]
        if namespace:
            cmd_parts.extend(["-n", namespace])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_rollout(self, args: dict) -> str:
        action = args["action"]
        resource = args["resource"]
        name = args["name"]
        namespace = args.get("namespace", "")
        revision = args.get("revision")

        cmd_parts = ["rollout", action, f"{resource}/{name}"]
        if namespace:
            cmd_parts.extend(["-n", namespace])
        if action == "undo" and revision:
            cmd_parts.extend([f"--to-revision={revision}"])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_exec(self, args: dict) -> str:
        pod = args["pod"]
        command = args["command"]
        namespace = args.get("namespace", "")
        container = args.get("container", "")

        cmd_parts = ["exec", pod]
        if namespace:
            cmd_parts.extend(["-n", namespace])
        if container:
            cmd_parts.extend(["-c", container])
        cmd_parts.extend(["--", *shlex.split(command)])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_apply(self, args: dict) -> str:
        manifest = args["manifest"]
        namespace = args.get("namespace", "")
        dry_run = args.get("dry_run", False)

        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(manifest)
            manifest_path = f.name

        try:
            cmd_parts = ["apply", "-f", manifest_path]
            if namespace:
                cmd_parts.extend(["-n", namespace])

            result = await self.kubectl.execute(" ".join(cmd_parts), dry_run=dry_run)
            return result.output if result.success else f"Error: {result.error}"
        finally:
            os.unlink(manifest_path)

    async def _handle_kubectl_delete(self, args: dict) -> str:
        resource = args["resource"]
        name = args.get("name", "")
        namespace = args.get("namespace", "")
        selector = args.get("selector", "")
        force = args.get("force", False)

        cmd_parts = ["delete", resource]
        if name:
            cmd_parts.append(name)
        if namespace:
            cmd_parts.extend(["-n", namespace])
        if selector:
            cmd_parts.extend(["-l", selector])
        if force:
            cmd_parts.extend(["--grace-period=0", "--force"])

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_list_contexts(self, args: dict) -> str:
        contexts = self.context_manager.list_contexts()
        current = self.context_manager.get_current_context()

        lines = ["Available Kubernetes Contexts:", ""]
        for ctx in contexts:
            marker = "*" if ctx.name == current.name else " "
            platform = self.context_manager.detect_platform(ctx.name)
            lines.append(f"  {marker} {ctx.name} ({platform.value}) - Cluster: {ctx.cluster}")

        return "\n".join(lines)

    async def _handle_switch_context(self, args: dict) -> str:
        context_name = args["context_name"]
        success = self.context_manager.switch_context(context_name)

        if success:
            platform = self.context_manager.detect_platform(context_name)
            return f"Switched to context: {context_name} (Platform: {platform.value})"
        return f"Failed to switch to context: {context_name}"

    async def _handle_get_current_context(self, args: dict) -> str:
        ctx = self.context_manager.get_current_context()
        platform = self.context_manager.detect_platform(ctx.name)

        return (
            f"Current Context: {ctx.name}\n"
            f"Cluster: {ctx.cluster}\n"
            f"User: {ctx.user}\n"
            f"Namespace: {ctx.namespace or 'default'}\n"
            f"Platform: {platform.value}"
        )

    async def _handle_kubectl_explain(self, args: dict) -> str:
        resource = args["resource"]
        result = await self.kubectl.execute(f"explain {resource}")
        return result.output if result.success else f"Error: {result.error}"

    async def _handle_kubectl_api_resources(self, args: dict) -> str:
        namespaced = args.get("namespaced")
        cmd_parts = ["api-resources"]
        if namespaced is not None:
            cmd_parts.append(f"--namespaced={str(namespaced).lower()}")

        result = await self.kubectl.execute(" ".join(cmd_parts))
        return result.output if result.success else f"Error: {result.error}"
