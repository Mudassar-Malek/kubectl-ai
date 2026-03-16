# kubectl-ai Setup Guide

This guide explains how to set up and use the **kubectl-ai** skill in Cursor IDE.

---

## Overview

The kubectl-ai skill enables natural language Kubernetes management. It requires:

1. **kubectl-ai MCP Server** — Runs locally, executes kubectl commands
2. **Cursor IDE Configuration** — Connects Cursor to the MCP server
3. **Kubernetes Access** — Valid kubeconfig for your cluster(s)

---

## Quick Start (5 minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/k8s-bot.git
cd k8s-bot
```

### Step 2: Run Automated Setup

```bash
chmod +x scripts/setup-mcp.sh
./scripts/setup-mcp.sh
```

This script will:
- Create a Python virtual environment
- Install all dependencies
- Configure Cursor's `~/.cursor/mcp.json`
- Test the MCP server

### Step 3: Restart Cursor

After setup, **restart Cursor IDE** to load the new MCP configuration.

### Step 4: Verify Setup

In Cursor, check that `user-kubectl-ai` appears in your MCP tools. You can verify by asking:

> "List all pods in default namespace"

---

## Manual Setup

If you prefer manual setup or the script doesn't work for your environment:

### Prerequisites

| Requirement | How to Check | Install Command |
|-------------|--------------|-----------------|
| Python 3.10+ | `python3 --version` | [python.org](https://python.org) |
| kubectl | `kubectl version` | [kubernetes.io/docs/tasks/tools](https://kubernetes.io/docs/tasks/tools/) |
| Valid kubeconfig | `kubectl cluster-info` | Provided by your cluster admin |

### Step 1: Create Virtual Environment

```bash
cd k8s-bot
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

Verify installation:
```bash
pip show mcp kubernetes click rich
```

### Step 3: Configure Cursor MCP

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "/FULL/PATH/TO/k8s-bot/venv/bin/python3",
      "args": ["/FULL/PATH/TO/k8s-bot/src/mcp_server.py"],
      "env": {
        "KUBECONFIG": "~/.kube/config",
        "PYTHONPATH": "/FULL/PATH/TO/k8s-bot"
      }
    }
  }
}
```

**Important:** Replace `/FULL/PATH/TO/k8s-bot` with the actual path where you cloned the repo.

Example for macOS:
```json
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "/Users/johndoe/projects/k8s-bot/venv/bin/python3",
      "args": ["/Users/johndoe/projects/k8s-bot/src/mcp_server.py"],
      "env": {
        "KUBECONFIG": "/Users/johndoe/.kube/config",
        "PYTHONPATH": "/Users/johndoe/projects/k8s-bot"
      }
    }
  }
}
```

### Step 4: Test MCP Server

```bash
cd k8s-bot
source venv/bin/activate
python src/mcp_server.py --help
```

Expected: Server should start without errors.

### Step 5: Restart Cursor

Completely quit and restart Cursor IDE.

---

## Enterprise Cluster Setup

For enterprise Kubernetes clusters that require authentication:

### Option A: Pre-authenticate Before Starting Cursor

```bash
# Authenticate with your enterprise CLI
eiamcli login

# Verify authentication
kubectl get nodes

# Then start Cursor
open -a "Cursor"
```

### Option B: Configure KUBECONFIG in mcp.json

Point to your enterprise kubeconfig:

```json
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "/path/to/venv/bin/python3",
      "args": ["/path/to/src/mcp_server.py"],
      "env": {
        "KUBECONFIG": "/path/to/enterprise-kubeconfig",
        "PYTHONPATH": "/path/to/k8s-bot"
      }
    }
  }
}
```

---

## Multi-Cluster Configuration

To work with multiple clusters, you have two options:

### Option 1: Single KUBECONFIG with Multiple Contexts

Merge your kubeconfigs:
```bash
export KUBECONFIG=~/.kube/config:~/.kube/dev-config:~/.kube/prod-config
kubectl config view --flatten > ~/.kube/merged-config
```

Then use merged config in mcp.json:
```json
"KUBECONFIG": "/Users/you/.kube/merged-config"
```

Use skill commands to switch:
> "Switch context to production cluster"

### Option 2: Separate MCP Servers per Cluster

Configure multiple servers in mcp.json:

```json
{
  "mcpServers": {
    "kubectl-ai-dev": {
      "command": "/path/to/venv/bin/python3",
      "args": ["/path/to/src/mcp_server.py"],
      "env": {
        "KUBECONFIG": "/path/to/dev-kubeconfig",
        "PYTHONPATH": "/path/to/k8s-bot"
      }
    },
    "kubectl-ai-prod": {
      "command": "/path/to/venv/bin/python3",
      "args": ["/path/to/src/mcp_server.py"],
      "env": {
        "KUBECONFIG": "/path/to/prod-kubeconfig",
        "PYTHONPATH": "/path/to/k8s-bot"
      }
    }
  }
}
```

---

## Using the Skill in Cursor

Once setup is complete, you can use natural language queries:

### Basic Commands

| Query | What it does |
|-------|--------------|
| "List all pods" | Shows pods across all namespaces |
| "Show deployments in production" | Lists deployments in production namespace |
| "Describe pod nginx-xyz" | Gets detailed pod information |
| "Why is my pod failing?" | Diagnoses pod issues |
| "Check cluster health" | Runs health check with score |
| "Run security audit" | Scans for security vulnerabilities |
| "Scale nginx to 5 replicas" | Scales deployment |
| "Show logs for payment-service" | Retrieves container logs |

### Invoking the Skill

You can reference the skill directly:
> "@SKILL.md why is the payment-service pod crashing?"

Or just ask naturally (Cursor auto-detects kubectl-ai relevance):
> "What pods are in CrashLoopBackOff?"

---

## Troubleshooting

### MCP Server Not Appearing

**Symptom:** kubectl-ai not listed in Cursor's MCP tools

**Fix:**
1. Verify `~/.cursor/mcp.json` syntax (valid JSON)
2. Ensure Python path is absolute (not relative)
3. Restart Cursor completely (Cmd+Q, not just close window)
4. Check MCP server starts manually:
   ```bash
   /path/to/venv/bin/python3 /path/to/src/mcp_server.py
   ```

### Module Not Found Errors

**Symptom:** `ModuleNotFoundError: No module named 'src'`

**Fix:** Ensure `PYTHONPATH` is set in mcp.json:
```json
"env": {
  "PYTHONPATH": "/full/path/to/k8s-bot"
}
```

### Kubectl Connection Refused

**Symptom:** `Unable to connect to the server`

**Fix:**
1. Verify kubectl works in terminal:
   ```bash
   kubectl cluster-info
   ```
2. For enterprise clusters, re-authenticate:
   ```bash
   eiamcli login
   ```
3. Check KUBECONFIG path in mcp.json is correct

### Permission Denied

**Symptom:** `Forbidden` or RBAC errors

**Fix:** Verify your cluster permissions:
```bash
kubectl auth can-i get pods --all-namespaces
```

---

## Directory Structure

```
k8s-bot/
├── SKILL.md              # Skill definition (copy to your skills repo)
├── SETUP.md              # This setup guide
├── requirements.txt      # Python dependencies
├── scripts/
│   └── setup-mcp.sh      # Automated setup script
├── src/
│   ├── mcp_server.py     # MCP server (connects Cursor to kubectl)
│   ├── main.py           # CLI entry point
│   ├── agent/            # AI agent logic
│   ├── k8s/              # Kubernetes operations
│   └── llm/              # LLM provider integrations
└── docs/                 # Additional documentation
```

---

## Updating the Skill

When a new version is released:

```bash
cd k8s-bot
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

Then restart Cursor.

---

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/your-org/k8s-bot/issues)
- **Slack:** #kubectl-ai-support
- **Docs:** See `docs/` folder for detailed documentation

---

## Security Notes

1. **Never commit kubeconfigs** — Keep them outside the repo
2. **Use namespace restrictions** — Limit access to specific namespaces
3. **Review commands** — The skill shows commands before execution
4. **Audit logs** — Check cluster audit logs for operations
