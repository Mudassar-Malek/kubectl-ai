"""Kubernetes tool definitions for Claude API."""

from typing import Any

# Essential tools for Ollama (smaller context, faster inference)
KUBERNETES_TOOLS_LITE: list[dict[str, Any]] = [
    {
        "name": "kubectl_get",
        "description": "List Kubernetes resources (pods, deployments, services, nodes, namespaces).",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {"type": "string", "description": "Resource type: pods, deployments, services, nodes, namespaces"},
                "namespace": {"type": "string", "description": "Namespace (use 'all' for all namespaces)"},
            },
            "required": ["resource"],
        },
    },
    {
        "name": "kubectl_describe",
        "description": "Get detailed info about a resource. Shows events and status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {"type": "string", "description": "Resource type"},
                "name": {"type": "string", "description": "Resource name"},
                "namespace": {"type": "string", "description": "Namespace"},
            },
            "required": ["resource", "name"],
        },
    },
    {
        "name": "kubectl_logs",
        "description": "Get container logs from a pod.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod": {"type": "string", "description": "Pod name"},
                "namespace": {"type": "string", "description": "Namespace"},
                "tail": {"type": "integer", "description": "Number of lines (default 50)"},
            },
            "required": ["pod"],
        },
    },
    {
        "name": "kubectl_get_events",
        "description": "Get cluster events to see what's happening.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {"type": "string", "description": "Namespace"},
            },
            "required": [],
        },
    },
]

# Full tools for Claude API (larger context supported)
KUBERNETES_TOOLS: list[dict[str, Any]] = [
    {
        "name": "kubectl_get",
        "description": "List Kubernetes resources. Use this to see pods, deployments, services, nodes, configmaps, secrets, namespaces, and other resources. Returns a formatted table of resources with their status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "The resource type to list (e.g., pods, deployments, services, nodes, configmaps, secrets, namespaces, ingresses, pv, pvc, jobs, cronjobs)",
                },
                "name": {
                    "type": "string",
                    "description": "Optional specific resource name to get",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace to query. Use 'all' for all namespaces. Defaults to current namespace.",
                },
                "selector": {
                    "type": "string",
                    "description": "Label selector to filter resources (e.g., 'app=nginx,env=prod')",
                },
                "output": {
                    "type": "string",
                    "enum": ["wide", "yaml", "json", "name"],
                    "description": "Output format. 'wide' shows additional columns.",
                },
            },
            "required": ["resource"],
        },
    },
    {
        "name": "kubectl_describe",
        "description": "Get detailed information about a specific Kubernetes resource. Shows events, conditions, and configuration details. Useful for debugging issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "The resource type (e.g., pod, deployment, service, node)",
                },
                "name": {
                    "type": "string",
                    "description": "The name of the resource to describe",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the resource. Defaults to current namespace.",
                },
            },
            "required": ["resource", "name"],
        },
    },
    {
        "name": "kubectl_logs",
        "description": "Fetch logs from a container in a pod. Essential for debugging application issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod": {
                    "type": "string",
                    "description": "Name of the pod",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the pod. Defaults to current namespace.",
                },
                "container": {
                    "type": "string",
                    "description": "Container name (required if pod has multiple containers)",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of lines from the end to show (default: 100)",
                },
                "since": {
                    "type": "string",
                    "description": "Show logs since duration (e.g., '5m', '1h', '24h')",
                },
                "previous": {
                    "type": "boolean",
                    "description": "Show logs from previous container instance (useful for crash debugging)",
                },
            },
            "required": ["pod"],
        },
    },
    {
        "name": "kubectl_get_events",
        "description": "Get cluster events. Events show what's happening in the cluster - scheduling, pulling images, creating containers, errors, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespace": {
                    "type": "string",
                    "description": "Namespace to query events from. Use 'all' for all namespaces.",
                },
                "field_selector": {
                    "type": "string",
                    "description": "Filter events by field (e.g., 'involvedObject.name=my-pod', 'type=Warning')",
                },
            },
            "required": [],
        },
    },
    {
        "name": "kubectl_top",
        "description": "Show resource usage (CPU/memory) for nodes or pods. Requires metrics-server to be installed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "enum": ["nodes", "pods"],
                    "description": "Show metrics for nodes or pods",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace for pod metrics. Use 'all' for all namespaces.",
                },
                "name": {
                    "type": "string",
                    "description": "Specific node or pod name",
                },
            },
            "required": ["resource"],
        },
    },
    {
        "name": "kubectl_scale",
        "description": "Scale a deployment, replicaset, or statefulset to a specified number of replicas. CAUTION: This modifies cluster state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "enum": ["deployment", "replicaset", "statefulset"],
                    "description": "Resource type to scale",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the resource to scale",
                },
                "replicas": {
                    "type": "integer",
                    "description": "Desired number of replicas",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the resource",
                },
            },
            "required": ["resource", "name", "replicas"],
        },
    },
    {
        "name": "kubectl_rollout",
        "description": "Manage rollouts for deployments. Check status, restart deployments, or undo to previous versions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "restart", "undo", "history"],
                    "description": "Rollout action to perform",
                },
                "resource": {
                    "type": "string",
                    "enum": ["deployment", "daemonset", "statefulset"],
                    "description": "Resource type",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the resource",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the resource",
                },
                "revision": {
                    "type": "integer",
                    "description": "Revision number for undo (defaults to previous)",
                },
            },
            "required": ["action", "resource", "name"],
        },
    },
    {
        "name": "kubectl_exec",
        "description": "Execute a command inside a container. Useful for debugging and inspection. CAUTION: Can modify container state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pod": {
                    "type": "string",
                    "description": "Name of the pod",
                },
                "command": {
                    "type": "string",
                    "description": "Command to execute (e.g., 'ls -la', 'cat /etc/config')",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the pod",
                },
                "container": {
                    "type": "string",
                    "description": "Container name (required if pod has multiple containers)",
                },
            },
            "required": ["pod", "command"],
        },
    },
    {
        "name": "kubectl_apply",
        "description": "Apply a Kubernetes manifest to create or update resources. CAUTION: This modifies cluster state and requires confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "manifest": {
                    "type": "string",
                    "description": "YAML manifest content to apply",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace to apply to (can also be in manifest)",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "Perform a dry run without making changes",
                },
            },
            "required": ["manifest"],
        },
    },
    {
        "name": "kubectl_delete",
        "description": "Delete Kubernetes resources. CAUTION: This is destructive and requires confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Resource type to delete (e.g., pod, deployment, service)",
                },
                "name": {
                    "type": "string",
                    "description": "Name of the resource to delete",
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace of the resource",
                },
                "selector": {
                    "type": "string",
                    "description": "Label selector to delete multiple resources",
                },
                "force": {
                    "type": "boolean",
                    "description": "Force immediate deletion",
                },
            },
            "required": ["resource"],
        },
    },
    {
        "name": "list_contexts",
        "description": "List all available Kubernetes contexts from kubeconfig. Shows cluster name, user, and current context.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "switch_context",
        "description": "Switch to a different Kubernetes context (cluster). Use this to switch between Minikube, EKS, AKS, GKE, or other clusters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "context_name": {
                    "type": "string",
                    "description": "Name of the context to switch to",
                },
            },
            "required": ["context_name"],
        },
    },
    {
        "name": "get_current_context",
        "description": "Get information about the current Kubernetes context including cluster name, namespace, and platform.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "kubectl_explain",
        "description": "Get documentation for Kubernetes resources and their fields. Useful for understanding resource schemas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "Resource to explain (e.g., 'pods', 'pods.spec.containers', 'deployment.spec')",
                },
            },
            "required": ["resource"],
        },
    },
    {
        "name": "kubectl_api_resources",
        "description": "List all available API resources in the cluster. Shows resource names, shortnames, API groups, and whether they're namespaced.",
        "input_schema": {
            "type": "object",
            "properties": {
                "namespaced": {
                    "type": "boolean",
                    "description": "Filter to show only namespaced or cluster-scoped resources",
                },
            },
            "required": [],
        },
    },
]


def get_tool_by_name(name: str) -> dict[str, Any] | None:
    """Get a tool definition by name."""
    for tool in KUBERNETES_TOOLS:
        if tool["name"] == name:
            return tool
    return None


def get_all_tool_names() -> list[str]:
    """Get list of all tool names."""
    return [tool["name"] for tool in KUBERNETES_TOOLS]


DESTRUCTIVE_TOOLS = {
    "kubectl_apply",
    "kubectl_delete",
    "kubectl_scale",
    "kubectl_exec",
    "kubectl_rollout",  # restart and undo are destructive
    "switch_context",
}

SAFE_TOOLS = {
    "kubectl_get",
    "kubectl_describe",
    "kubectl_logs",
    "kubectl_get_events",
    "kubectl_top",
    "list_contexts",
    "get_current_context",
    "kubectl_explain",
    "kubectl_api_resources",
}


def is_destructive_tool(name: str) -> bool:
    """Check if a tool is potentially destructive."""
    return name in DESTRUCTIVE_TOOLS
