"""Tests for kubectl executor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.k8s.executor import (
    ConfirmationRequest,
    ExecutionResult,
    KubectlExecutor,
    ToolExecutor,
)
from src.k8s.validators import RiskLevel
from src.utils.config import Config


@pytest.fixture
def mock_config():
    config = Config(
        anthropic_api_key="test-key",
        safe_mode=True,
        dry_run=False,
        timeout=10,
        kubeconfig="/tmp/test-kubeconfig",
    )
    return config


class TestKubectlExecutor:
    """Tests for KubectlExecutor class."""

    @pytest.fixture
    def executor(self, mock_config):
        return KubectlExecutor(mock_config)

    @pytest.mark.asyncio
    async def test_execute_valid_command(self, executor):
        with patch.object(executor, "_run_subprocess") as mock_run:
            mock_run.return_value = MagicMock(
                output="NAME  READY  STATUS\nnginx  1/1  Running",
                error=None,
                exit_code=0,
            )

            result = await executor.execute("get pods")

            assert result.success
            assert "nginx" in result.output
            assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_invalid_command_blocked(self, executor):
        result = await executor.execute("get pods; rm -rf /")

        assert not result.success
        assert "Blocked pattern" in result.error

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor):
        async def slow_command():
            await asyncio.sleep(100)
            return MagicMock(output="", error=None, exit_code=0)

        with patch.object(executor, "_run_subprocess", side_effect=asyncio.TimeoutError):
            result = await executor.execute("get pods", timeout=1)

            assert not result.success
            assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_dry_run(self, executor):
        with patch.object(executor, "_run_subprocess") as mock_run:
            mock_run.return_value = MagicMock(
                output="deployment.apps/nginx created (dry run)",
                error=None,
                exit_code=0,
            )

            result = await executor.execute("apply -f test.yaml", dry_run=True)

            assert result.success
            assert result.was_dry_run
            call_args = mock_run.call_args[0][0]
            assert "--dry-run" in call_args

    @pytest.mark.asyncio
    async def test_dangerous_operation_requires_confirmation(self, executor):
        confirmation_called = False

        def mock_confirmation(request: ConfirmationRequest) -> bool:
            nonlocal confirmation_called
            confirmation_called = True
            assert request.risk_level == RiskLevel.CRITICAL
            return True

        executor.confirmation_handler = mock_confirmation

        with patch.object(executor, "_run_subprocess") as mock_run:
            mock_run.return_value = MagicMock(
                output="pod deleted",
                error=None,
                exit_code=0,
            )

            result = await executor.execute("delete pod my-pod")

            assert confirmation_called
            assert result.success

    @pytest.mark.asyncio
    async def test_dangerous_operation_cancelled(self, executor):
        def mock_confirmation(request: ConfirmationRequest) -> bool:
            return False

        executor.confirmation_handler = mock_confirmation

        result = await executor.execute("delete pod my-pod")

        assert not result.success
        assert "cancelled" in result.error.lower()

    @pytest.mark.asyncio
    async def test_safe_operation_no_confirmation(self, executor):
        confirmation_called = False

        def mock_confirmation(request: ConfirmationRequest) -> bool:
            nonlocal confirmation_called
            confirmation_called = True
            return True

        executor.confirmation_handler = mock_confirmation

        with patch.object(executor, "_run_subprocess") as mock_run:
            mock_run.return_value = MagicMock(
                output="NAME  READY",
                error=None,
                exit_code=0,
            )

            result = await executor.execute("get pods")

            assert not confirmation_called
            assert result.success

    def test_build_command_with_kubeconfig(self, executor):
        with patch("os.path.exists", return_value=True):
            cmd = executor._build_command("get pods", dry_run=False)

            assert "kubectl" in cmd
            assert "--kubeconfig" in cmd
            assert "get pods" in cmd

    def test_build_command_with_dry_run(self, executor):
        with patch("os.path.exists", return_value=True):
            cmd = executor._build_command("apply -f test.yaml", dry_run=True)

            assert "--dry-run=client" in cmd


class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.fixture
    def tool_executor(self, mock_config):
        kubectl_executor = MagicMock()
        context_manager = MagicMock()
        return ToolExecutor(kubectl_executor, context_manager)

    @pytest.mark.asyncio
    async def test_handle_kubectl_get(self, tool_executor):
        tool_executor.kubectl.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                output="NAME  READY  STATUS\nnginx  1/1  Running",
                command="kubectl get pods",
            )
        )

        result = await tool_executor.execute(
            "kubectl_get",
            {"resource": "pods", "namespace": "default"}
        )

        assert "nginx" in result
        tool_executor.kubectl.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_kubectl_describe(self, tool_executor):
        tool_executor.kubectl.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                output="Name: nginx\nNamespace: default\nStatus: Running",
                command="kubectl describe pod nginx",
            )
        )

        result = await tool_executor.execute(
            "kubectl_describe",
            {"resource": "pod", "name": "nginx", "namespace": "default"}
        )

        assert "nginx" in result

    @pytest.mark.asyncio
    async def test_handle_kubectl_logs(self, tool_executor):
        tool_executor.kubectl.execute = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                output="2024-01-01 INFO Starting application",
                command="kubectl logs my-pod",
            )
        )

        result = await tool_executor.execute(
            "kubectl_logs",
            {"pod": "my-pod", "tail": 50}
        )

        assert "Starting application" in result

    @pytest.mark.asyncio
    async def test_handle_list_contexts(self, tool_executor):
        mock_context = MagicMock()
        mock_context.name = "minikube"
        mock_context.cluster = "minikube"

        tool_executor.context_manager.list_contexts.return_value = [mock_context]
        tool_executor.context_manager.get_current_context.return_value = mock_context
        tool_executor.context_manager.detect_platform.return_value = MagicMock(value="minikube")

        result = await tool_executor.execute("list_contexts", {})

        assert "minikube" in result

    @pytest.mark.asyncio
    async def test_handle_switch_context(self, tool_executor):
        tool_executor.context_manager.switch_context.return_value = True
        tool_executor.context_manager.detect_platform.return_value = MagicMock(value="eks")

        result = await tool_executor.execute(
            "switch_context",
            {"context_name": "my-eks-cluster"}
        )

        assert "Switched" in result
        tool_executor.context_manager.switch_context.assert_called_with("my-eks-cluster")

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, tool_executor):
        result = await tool_executor.execute("unknown_tool", {})

        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_handle_tool_error(self, tool_executor):
        tool_executor.kubectl.execute = AsyncMock(
            return_value=ExecutionResult(
                success=False,
                output="",
                error="Connection refused",
                command="kubectl get pods",
            )
        )

        result = await tool_executor.execute(
            "kubectl_get",
            {"resource": "pods"}
        )

        assert "Error" in result
