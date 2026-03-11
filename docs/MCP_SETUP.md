# kubectl-ai MCP Server Setup

This guide explains how to set up kubectl-ai as an MCP (Model Context Protocol) server, allowing Claude in Cursor or other MCP clients to directly interact with your Kubernetes clusters.

---

## Quick Setup (Recommended)

Run the automated setup script:

```bash
# Clone the repository
git clone https://github.com/Mudassar-Malek/kubectl-ai.git
cd kubectl-ai

# Run the setup script
./scripts/setup-mcp.sh

# Restart Cursor IDE
# Then ask Claude: "Show me all pods in my cluster"
```

That's it! The script will:
- Create a virtual environment
- Install all dependencies
- Configure Cursor's MCP settings
- Test the connection

---

## Manual Setup

If you prefer manual setup, follow the steps below.

---

## What is MCP?

MCP (Model Context Protocol) allows AI assistants like Claude to use external tools. Instead of running kubectl-ai as a separate chatbot, you expose it as an MCP server that Claude can call directly.

### Benefits

| Aspect | CLI Bot | MCP Server |
|--------|---------|------------|
| LLM Used | Ollama (local) | Claude (in Cursor) |
| Speed | 30-120 seconds | 2-5 seconds |
| Integration | Separate terminal | Inside Cursor |
| Context | Separate conversation | Shares Cursor context |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CURSOR IDE                           │
│                                                              │
│   You: "Show me all failing pods in production"             │
│                           │                                  │
│                           ▼                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                    CLAUDE                            │   │
│   │  (Sees kubectl-ai tools via MCP)                    │   │
│   │  Decides to call: kubectl_get(resource="pods")      │   │
│   └──────────────────────┬──────────────────────────────┘   │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           │ MCP Protocol (stdio)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    kubectl-ai MCP Server                     │
│                                                              │
│   Receives: kubectl_get(resource="pods")                    │
│   Executes: kubectl get pods                                │
│   Returns: Pod list to Claude                               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  KUBERNETES CLUSTER                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup Instructions

### Step 1: Install MCP Package

```bash
cd /Users/mmalek/Documents/github_repo/k8s-bot
source venv/bin/activate
pip install mcp
```

### Step 2: Test the MCP Server

```bash
# Test that it starts correctly
python -m src.mcp_server

# You should see:
# Starting kubectl-ai MCP Server...
# Kubeconfig: /Users/mmalek/.kube/config
# Current context: minikube
# MCP Server ready. Waiting for connections...
```

Press `Ctrl+C` to stop.

### Step 3: Configure Cursor

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "/Users/mmalek/Documents/github_repo/k8s-bot/venv/bin/python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/Users/mmalek/Documents/github_repo/k8s-bot",
      "env": {
        "KUBECONFIG": "/Users/mmalek/.kube/config"
      }
    }
  }
}
```

### Step 4: Restart Cursor

1. Quit Cursor completely
2. Reopen Cursor
3. The MCP server will auto-start

### Step 5: Verify in Cursor

Open a new chat in Cursor and ask:

```
What Kubernetes tools do you have access to?
```

Claude should list the kubectl-ai tools.

---

## Available Tools

Once configured, Claude has access to these tools:

### Read Operations

| Tool | Description |
|------|-------------|
| `kubectl_get` | List resources (pods, deployments, services, etc.) |
| `kubectl_describe` | Get detailed resource info |
| `kubectl_logs` | View container logs |
| `kubectl_get_events` | View cluster events |
| `get_current_context` | Show current cluster |
| `list_contexts` | List all clusters |

### Analysis Tools

| Tool | Description |
|------|-------------|
| `cluster_health` | Get cluster health score |
| `security_audit` | Run security checks |
| `explain_error` | Diagnose failing resources |

### Write Operations

| Tool | Description |
|------|-------------|
| `kubectl_scale` | Scale deployments |
| `kubectl_rollout` | Manage rollouts |
| `switch_context` | Switch clusters |

---

## Usage Examples

Once configured, just ask Claude in Cursor:

### Basic Queries
```
Show me all pods in the default namespace
List deployments across all namespaces
What services are running?
```

### Troubleshooting
```
Why is my nginx pod failing?
Check the health of my cluster
Run a security audit
```

### Operations
```
Scale the web deployment to 5 replicas
Restart the api-server deployment
Switch to my production cluster
```

---

## Configuration Options

### Environment Variables

You can pass environment variables in `mcp.json`:

```json
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/k8s-bot",
      "env": {
        "KUBECONFIG": "/path/to/.kube/config",
        "K8S_BOT_SAFE_MODE": "true",
        "K8S_BOT_TIMEOUT": "30"
      }
    }
  }
}
```

### Multiple Clusters

For multiple clusters, you can create multiple MCP servers:

```json
{
  "mcpServers": {
    "kubectl-ai-dev": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/k8s-bot",
      "env": {
        "KUBECONFIG": "/path/to/dev-kubeconfig"
      }
    },
    "kubectl-ai-prod": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/k8s-bot",
      "env": {
        "KUBECONFIG": "/path/to/prod-kubeconfig"
      }
    }
  }
}
```

---

## Troubleshooting

### MCP Server Not Starting

```bash
# Check if MCP is installed
pip show mcp

# Test the server manually
cd /Users/mmalek/Documents/github_repo/k8s-bot
source venv/bin/activate
python -m src.mcp_server
```

### Tools Not Appearing in Cursor

1. Check `~/.cursor/mcp.json` syntax (valid JSON?)
2. Restart Cursor completely
3. Check Cursor's MCP logs

### Permission Errors

```bash
# Make sure the kubeconfig is readable
ls -la ~/.kube/config

# Test kubectl directly
kubectl get nodes
```

### Debugging

Add debug output to see what's happening:

```bash
# Run with verbose output
python -m src.mcp_server 2>&1 | tee mcp-debug.log
```

---

## Security Considerations

1. **Read-Only Mode**: Consider creating a read-only kubeconfig for safety
2. **Namespace Restrictions**: Use RBAC to limit what namespaces can be accessed
3. **Audit Logging**: MCP server logs all tool calls to stderr

### Creating a Read-Only Kubeconfig

```bash
# Create a service account with read-only access
kubectl create serviceaccount mcp-reader
kubectl create clusterrolebinding mcp-reader --clusterrole=view --serviceaccount=default:mcp-reader

# Get the token and create kubeconfig
# (Use this kubeconfig in mcp.json)
```

---

## Comparison: CLI Bot vs MCP Server

| Feature | CLI Bot | MCP Server |
|---------|---------|------------|
| How to use | `python -m src.main chat` | Just ask Claude in Cursor |
| LLM | Ollama (local) or Claude API | Claude (via Cursor) |
| Speed | Depends on Ollama | Fast (Claude) |
| Pre-hook approval | ✅ Supported | ❌ Not yet |
| Conversation memory | ✅ Yes | ✅ Cursor manages it |
| Cost | Free (Ollama) or API costs | Included in Cursor |

---

## File Structure

```
k8s-bot/
├── src/
│   ├── mcp_server.py      # MCP server entry point
│   ├── k8s/
│   │   ├── executor.py    # Tool execution
│   │   ├── health.py      # Health & security tools
│   │   └── contexts.py    # Cluster management
│   └── utils/
│       └── config.py      # Configuration
└── docs/
    └── MCP_SETUP.md       # This file
```

---

## Quick Reference

```bash
# Install MCP
pip install mcp

# Test server
python -m src.mcp_server

# Configure Cursor
# Edit ~/.cursor/mcp.json

# Restart Cursor
# Then ask Claude about Kubernetes!
```

That's it! Your kubectl-ai is now available as an MCP server.
