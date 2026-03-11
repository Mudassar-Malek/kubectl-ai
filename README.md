# K8s IntelliBot

An **agentic AI-powered chatbot** for Kubernetes management. Ask questions about your clusters in natural language, and the bot will autonomously execute kubectl commands, diagnose issues, and provide intelligent responses.

**No API key required!** Uses Ollama for free, local AI inference.

## Features

- **100% Free**: Uses Ollama for local LLM inference - no API costs
- **Natural Language Interface**: Ask questions like "Why is my nginx deployment failing?" instead of memorizing kubectl syntax
- **Agentic AI**: Autonomous multi-step reasoning - the bot gathers information, diagnoses issues, and suggests solutions
- **Multi-Platform Support**: Works with Minikube, AWS EKS, Azure AKS, Google GKE, Kind, and more
- **Safety First**: Destructive operations require confirmation; supports dry-run mode
- **Beautiful CLI**: Rich terminal interface with formatted output
- **Fully Portable**: Clone, configure, and run in minutes
- **MCP Server**: Use as an MCP server with Cursor IDE - Claude can directly query your clusters!
- **Cluster Health Score**: Instant health overview with actionable insights
- **Security Audit**: Automated security scanning for misconfigurations

---

## 🚀 MCP Server Setup (Use with Cursor IDE)

The fastest way to use kubectl-ai is as an MCP server with Cursor. Claude can then directly query your Kubernetes clusters!

```bash
# Clone and setup
git clone https://github.com/Mudassar-Malek/kubectl-ai.git
cd kubectl-ai
./scripts/setup-mcp.sh

# Restart Cursor, then ask Claude:
# "Show me all pods in my cluster"
# "Check the health of my Kubernetes cluster"
# "Run a security audit"
```

**That's it!** No Ollama needed - Claude is the AI. See [MCP Setup Guide](docs/MCP_SETUP.md) for details.

---

## Quick Start with Minikube (5 Minutes)

### Prerequisites

- Python 3.10+
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- [Ollama](https://ollama.ai) installed (for free local AI)

### Step 1: Set Up Ollama (Free Local AI)

```bash
# Install Ollama (macOS)
brew install ollama

# Or on Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# In a new terminal, pull the AI model (one-time download ~4GB)
ollama pull llama3.1:8b
```

### Step 2: Start Minikube

```bash
# Start Minikube cluster
minikube start

# Verify it's running
kubectl get nodes
```

### Step 3: Install K8s IntelliBot

```bash
# Clone the repository
git clone https://github.com/your-org/k8s-intellibot.git
cd k8s-intellibot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy the default configuration
cp .env.example .env
```

### Step 4: Run the Bot

```bash
# Validate everything is set up correctly
python -m src.main validate

# Start interactive mode
python -m src.main
```

That's it! No API keys needed. The bot uses your local Ollama instance.

### Configuration

Edit `.env` to customize settings:

```bash
# LLM Provider: "ollama" (free, local) or "anthropic" (paid API)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
K8S_BOT_MODEL=llama3.1:8b

# Alternative models (smaller/faster):
# K8S_BOT_MODEL=llama3.2:3b
# K8S_BOT_MODEL=mistral:7b

# Bot settings
K8S_BOT_SAFE_MODE=true      # Require confirmation for destructive operations
K8S_BOT_DRY_RUN=false       # Enable dry-run mode by default
K8S_BOT_TIMEOUT=30          # Command timeout in seconds

# Kubernetes
KUBECONFIG=~/.kube/config
```

### Using Anthropic Claude (Optional)

If you prefer Claude API (paid):

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
K8S_BOT_MODEL=claude-sonnet-4-20250514
```

---

## Minikube Live Demo

Follow this guide to set up a demo environment with sample workloads to test K8s IntelliBot.

### 1. Deploy Sample Applications

```bash
# Create a demo namespace
kubectl create namespace demo

# Deploy nginx
kubectl create deployment nginx --image=nginx:latest -n demo
kubectl expose deployment nginx --port=80 --type=ClusterIP -n demo

# Deploy redis
kubectl create deployment redis --image=redis:alpine -n demo
kubectl expose deployment redis --port=6379 --type=ClusterIP -n demo

# Deploy a failing pod (for troubleshooting demo)
kubectl create deployment buggy-app --image=busybox -n demo -- /bin/sh -c "exit 1"

# Deploy a pending pod (missing resources)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: pending-pod
  namespace: demo
spec:
  containers:
  - name: app
    image: nginx
    resources:
      requests:
        memory: "100Gi"  # Impossible to schedule
EOF

# Check the deployments
kubectl get all -n demo
```

### 2. Demo Scenarios

Start the bot and try these scenarios:

```bash
python -m src.main
```

**Scenario 1: Basic Exploration**
```
You: Show me all pods in the demo namespace
You: What deployments are running?
You: Describe the nginx service
```

**Scenario 2: Troubleshooting a Failing Pod**
```
You: Why is the buggy-app deployment failing?
```
The bot will:
1. Check the deployment status
2. Describe the pods
3. Check events
4. Diagnose the "CrashLoopBackOff" issue

**Scenario 3: Investigating Pending Pods**
```
You: Why is the pending-pod not running?
```
The bot will:
1. Get pod status
2. Describe the pod
3. Identify insufficient resources

**Scenario 4: Scaling Operations**
```
You: Scale the nginx deployment to 3 replicas
You: Show me the pods now
```

**Scenario 5: Log Analysis**
```
You: Get the logs from nginx pods in demo namespace
You: Show me recent events in demo namespace
```

**Scenario 6: Resource Usage**
```
You: What's using the most memory in the cluster?
You: Show me node resource usage
```

### 3. Clean Up Demo

```bash
kubectl delete namespace demo
```

### Useful Minikube Commands

```bash
# Check Minikube status
minikube status

# Access Minikube dashboard
minikube dashboard

# Get Minikube IP
minikube ip

# SSH into Minikube node
minikube ssh

# Stop Minikube (preserves state)
minikube stop

# Delete Minikube cluster
minikube delete
```

---

## Usage

### Interactive Mode

Start an interactive session:

```bash
$ python -m src.main

╔═══════════════════════════════════════════════════════════════╗
║             🤖 K8s IntelliBot - Kubernetes AI Assistant       ║
╚═══════════════════════════════════════════════════════════════╝

┌─ Current Cluster ─────────────────────────────────────────────┐
│ Context:   minikube                                           │
│ Cluster:   minikube                                           │
│ Platform:  minikube                                           │
│ Namespace: default                                            │
└───────────────────────────────────────────────────────────────┘

You: Show me all pods in the default namespace

┌───────────────────────────────────────────────────────────────┐
│ Here are the pods in the default namespace:                   │
│                                                               │
│ | NAME          | READY | STATUS  | RESTARTS | AGE |         │
│ |---------------|-------|---------|----------|-----|         │
│ | nginx-abc123  | 1/1   | Running | 0        | 2d  |         │
│ | redis-xyz789  | 1/1   | Running | 0        | 5d  |         │
│                                                               │
│ All pods are running healthy.                                 │
└───────────────────────────────────────────────────────────────┘
(1 tool calls made)

You:
```

### Example Queries

**Simple queries:**
- "Show me all pods"
- "List deployments in the production namespace"
- "Get the logs from the api-server pod"
- "What services are running?"

**Troubleshooting:**
- "Why is my nginx deployment not working?"
- "Why are my pods pending?"
- "Debug the crash loop in the worker pod"
- "What's using the most memory?"

**Operations:**
- "Scale the web deployment to 5 replicas"
- "Restart the api-server deployment"
- "Switch to my EKS production cluster"

### CLI Commands

```bash
# Single query mode
python -m src.main ask "show me all pods"

# List contexts
python -m src.main contexts

# Switch context
python -m src.main switch my-eks-cluster

# Validate connection
python -m src.main validate

# Run with dry-run mode
python -m src.main --dry-run

# Debug mode
python -m src.main --debug
```

### In-Session Commands

| Command | Description |
|---------|-------------|
| `help` | Show help message |
| `quit` / `exit` | Exit the chatbot |
| `clear` | Clear conversation history |
| `context` | Show current cluster context |
| `contexts` | List all available contexts |
| `switch <name>` | Switch to a different context |

## Docker Usage

### Build and Run

```bash
# Build the image
docker build -t k8s-intellibot:latest .

# Run with docker-compose
docker-compose up k8s-bot
```

### Docker Compose

The `docker-compose.yml` automatically mounts:
- `~/.kube` - Kubernetes config
- `~/.aws` - AWS credentials (for EKS)
- `~/.config/gcloud` - Google Cloud credentials (for GKE)
- `~/.azure` - Azure credentials (for AKS)

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run
docker-compose up k8s-bot
```

## Platform-Specific Setup

### Minikube / Podman (Recommended for Learning)

```bash
# Install Minikube (macOS)
brew install minikube

# Install Minikube (Linux)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start with default driver (Docker)
minikube start

# Or with Podman driver
minikube start --driver=podman

# With more resources for better performance
minikube start --cpus=4 --memory=8192

# Enable useful addons
minikube addons enable metrics-server
minikube addons enable dashboard

# Verify connection
kubectl get nodes
python -m src.main validate
```

### AWS EKS

```bash
# Configure AWS CLI
aws configure

# Update kubeconfig for your cluster
aws eks update-kubeconfig --name my-cluster --region us-east-1

# Run the bot
python -m src.main
```

### Azure AKS

```bash
# Login to Azure
az login

# Get credentials
az aks get-credentials --resource-group myResourceGroup --name myAKSCluster

# Run the bot
python -m src.main
```

### Google GKE

```bash
# Authenticate with Google Cloud
gcloud auth login

# Get credentials
gcloud container clusters get-credentials my-cluster --zone us-central1-a

# Run the bot
python -m src.main
```

## Safety Features

K8s IntelliBot includes multiple safety features:

1. **Confirmation Required**: Destructive operations (delete, apply, scale) require explicit confirmation
2. **Dry-Run Mode**: Test commands without making changes: `--dry-run`
3. **Command Validation**: Dangerous patterns (command chaining, pipes) are blocked
4. **Risk Assessment**: Each command is classified by risk level

### Risk Levels

| Level | Operations | Behavior |
|-------|------------|----------|
| Safe | get, describe, logs | Execute immediately |
| Moderate | scale, exec | Execute (confirmation optional) |
| Dangerous | apply, create | Requires confirmation |
| Critical | delete, drain | Requires confirmation |

## Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linters
make lint

# Format code
make format
```

### Project Structure

```
k8s-bot/
├── src/
│   ├── main.py              # CLI entry point
│   ├── agent/
│   │   ├── core.py          # Agentic AI loop
│   │   ├── tools.py         # kubectl tool definitions
│   │   ├── prompts.py       # System prompts
│   │   └── memory.py        # Conversation history
│   ├── k8s/
│   │   ├── executor.py      # Safe kubectl execution
│   │   ├── contexts.py      # Multi-cluster management
│   │   ├── validators.py    # Command validation
│   │   └── parser.py        # Output parsing
│   └── utils/
│       ├── config.py        # Configuration
│       └── logger.py        # Logging
├── tests/                   # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Slack Integration

Integrate K8s IntelliBot with Slack to manage your Kubernetes clusters from your team's Slack workspace.

### Step 1: Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name it "K8s IntelliBot" and select your workspace
4. Click **Create App**

### Step 2: Configure Bot Permissions

1. Go to **OAuth & Permissions** in the sidebar
2. Under **Scopes** → **Bot Token Scopes**, add:
   - `app_mentions:read` - Respond when mentioned
   - `chat:write` - Send messages
   - `channels:history` - Read channel messages (optional)
   - `im:history` - Read DM messages (optional)

### Step 3: Enable Socket Mode

1. Go to **Socket Mode** in the sidebar
2. Toggle **Enable Socket Mode** ON
3. Give your token a name (e.g., "k8s-bot-socket")
4. Copy the **App-Level Token** (starts with `xapp-`)

### Step 4: Enable Events

1. Go to **Event Subscriptions**
2. Toggle **Enable Events** ON
3. Under **Subscribe to bot events**, add:
   - `app_mention` - Trigger on @mentions
   - `message.im` - Direct messages (optional)

### Step 5: Install the App

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Authorize the app
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 6: Configure Environment

Add to your `.env` file:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
```

### Step 7: Create the Slack Bot

Create `src/slack_bot.py`:

```python
"""Slack bot integration for K8s IntelliBot."""

import asyncio
import os
import re

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from src.agent.core import KubernetesAgent
from src.agent.tools import KUBERNETES_TOOLS
from src.k8s.contexts import ContextManager
from src.k8s.executor import KubectlExecutor, ToolExecutor
from src.utils.config import Config


# Initialize Slack app
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize K8s bot components
config = Config.load()
context_manager = ContextManager(config.kubeconfig)
kubectl_executor = KubectlExecutor(config)
tool_executor = ToolExecutor(kubectl_executor, context_manager)
agent = KubernetesAgent(
    config=config,
    tools=KUBERNETES_TOOLS,
    tool_executor=tool_executor.execute,
)


@app.event("app_mention")
async def handle_mention(event, say):
    """Handle @mentions of the bot."""
    text = event.get("text", "")
    # Remove the bot mention from the text
    query = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    
    if not query:
        await say("Hi! Ask me anything about your Kubernetes cluster. For example: 'Show me all pods'")
        return
    
    # Show typing indicator
    await say("Thinking... 🤔")
    
    # Process the query
    response = await agent.run(query)
    
    # Format response for Slack
    if response.success:
        message = f"```\n{response.text}\n```"
        if response.tool_calls_made > 0:
            message += f"\n_({response.tool_calls_made} kubectl commands executed)_"
    else:
        message = f"❌ Error: {response.text}"
    
    await say(message)


@app.event("message")
async def handle_dm(event, say):
    """Handle direct messages."""
    # Only respond to DMs, not channel messages
    if event.get("channel_type") != "im":
        return
    
    query = event.get("text", "").strip()
    if not query:
        return
    
    response = await agent.run(query)
    
    if response.success:
        await say(f"```\n{response.text}\n```")
    else:
        await say(f"❌ Error: {response.text}")


async def main():
    """Start the Slack bot."""
    handler = AsyncSocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
```

### Step 8: Install Slack Dependencies

```bash
pip install slack-bolt slack-sdk

# Or install the slack extras
pip install -e ".[slack]"
```

### Step 9: Run the Slack Bot

```bash
# Run the Slack bot
python -m src.slack_bot
```

### Usage in Slack

Once running, you can interact with the bot:

```
@K8s IntelliBot show me all pods in production

@K8s IntelliBot why is the api-server deployment failing?

@K8s IntelliBot scale web deployment to 5 replicas
```

### Docker Compose for Slack

Add to `docker-compose.yml`:

```yaml
services:
  k8s-bot-slack:
    build: .
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
      - SLACK_APP_TOKEN=${SLACK_APP_TOKEN}
    volumes:
      - ${HOME}/.kube:/home/k8sbot/.kube:ro
    command: python -m src.slack_bot
```

Run with:

```bash
docker-compose up k8s-bot-slack
```

### Security Considerations for Slack

1. **Restrict Access**: Only allow the bot in specific channels
2. **Audit Logging**: Enable logging for all commands executed
3. **Safe Mode**: Always run with `K8S_BOT_SAFE_MODE=true` in production
4. **Confirmation Flow**: Consider implementing Slack interactive buttons for destructive operations

---

## Troubleshooting

### Connection Issues

```bash
# Validate your setup
python -m src.main validate

# Check kubectl directly
kubectl cluster-info
kubectl get nodes
```

### API Key Issues

Ensure your `ANTHROPIC_API_KEY` is set correctly:

```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Test the key
python -c "from anthropic import Anthropic; print(Anthropic().models.list())"
```

### Permission Issues

If you see "Forbidden" errors, check your RBAC permissions:

```bash
kubectl auth can-i get pods
kubectl auth can-i list deployments
```

## Documentation

For deeper understanding of how K8s IntelliBot works:

| Document | Description |
|----------|-------------|
| [Architecture Guide](docs/ARCHITECTURE.md) | Complete code walkthrough, how the agentic loop works, module explanations |
| [Quick Reference](docs/QUICK_REFERENCE.md) | One-page cheat sheet for demos and quick explanations |

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with [Ollama](https://ollama.ai) for free local AI inference
- Optional [Anthropic Claude](https://anthropic.com) integration for premium API
- Uses [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Inspired by the Kubernetes community
