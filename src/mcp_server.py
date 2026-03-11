"""MCP Server for kubectl-ai - Expose Kubernetes tools via Model Context Protocol."""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to Python path (needed for MCP server)
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource
except ImportError:
    print("MCP package not installed. Run: pip install mcp")
    print("Or: pip install 'mcp[cli]'")
    sys.exit(1)

from src.k8s.contexts import ContextManager
from src.k8s.executor import KubectlExecutor, ToolExecutor
from src.k8s.health import ClusterHealthChecker, SecurityAuditor
from src.utils.config import Config

# Load configuration
config = Config.load()

# Initialize Kubernetes components
context_manager = ContextManager(config.kubeconfig)
kubectl_executor = KubectlExecutor(config)
tool_executor = ToolExecutor(kubectl_executor, context_manager)

# Create MCP server
server = Server("kubectl-ai")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Kubernetes tools."""
    return [
        Tool(
            name="kubectl_get",
            description="List Kubernetes resources (pods, deployments, services, nodes, namespaces, configmaps, secrets)",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource type: pods, deployments, services, nodes, namespaces, configmaps, secrets, ingresses, pv, pvc"
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional: specific resource name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (use 'all' for all namespaces)"
                    },
                    "selector": {
                        "type": "string",
                        "description": "Label selector (e.g., 'app=nginx')"
                    },
                    "output": {
                        "type": "string",
                        "enum": ["wide", "yaml", "json", "name"],
                        "description": "Output format"
                    }
                },
                "required": ["resource"]
            }
        ),
        Tool(
            name="kubectl_describe",
            description="Get detailed information about a Kubernetes resource including events and status",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource type (pod, deployment, service, node)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace"
                    }
                },
                "required": ["resource", "name"]
            }
        ),
        Tool(
            name="kubectl_logs",
            description="Get container logs from a pod",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod": {
                        "type": "string",
                        "description": "Pod name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace"
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name (for multi-container pods)"
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines to show (default: 100)"
                    },
                    "since": {
                        "type": "string",
                        "description": "Show logs since (e.g., '1h', '30m')"
                    },
                    "previous": {
                        "type": "boolean",
                        "description": "Show logs from previous container instance"
                    }
                },
                "required": ["pod"]
            }
        ),
        Tool(
            name="kubectl_get_events",
            description="Get cluster events to see what's happening (scheduling, errors, warnings)",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace (use 'all' for all namespaces)"
                    }
                }
            }
        ),
        Tool(
            name="cluster_health",
            description="Get cluster health score and status report (nodes, pods, deployments, services)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="security_audit",
            description="Run security audit on the cluster (privileged containers, root users, resource limits, network policies)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="kubectl_scale",
            description="Scale a deployment, replicaset, or statefulset",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "description": "Resource type (deployment, replicaset, statefulset)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name"
                    },
                    "replicas": {
                        "type": "integer",
                        "description": "Number of replicas"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace"
                    }
                },
                "required": ["resource", "name", "replicas"]
            }
        ),
        Tool(
            name="kubectl_rollout",
            description="Manage rollouts (status, history, restart, undo)",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["status", "history", "restart", "undo"],
                        "description": "Rollout action"
                    },
                    "resource": {
                        "type": "string",
                        "description": "Resource type (deployment, daemonset, statefulset)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace"
                    },
                    "revision": {
                        "type": "integer",
                        "description": "Revision number (for undo)"
                    }
                },
                "required": ["action", "resource", "name"]
            }
        ),
        Tool(
            name="list_contexts",
            description="List all available Kubernetes contexts (clusters)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="switch_context",
            description="Switch to a different Kubernetes context (cluster)",
            inputSchema={
                "type": "object",
                "properties": {
                    "context_name": {
                        "type": "string",
                        "description": "Name of the context to switch to"
                    }
                },
                "required": ["context_name"]
            }
        ),
        Tool(
            name="get_current_context",
            description="Get the current Kubernetes context (cluster) information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="explain_error",
            description="Diagnose why a pod or resource is failing (CrashLoopBackOff, ImagePullBackOff, Pending, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": "Resource type (pod, deployment)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace"
                    }
                },
                "required": ["resource_type", "name"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a Kubernetes tool."""
    try:
        # Handle special tools that don't go through ToolExecutor
        if name == "cluster_health":
            checker = ClusterHealthChecker(config.kubeconfig)
            report = await checker.get_health_report()
            return [TextContent(type="text", text=report.to_string())]
        
        elif name == "security_audit":
            auditor = SecurityAuditor(config.kubeconfig)
            report = await auditor.get_audit_report()
            return [TextContent(type="text", text=report.to_string())]
        
        # All other tools go through ToolExecutor
        result = await tool_executor.execute(name, arguments)
        return [TextContent(type="text", text=result)]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources (cluster info)."""
    try:
        ctx = context_manager.get_current_context()
        return [
            Resource(
                uri=f"k8s://context/{ctx.name}",
                name=f"Current Context: {ctx.name}",
                description=f"Cluster: {ctx.cluster}, Namespace: {ctx.namespace or 'default'}",
                mimeType="text/plain"
            )
        ]
    except Exception:
        return []


async def main():
    """Run the MCP server."""
    print("Starting kubectl-ai MCP Server...", file=sys.stderr)
    print(f"Kubeconfig: {config.kubeconfig}", file=sys.stderr)
    
    try:
        ctx = context_manager.get_current_context()
        print(f"Current context: {ctx.name}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not get current context: {e}", file=sys.stderr)
    
    print("MCP Server ready. Waiting for connections...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
