"""Tests for kubectl command validators."""

import pytest

from src.k8s.validators import CommandValidator, RiskLevel, ValidationResult


class TestCommandValidator:
    """Tests for CommandValidator class."""

    @pytest.fixture
    def validator(self):
        return CommandValidator()

    # Safe command tests
    def test_get_pods_is_safe(self, validator):
        result = validator.validate_command("get pods")
        assert result.is_valid
        assert result.risk_level == RiskLevel.SAFE
        assert not result.requires_confirmation

    def test_describe_deployment_is_safe(self, validator):
        result = validator.validate_command("describe deployment nginx")
        assert result.is_valid
        assert result.risk_level == RiskLevel.SAFE

    def test_logs_is_safe(self, validator):
        result = validator.validate_command("logs my-pod --tail=100")
        assert result.is_valid
        assert result.risk_level == RiskLevel.SAFE

    def test_explain_is_safe(self, validator):
        result = validator.validate_command("explain pods.spec")
        assert result.is_valid
        assert result.risk_level == RiskLevel.SAFE

    # Moderate risk tests
    def test_scale_is_moderate(self, validator):
        result = validator.validate_command("scale deployment/nginx --replicas=3")
        assert result.is_valid
        assert result.risk_level == RiskLevel.MODERATE

    def test_exec_is_moderate(self, validator):
        result = validator.validate_command("exec -it my-pod -- /bin/sh")
        assert result.is_valid
        assert result.risk_level == RiskLevel.MODERATE

    # Dangerous operation tests
    def test_apply_is_dangerous(self, validator):
        result = validator.validate_command("apply -f deployment.yaml", safe_mode=True)
        assert result.is_valid
        assert result.risk_level == RiskLevel.DANGEROUS
        assert result.requires_confirmation

    def test_rollout_restart_is_dangerous(self, validator):
        result = validator.validate_command("rollout restart deployment/nginx", safe_mode=True)
        assert result.is_valid
        assert result.risk_level == RiskLevel.DANGEROUS
        assert result.requires_confirmation

    # Critical operation tests
    def test_delete_is_critical(self, validator):
        result = validator.validate_command("delete pod my-pod", safe_mode=True)
        assert result.is_valid
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.requires_confirmation

    def test_delete_namespace_is_critical(self, validator):
        result = validator.validate_command("delete namespace production", safe_mode=True)
        assert result.is_valid
        assert result.risk_level == RiskLevel.CRITICAL

    # Blocked patterns tests
    def test_command_chaining_blocked(self, validator):
        result = validator.validate_command("get pods; rm -rf /")
        assert not result.is_valid
        assert "Blocked pattern" in result.message

    def test_pipe_blocked(self, validator):
        result = validator.validate_command("get pods | grep nginx")
        assert not result.is_valid

    def test_and_operator_blocked(self, validator):
        result = validator.validate_command("get pods && delete pods")
        assert not result.is_valid

    def test_command_substitution_blocked(self, validator):
        result = validator.validate_command("get pods $(whoami)")
        assert not result.is_valid

    def test_backtick_substitution_blocked(self, validator):
        result = validator.validate_command("get pods `id`")
        assert not result.is_valid

    def test_output_redirection_blocked(self, validator):
        result = validator.validate_command("get pods > /tmp/pods.txt")
        assert not result.is_valid

    # Empty command test
    def test_empty_command_invalid(self, validator):
        result = validator.validate_command("")
        assert not result.is_valid
        assert "Empty command" in result.message

    def test_whitespace_only_invalid(self, validator):
        result = validator.validate_command("   ")
        assert not result.is_valid

    # Safe mode toggle tests
    def test_dangerous_without_safe_mode(self, validator):
        result = validator.validate_command("delete pod my-pod", safe_mode=False)
        assert result.is_valid
        assert not result.requires_confirmation

    def test_dangerous_with_safe_mode(self, validator):
        result = validator.validate_command("delete pod my-pod", safe_mode=True)
        assert result.is_valid
        assert result.requires_confirmation


class TestResourceNameValidation:
    """Tests for resource name validation."""

    @pytest.fixture
    def validator(self):
        return CommandValidator()

    def test_valid_resource_name(self, validator):
        assert validator.validate_resource_name("my-pod")
        assert validator.validate_resource_name("nginx-deployment")
        assert validator.validate_resource_name("api-v2")

    def test_valid_single_char(self, validator):
        assert validator.validate_resource_name("a")

    def test_invalid_starts_with_hyphen(self, validator):
        assert not validator.validate_resource_name("-my-pod")

    def test_invalid_ends_with_hyphen(self, validator):
        assert not validator.validate_resource_name("my-pod-")

    def test_invalid_uppercase(self, validator):
        assert not validator.validate_resource_name("MyPod")

    def test_invalid_underscore(self, validator):
        assert not validator.validate_resource_name("my_pod")

    def test_invalid_empty(self, validator):
        assert not validator.validate_resource_name("")


class TestLabelSelectorValidation:
    """Tests for label selector validation."""

    @pytest.fixture
    def validator(self):
        return CommandValidator()

    def test_valid_simple_selector(self, validator):
        assert validator.validate_label_selector("app=nginx")

    def test_valid_multiple_selectors(self, validator):
        assert validator.validate_label_selector("app=nginx,env=prod")

    def test_valid_empty_selector(self, validator):
        assert validator.validate_label_selector("")

    def test_valid_complex_selector(self, validator):
        assert validator.validate_label_selector("app.kubernetes.io/name=nginx")
