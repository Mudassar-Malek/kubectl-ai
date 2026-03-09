"""Multi-platform Kubernetes context management."""

import os
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import get_logger


class Platform(Enum):
    """Supported Kubernetes platforms."""

    MINIKUBE = "minikube"
    EKS = "aws-eks"
    AKS = "azure-aks"
    GKE = "google-gke"
    KIND = "kind"
    K3S = "k3s"
    RANCHER = "rancher"
    OPENSHIFT = "openshift"
    DOCKER_DESKTOP = "docker-desktop"
    UNKNOWN = "unknown"


@dataclass
class ClusterContext:
    """Represents a Kubernetes context."""

    name: str
    cluster: str
    user: str
    namespace: Optional[str] = None
    is_current: bool = False


class ContextManager:
    """Manages Kubernetes contexts across multiple platforms.

    Supports:
    - Minikube (including Podman driver)
    - AWS EKS
    - Azure AKS
    - Google GKE
    - Kind
    - Docker Desktop
    - And other kubeconfig-based clusters
    """

    PLATFORM_PATTERNS = {
        Platform.MINIKUBE: [r"minikube", r"podman-minikube"],
        Platform.EKS: [r"arn:aws:eks:", r"eks[._-]", r"\.eks\.amazonaws\.com"],
        Platform.AKS: [r"\.azmk8s\.io", r"aks[._-]", r"azure"],
        Platform.GKE: [r"gke_", r"\.gke\.io", r"container\.googleapis\.com"],
        Platform.KIND: [r"kind-", r"kind$"],
        Platform.K3S: [r"k3s", r"k3d-"],
        Platform.RANCHER: [r"rancher"],
        Platform.OPENSHIFT: [r"openshift", r"ocp"],
        Platform.DOCKER_DESKTOP: [r"docker-desktop", r"docker-for-desktop"],
    }

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """Initialize the context manager.

        Args:
            kubeconfig_path: Path to kubeconfig file. Defaults to ~/.kube/config
        """
        self.kubeconfig_path = os.path.expanduser(
            kubeconfig_path or os.environ.get("KUBECONFIG", "~/.kube/config")
        )
        self.logger = get_logger("context_manager")
        self._kubeconfig_cache: Optional[dict] = None
        self._cache_mtime: float = 0

    def _load_kubeconfig(self) -> dict:
        """Load kubeconfig file with caching."""
        if not Path(self.kubeconfig_path).exists():
            self.logger.warning(f"Kubeconfig not found: {self.kubeconfig_path}")
            return {"contexts": [], "clusters": [], "users": [], "current-context": ""}

        mtime = Path(self.kubeconfig_path).stat().st_mtime
        if self._kubeconfig_cache and mtime == self._cache_mtime:
            return self._kubeconfig_cache

        with open(self.kubeconfig_path, "r") as f:
            self._kubeconfig_cache = yaml.safe_load(f) or {}
            self._cache_mtime = mtime
            return self._kubeconfig_cache

    def list_contexts(self) -> list[ClusterContext]:
        """List all available Kubernetes contexts.

        Returns:
            List of ClusterContext objects
        """
        config = self._load_kubeconfig()
        current = config.get("current-context", "")
        contexts = []

        for ctx in config.get("contexts", []):
            ctx_info = ctx.get("context", {})
            contexts.append(
                ClusterContext(
                    name=ctx.get("name", ""),
                    cluster=ctx_info.get("cluster", ""),
                    user=ctx_info.get("user", ""),
                    namespace=ctx_info.get("namespace"),
                    is_current=ctx.get("name") == current,
                )
            )

        return contexts

    def get_current_context(self) -> ClusterContext:
        """Get the currently active context.

        Returns:
            ClusterContext for the current context
        """
        config = self._load_kubeconfig()
        current_name = config.get("current-context", "")

        if not current_name:
            return ClusterContext(name="", cluster="", user="", is_current=True)

        for ctx in config.get("contexts", []):
            if ctx.get("name") == current_name:
                ctx_info = ctx.get("context", {})
                return ClusterContext(
                    name=current_name,
                    cluster=ctx_info.get("cluster", ""),
                    user=ctx_info.get("user", ""),
                    namespace=ctx_info.get("namespace"),
                    is_current=True,
                )

        return ClusterContext(name=current_name, cluster="", user="", is_current=True)

    def switch_context(self, context_name: str) -> bool:
        """Switch to a different Kubernetes context.

        Args:
            context_name: Name of the context to switch to

        Returns:
            True if successful, False otherwise
        """
        contexts = self.list_contexts()
        if not any(ctx.name == context_name for ctx in contexts):
            self.logger.error(f"Context not found: {context_name}")
            return False

        try:
            result = subprocess.run(
                ["kubectl", "config", "use-context", context_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self._kubeconfig_cache = None
                self.logger.info(f"Switched to context: {context_name}")
                return True
            else:
                self.logger.error(f"Failed to switch context: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Context switch timed out")
            return False
        except Exception as e:
            self.logger.error(f"Context switch failed: {e}")
            return False

    def detect_platform(self, context_name: Optional[str] = None) -> Platform:
        """Detect the platform type for a context.

        Args:
            context_name: Context name to analyze. Uses current if not specified.

        Returns:
            Detected Platform enum value
        """
        if context_name is None:
            ctx = self.get_current_context()
            context_name = ctx.name
            cluster_name = ctx.cluster
        else:
            config = self._load_kubeconfig()
            cluster_name = ""
            for ctx in config.get("contexts", []):
                if ctx.get("name") == context_name:
                    cluster_name = ctx.get("context", {}).get("cluster", "")
                    break

        search_string = f"{context_name} {cluster_name}".lower()

        for platform, patterns in self.PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, search_string, re.IGNORECASE):
                    return platform

        return Platform.UNKNOWN

    def get_cluster_info(self, context_name: Optional[str] = None) -> dict:
        """Get detailed cluster information.

        Args:
            context_name: Context to get info for. Uses current if not specified.

        Returns:
            Dictionary with cluster details
        """
        config = self._load_kubeconfig()

        if context_name is None:
            context_name = config.get("current-context", "")

        cluster_name = ""
        user_name = ""
        namespace = None

        for ctx in config.get("contexts", []):
            if ctx.get("name") == context_name:
                ctx_info = ctx.get("context", {})
                cluster_name = ctx_info.get("cluster", "")
                user_name = ctx_info.get("user", "")
                namespace = ctx_info.get("namespace")
                break

        cluster_info = {}
        for cluster in config.get("clusters", []):
            if cluster.get("name") == cluster_name:
                cluster_info = cluster.get("cluster", {})
                break

        return {
            "context": context_name,
            "cluster": cluster_name,
            "user": user_name,
            "namespace": namespace or "default",
            "server": cluster_info.get("server", ""),
            "platform": self.detect_platform(context_name).value,
        }

    def validate_connection(self) -> tuple[bool, str]:
        """Validate the current cluster connection.

        Returns:
            Tuple of (success, message)
        """
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info", "--request-timeout=5s"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return True, "Cluster connection validated"
            else:
                return False, f"Connection failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            return False, "Connection timed out"
        except FileNotFoundError:
            return False, "kubectl not found in PATH"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def set_namespace(self, namespace: str, context_name: Optional[str] = None) -> bool:
        """Set the default namespace for a context.

        Args:
            namespace: Namespace to set as default
            context_name: Context to modify. Uses current if not specified.

        Returns:
            True if successful
        """
        if context_name is None:
            context_name = self.get_current_context().name

        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "config",
                    "set-context",
                    context_name,
                    f"--namespace={namespace}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self._kubeconfig_cache = None
                self.logger.info(f"Set namespace to {namespace} for context {context_name}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to set namespace: {e}")
            return False


def get_platform_features(platform: Platform) -> dict:
    """Get platform-specific features and notes.

    Args:
        platform: The platform to get features for

    Returns:
        Dictionary of platform features
    """
    features = {
        Platform.MINIKUBE: {
            "local": True,
            "supports_load_balancer": False,
            "notes": "Local development cluster. Use 'minikube tunnel' for LoadBalancer services.",
        },
        Platform.EKS: {
            "local": False,
            "supports_load_balancer": True,
            "notes": "AWS managed Kubernetes. IAM authentication required.",
        },
        Platform.AKS: {
            "local": False,
            "supports_load_balancer": True,
            "notes": "Azure managed Kubernetes. Azure AD authentication available.",
        },
        Platform.GKE: {
            "local": False,
            "supports_load_balancer": True,
            "notes": "Google managed Kubernetes. GCP IAM integration available.",
        },
        Platform.KIND: {
            "local": True,
            "supports_load_balancer": False,
            "notes": "Local development cluster running in Docker.",
        },
        Platform.DOCKER_DESKTOP: {
            "local": True,
            "supports_load_balancer": False,
            "notes": "Local Kubernetes in Docker Desktop.",
        },
    }

    return features.get(
        platform,
        {"local": False, "supports_load_balancer": True, "notes": "Standard Kubernetes cluster"},
    )
