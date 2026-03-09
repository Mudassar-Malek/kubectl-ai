# kubectl-ai Features

A comprehensive list of all features that make kubectl-ai unique from other Kubernetes tools.

---

## Core Features

### 1. Natural Language Interface
Talk to your Kubernetes cluster like you would talk to a colleague.

```
You: "Why is my pod failing?"
Bot: [Automatically checks pod status, events, logs, and explains the issue]
```

**Supported queries:**
- "Show me all pods"
- "Why is my deployment not working?"
- "Scale nginx to 5 replicas"
- "What happened in the last hour?"

---

### 2. Agentic AI (Multi-Step Reasoning)
Unlike simple chatbots, kubectl-ai can take multiple autonomous steps to solve problems.

```
User: "Why is my app slow?"

Bot thinks:
  1. Let me check the pods... 
  2. Found high CPU usage, let me check resource limits...
  3. Let me look at recent events...
  4. Checking HPA status...
  
Bot: "Your app is slow because pod 'api-server' is hitting its CPU limit. 
     It's using 100% of its 500m CPU limit. Consider increasing the limit 
     or adding more replicas."
```

---

### 3. Pre-Hook Approval System
Every kubectl command requires human approval before execution.

```
╭────────────────────────────── Command Approval ──────────────────────────────╮
│ 📋 Command to Execute                                                        │
│                                                                              │
│ kubectl get pods --all-namespaces                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
Execute this command? [Y/n]: 
```

**Benefits:**
- Full visibility into what commands run
- Prevent accidental destructive operations
- Audit trail of executed commands

---

### 4. Free Local LLM Support (Ollama)
Run completely offline with no API costs using Ollama.

| Provider | Cost | Speed | Privacy |
|----------|------|-------|---------|
| Ollama (local) | Free | Slower | Full privacy |
| Claude API | Paid | Fast | Cloud-based |

**Supported models:**
- `llama3.2:1b` - Fast, basic accuracy
- `llama3.2:3b` - Balanced
- `llama3.1:8b` - Best quality (needs GPU)

---

## Advanced Features

### 5. Cluster Health Score
Get an instant health overview of your entire cluster.

```bash
python -m src.main health
```

**Output:**
```
══════════════════════════════════════════════════
  CLUSTER HEALTH SCORE: 85/100 🟢
══════════════════════════════════════════════════

✅ Nodes: 3/3 nodes ready
✅ Pods: 45/45 pods running
⚠️ Deployments: 8/9 fully available
   └─ 1 deployment(s) degraded
✅ Services: 12 services with endpoints
✅ Storage: 5/5 PVCs bound

══════════════════════════════════════════════════
```

**Checks performed:**
- Node health and readiness
- Pod status across all namespaces
- Deployment replica availability
- Service endpoint health
- PVC binding status

---

### 6. Security Audit
Automated security scanning for common misconfigurations.

```bash
python -m src.main security
```

**Output:**
```
══════════════════════════════════════════════════
  SECURITY AUDIT SCORE: 65/100
══════════════════════════════════════════════════

🔴 CRITICAL (2 issues)
────────────────────────────────────────
  • Container running in privileged mode
    Resource: kube-system/debug-pod
    Fix: Remove privileged: true from securityContext

🟠 HIGH (3 issues)
────────────────────────────────────────
  • Container may run as root
    Resource: default/api-server
    Fix: Set runAsNonRoot: true in securityContext

🟡 MEDIUM (5 issues)
────────────────────────────────────────
  • No resource limits defined
    Resource: default/worker-pod
    Fix: Add resources.limits.cpu and resources.limits.memory

══════════════════════════════════════════════════
```

**Security checks:**
- Privileged containers
- Containers running as root
- Missing resource limits
- Default service account usage
- Network policies presence

---

### 7. Error Explanation Mode
Deep diagnosis of why resources are failing.

```
You: "Explain why my-app pod is failing"

Bot: === Diagnosis for pod/my-app ===

--- Recent Events ---
Warning  FailedScheduling  2m   default-scheduler  0/3 nodes are available: 
         3 Insufficient memory

--- Analysis ---
Your pod cannot be scheduled because no nodes have enough memory.
The pod requests 8Gi but the largest available is 4Gi.

--- Recommendations ---
1. Reduce memory request in pod spec
2. Add a node with more memory
3. Check if other pods can be evicted
```

---

### 8. YAML Generation from Natural Language
Create Kubernetes resources using plain English.

```
You: "Generate a deployment for nginx with 3 replicas and 512MB memory"

Bot: Here's your deployment YAML:

apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        resources:
          limits:
            memory: "512Mi"

Save to file and run: kubectl apply -f deployment.yaml
```

---

### 9. Multi-Cluster Support
Works with any Kubernetes platform:

| Platform | Support |
|----------|---------|
| Minikube | ✅ Full |
| Kind | ✅ Full |
| Docker Desktop | ✅ Full |
| AWS EKS | ✅ Full |
| Azure AKS | ✅ Full |
| Google GKE | ✅ Full |
| Custom clusters | ✅ Full |

**Context management:**
```bash
# List contexts
python -m src.main contexts

# Switch context
python -m src.main switch production-eks
```

---

### 10. Safety Features
Built-in protection against dangerous operations.

**Risk Levels:**
| Level | Operations | Behavior |
|-------|------------|----------|
| Safe | get, describe, logs | Execute normally |
| Moderate | scale, rollout | Confirm required |
| Dangerous | delete, drain | Strong warning + confirm |
| Critical | delete namespace | Blocked or requires force |

**Blocked Patterns:**
- Shell injection: `;`, `|`, `&&`, `||`
- Command substitution: `$()`, backticks
- Redirections: `>`, `<`

---

## Integration Features

### 11. Slack Integration
Deploy the bot to Slack for team access.

```
@k8s-bot show me all pods
@k8s-bot why is production down?
```

Features:
- Mention support (@k8s-bot)
- Direct messages
- Slash commands (/k8s)

---

### 12. MCP (Model Context Protocol) Ready
Can be exposed as an MCP server for use with Claude and other AI assistants.

```json
{
  "mcpServers": {
    "kubectl-ai": {
      "command": "python",
      "args": ["-m", "src.mcp_server"]
    }
  }
}
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `python -m src.main chat` | Interactive chat mode |
| `python -m src.main ask "query"` | Single question mode |
| `python -m src.main health` | Cluster health check |
| `python -m src.main security` | Security audit |
| `python -m src.main contexts` | List K8s contexts |
| `python -m src.main switch <name>` | Switch context |
| `python -m src.main validate` | Validate setup |

---

## Available Tools

The AI agent has access to these tools:

### Read Operations
| Tool | Description |
|------|-------------|
| `kubectl_get` | List resources (pods, deployments, etc.) |
| `kubectl_describe` | Get detailed resource info |
| `kubectl_logs` | View container logs |
| `kubectl_get_events` | View cluster events |
| `kubectl_top` | Resource usage metrics |
| `kubectl_explain` | API documentation |

### Write Operations (Requires Confirmation)
| Tool | Description |
|------|-------------|
| `kubectl_scale` | Scale deployments |
| `kubectl_rollout` | Manage rollouts |
| `kubectl_apply` | Apply configurations |
| `kubectl_delete` | Delete resources |
| `kubectl_exec` | Execute in containers |

### Special Tools
| Tool | Description |
|------|-------------|
| `cluster_health` | Get health score |
| `security_audit` | Run security checks |
| `explain_error` | Diagnose failures |
| `generate_yaml` | Create YAML from description |

---

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | LLM provider (ollama/anthropic) |
| `K8S_BOT_MODEL` | `llama3.2:3b` | Model to use |
| `K8S_BOT_CONFIRM_COMMANDS` | `false` | Require approval for commands |
| `K8S_BOT_SAFE_MODE` | `true` | Enable safety checks |
| `K8S_BOT_DRY_RUN` | `false` | Show commands without executing |
| `K8S_BOT_TIMEOUT` | `30` | Command timeout (seconds) |
| `KUBECONFIG` | `~/.kube/config` | Kubeconfig path |

---

## What Makes kubectl-ai Unique

| Feature | kubectl-ai | k9s | Lens | kubectl-ai (others) |
|---------|------------|-----|------|---------------------|
| Natural Language | ✅ | ❌ | ❌ | Some |
| Agentic (Multi-step) | ✅ | ❌ | ❌ | Rare |
| Free Local LLM | ✅ | N/A | N/A | Rare |
| Pre-hook Approval | ✅ | ❌ | ❌ | ❌ |
| Health Scoring | ✅ | Partial | ✅ | ❌ |
| Security Audit | ✅ | ❌ | Partial | ❌ |
| Error Explanation | ✅ | ❌ | ❌ | ❌ |
| YAML Generation | ✅ | ❌ | ❌ | Some |
| MCP Compatible | ✅ | ❌ | ❌ | ❌ |
| Slack Integration | ✅ | ❌ | ❌ | Some |

---

## Roadmap (Future Features)

- [ ] **Runbook Integration** - Store and execute common troubleshooting runbooks
- [ ] **Learning Mode** - Bot learns from your patterns
- [ ] **Cost Awareness** - Estimate cloud costs for resources
- [ ] **Multi-Cluster Comparison** - Diff between clusters
- [ ] **Incident Timeline** - Visual timeline of events
- [ ] **Predictive Scaling** - Suggest scaling based on patterns
- [ ] **GitOps Integration** - Show what changed since last deploy
- [ ] **Compliance Checks** - SOC2, HIPAA, PCI compliance scanning
- [ ] **Voice Commands** - Voice interface support

---

## Quick Start

```bash
# Install
git clone https://github.com/yourusername/kubectl-ai
cd kubectl-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
python -m src.main chat
```

---

## Examples

### Basic Queries
```
"show me all pods"
"list deployments in kube-system"
"get services"
```

### Troubleshooting
```
"why is my pod failing?"
"explain the error for api-server pod"
"what events happened recently?"
```

### Operations
```
"scale nginx to 5 replicas"
"restart the api deployment"
"show logs from web-app"
```

### Analysis
```
"check cluster health"
"run security audit"
"compare staging vs production"
```

##What Makes kubectl-ai Unique
✅ Pre-hook approval system
✅ Free local LLM (Ollama)
✅ Cluster health scoring
✅ Security auditing
✅ Error explanation mode
✅ YAML generation
✅ Agentic multi-step reasoning
✅ MCP compatible (ready to implement)
All documentation is in docs/FEATURES.md.

---

That's everything kubectl-ai can do!
