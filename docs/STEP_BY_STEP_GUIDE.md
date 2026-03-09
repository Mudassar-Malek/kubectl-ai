# K8s IntelliBot - Complete Step-by-Step Guide

This guide explains everything about the K8s IntelliBot from scratch. By the end, you'll understand exactly how it works.

---

## Table of Contents

1. [What is This Bot?](#1-what-is-this-bot)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [How to Run](#4-how-to-run)
5. [Understanding the Architecture](#5-understanding-the-architecture)
6. [Code Walkthrough](#6-code-walkthrough)
7. [How a Query is Processed](#7-how-a-query-is-processed)
8. [Configuration Options](#8-configuration-options)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. What is This Bot?

### Simple Explanation
K8s IntelliBot is a chatbot that helps you manage Kubernetes clusters using natural language. Instead of remembering complex kubectl commands, you just ask questions like:

- "Show me all pods"
- "Why is my deployment failing?"
- "Scale nginx to 5 replicas"

### What Makes It "Agentic"?
The bot can **think and act autonomously**:
1. It analyzes your question
2. Decides which kubectl commands to run
3. Executes them
4. Analyzes the results
5. Runs more commands if needed
6. Gives you a final answer

This is different from a simple chatbot - it takes **multiple steps** on its own.

### Key Features
- ✅ Natural language interface
- ✅ Works with Minikube, EKS, AKS, GKE
- ✅ Free to use (with Ollama)
- ✅ Safe - blocks dangerous commands
- ✅ Multi-step reasoning

---

## 2. Prerequisites

Before you start, you need:

### Required
| Tool | Purpose | Install Command |
|------|---------|-----------------|
| Python 3.10+ | Run the bot | `brew install python` |
| kubectl | Execute K8s commands | `brew install kubectl` |
| Ollama | Free AI model | `brew install ollama` |
| A K8s Cluster | Target cluster | Minikube, Kind, or cloud |

### For Minikube (Local Testing)
```bash
# Install Minikube
brew install minikube

# Start cluster
minikube start

# Verify
kubectl get nodes
```

### For Ollama (Free AI)
```bash
# Install
brew install ollama

# Start server
ollama serve

# Download model (in another terminal)
ollama pull llama3.2:3b
```

---

## 3. Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd k8s-bot
```

### Step 2: Create Virtual Environment
```bash
# Create
python3 -m venv venv

# Activate
source venv/bin/activate   # Mac/Linux
# OR
.\venv\Scripts\activate    # Windows
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
pip3 install -r requirements.txt

### Step 4: Configure Environment
```bash
# Copy example config
cp .env.example .env

# Edit .env file
nano .env
```

**Minimum .env file:**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
K8S_BOT_MODEL=llama3.2:3b
KUBECONFIG=/path/to/your/.kube/config
```

### Step 5: Validate Setup
```bash
python -m src.main validate
```

Expected output:
```
✓ Configuration loaded
✓ LLM Provider: Ollama (llama3.2:3b)
✓ Kubernetes cluster connected
```

---

## 4. How to Run

### Interactive Chat Mode
```bash
python -m src.main chat
```
Then type your questions. Type `exit` to quit.

### Single Query Mode
```bash
python -m src.main ask "show me all pods"
```

### List Kubernetes Contexts
```bash
python -m src.main contexts
```

### Switch Cluster
```bash
python -m src.main switch my-cluster-name
```

---

## 5. Understanding the Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR TERMINAL                         │
│                                                          │
│  You type: "Why is my pod failing?"                     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   K8s IntelliBot                         │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   CLI       │  │   Agent     │  │   LLM       │      │
│  │  (main.py)  │→ │  (core.py)  │→ │  (Ollama)   │      │
│  └─────────────┘  └──────┬──────┘  └─────────────┘      │
│                          │                               │
│                          ▼                               │
│                   ┌─────────────┐                        │
│                   │  Executor   │                        │
│                   │  (kubectl)  │                        │
│                   └──────┬──────┘                        │
└──────────────────────────┼──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               KUBERNETES CLUSTER                         │
│                                                          │
│   Pods, Deployments, Services, Nodes, etc.              │
└─────────────────────────────────────────────────────────┘
```

### Component Breakdown

| Component | File | Responsibility |
|-----------|------|----------------|
| **CLI** | `main.py` | Handles user input/output |
| **Agent** | `agent/core.py` | Orchestrates the thinking loop |
| **Memory** | `agent/memory.py` | Stores conversation history |
| **Tools** | `agent/tools.py` | Defines available kubectl commands |
| **Prompts** | `agent/prompts.py` | Instructions for the AI |
| **LLM Provider** | `llm/` | Communicates with AI (Ollama/Claude) |
| **Executor** | `k8s/executor.py` | Runs kubectl commands |
| **Validator** | `k8s/validators.py` | Ensures command safety |
| **Parser** | `k8s/parser.py` | Formats kubectl output |
| **Contexts** | `k8s/contexts.py` | Manages cluster connections |
| **Config** | `utils/config.py` | Loads settings |

---

## 6. Code Walkthrough

### File-by-File Explanation

#### `src/main.py` - The Entry Point

**What it does:** Handles the CLI interface

```python
@click.group()
def cli():
    """K8s IntelliBot CLI"""
    pass

@cli.command()
def chat():
    """Start interactive chat"""
    # Creates agent
    # Loops waiting for user input
    # Displays responses

@cli.command()
def ask(query):
    """Single query"""
    # Creates agent
    # Processes one query
    # Exits
```

**Key Functions:**
- `chat()` - Interactive mode
- `ask()` - Single query mode
- `validate()` - Check setup
- `process_query()` - Send query to agent

---

#### `src/agent/core.py` - The Brain

**What it does:** The main loop that thinks and acts

```python
class KubernetesAgent:
    def __init__(self, config, tools, tool_executor, llm_provider):
        self.memory = ConversationMemory()  # Conversation history
        self.tools = tools                   # Available kubectl commands
        self.tool_executor = tool_executor   # Function to run commands
        self.llm = llm_provider              # AI model
    
    async def process(self, user_query: str) -> str:
        # Step 1: Add user message to memory
        self.memory.add_message("user", user_query)
        
        # Step 2: The agentic loop
        while True:
            # Ask the LLM what to do
            response = self.llm.create_message(
                messages=self.memory.messages,
                system=SYSTEM_PROMPT,
                tools=self.tools
            )
            
            # If LLM wants to use a tool
            if response.stop_reason == "tool_use":
                # Execute the tool (kubectl command)
                results = await self._execute_tool_calls(response)
                # Add results to memory
                self.memory.add_tool_results(results)
                # Continue the loop
                continue
            
            # LLM has a final answer
            return response.text
```

**The Loop Visualized:**

```
┌──────────────────────────────────────────────────────┐
│                    AGENT LOOP                         │
│                                                       │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐        │
│  │  Ask    │ ──▶ │  LLM    │ ──▶ │ Check   │        │
│  │  LLM    │     │ Thinks  │     │ Response│        │
│  └─────────┘     └─────────┘     └────┬────┘        │
│       ▲                               │              │
│       │         ┌─────────────────────┴─────┐       │
│       │         │                           │        │
│       │         ▼                           ▼        │
│  ┌────┴────┐   Tool Call?              Text Answer? │
│  │ Add to  │   │                           │        │
│  │ Memory  │   ▼                           ▼        │
│  └─────────┘  ┌─────────┐            ┌─────────┐   │
│       ▲       │ Execute │            │ Return  │   │
│       │       │ kubectl │            │ to User │   │
│       │       └────┬────┘            └─────────┘   │
│       │            │                                 │
│       └────────────┘                                 │
│                                                       │
└──────────────────────────────────────────────────────┘
```

---

#### `src/agent/tools.py` - Available Commands

**What it does:** Defines what kubectl commands the bot can use

```python
KUBERNETES_TOOLS_LITE = [
    {
        "name": "kubectl_get",
        "description": "List Kubernetes resources",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "description": "pods, deployments, services, etc."
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace to query"
                }
            },
            "required": ["resource"]
        }
    },
    # kubectl_describe, kubectl_logs, kubectl_get_events...
]
```

**Available Tools:**

| Tool | kubectl Command | Use Case |
|------|-----------------|----------|
| `kubectl_get` | `kubectl get <resource>` | List resources |
| `kubectl_describe` | `kubectl describe <resource>` | Get details |
| `kubectl_logs` | `kubectl logs <pod>` | View container logs |
| `kubectl_get_events` | `kubectl get events` | See cluster events |

---

#### `src/agent/prompts.py` - AI Instructions

**What it does:** Tells the AI how to behave

```python
SYSTEM_PROMPT = """
You are K8s IntelliBot, a Kubernetes assistant.

Your capabilities:
- List and describe Kubernetes resources
- View logs and events
- Help troubleshoot issues

Rules:
1. Always use tools to get real cluster data
2. Verify before destructive operations
3. Explain your findings clearly
4. If unsure, ask for clarification

When using tools, respond with the tool name and arguments.
"""
```

---

#### `src/llm/ollama_provider.py` - AI Communication

**What it does:** Sends requests to Ollama and parses responses

```python
class OllamaProvider:
    def __init__(self, model="llama3.2:3b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def create_message(self, messages, system, tools):
        # Build the request
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False
        }
        
        # Send to Ollama
        response = requests.post(f"{self.base_url}/api/chat", json=payload)
        
        # Parse response - look for tool calls or text
        return self._parse_response(response.json())
    
    def _extract_tool_call(self, text):
        # Look for JSON like: {"tool": "kubectl_get", "arguments": {...}}
        # Extract and return as ToolCall object
        pass
```

---

#### `src/k8s/executor.py` - Command Execution

**What it does:** Safely runs kubectl commands

```python
class KubectlExecutor:
    def __init__(self, config, confirmation_handler):
        self.validator = CommandValidator()
        self.parser = OutputParser()
        self.config = config
    
    def execute(self, command: list[str]) -> str:
        # Step 1: Validate the command
        validation = self.validator.validate(command)
        
        if not validation.is_valid:
            raise SecurityError(validation.error)
        
        # Step 2: Check risk level
        if validation.risk_level == RiskLevel.DANGEROUS:
            if not self.confirm("This is dangerous. Continue?"):
                return "Cancelled by user"
        
        # Step 3: Execute
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=self.config.timeout
        )
        
        # Step 4: Parse and return output
        return self.parser.parse(result.stdout)
```

---

#### `src/k8s/validators.py` - Safety Checks

**What it does:** Prevents dangerous or malicious commands

```python
class CommandValidator:
    # Blocked patterns (shell injection prevention)
    BLOCKED_PATTERNS = [";", "|", "&&", "||", "$(", "`", ">", "<"]
    
    # Risk levels for different commands
    SAFE_COMMANDS = ["get", "describe", "logs", "top", "explain"]
    DANGEROUS_COMMANDS = ["delete", "drain", "cordon", "taint"]
    CRITICAL_COMMANDS = ["delete namespace", "delete node"]
    
    def validate(self, command: list[str]) -> ValidationResult:
        command_str = " ".join(command)
        
        # Check for blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in command_str:
                return ValidationResult(
                    is_valid=False,
                    error=f"Blocked pattern: {pattern}"
                )
        
        # Determine risk level
        risk = self._assess_risk(command)
        
        return ValidationResult(is_valid=True, risk_level=risk)
```

---

#### `src/agent/memory.py` - Conversation History

**What it does:** Keeps track of the conversation

```python
@dataclass
class Message:
    role: str       # "user", "assistant", or "tool"
    content: Any    # Text or tool results

class ConversationMemory:
    def __init__(self):
        self.messages = []
    
    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
    
    def add_tool_result(self, tool_id: str, result: str):
        self.messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "content": result}]
        })
```

---

## 7. How a Query is Processed

Let's trace what happens when you ask: **"Why is my nginx pod failing?"**

### Step-by-Step Trace

```
STEP 1: User Input
──────────────────
User types: "Why is my nginx pod failing?"
File: main.py → process_query()


STEP 2: Send to Agent
─────────────────────
main.py calls: agent.process("Why is my nginx pod failing?")
File: agent/core.py


STEP 3: Add to Memory
─────────────────────
memory.messages = [
    {"role": "user", "content": "Why is my nginx pod failing?"}
]


STEP 4: Ask LLM (First Call)
────────────────────────────
Agent sends to Ollama:
- System prompt (who you are, what tools you have)
- Conversation history
- Available tools

LLM responds:
{"tool": "kubectl_get", "arguments": {"resource": "pods"}}


STEP 5: Execute Tool
────────────────────
executor.py runs: kubectl get pods

Output:
NAME         READY   STATUS             RESTARTS   AGE
nginx-pod    0/1     CrashLoopBackOff   5          10m


STEP 6: Add Result to Memory
────────────────────────────
memory.messages = [
    {"role": "user", "content": "Why is my nginx pod failing?"},
    {"role": "assistant", "content": [tool_call]},
    {"role": "user", "content": [tool_result: "NAME nginx-pod..."]}
]


STEP 7: Ask LLM (Second Call)
─────────────────────────────
Agent sends updated conversation to LLM.

LLM sees the pod is in CrashLoopBackOff and responds:
{"tool": "kubectl_logs", "arguments": {"pod": "nginx-pod"}}


STEP 8: Execute Tool
────────────────────
executor.py runs: kubectl logs nginx-pod

Output:
Error: Cannot find /etc/nginx/nginx.conf
nginx: configuration file not found


STEP 9: Add Result to Memory
────────────────────────────
Memory now has full conversation + both tool results.


STEP 10: Ask LLM (Third Call)
─────────────────────────────
LLM now has enough information.

LLM responds with TEXT (not a tool call):
"Your nginx pod is failing because the configuration file
is missing. The error shows 'Cannot find /etc/nginx/nginx.conf'.

To fix this:
1. Check if your ConfigMap with nginx.conf exists
2. Verify the volume mount in your pod spec
3. Recreate the pod after fixing the config"


STEP 11: Return to User
───────────────────────
Agent returns the text response.
main.py displays it in a nice panel.


DONE!
```

### Sequence Diagram

```
User          main.py        Agent         LLM           Executor      Cluster
  │              │              │            │               │            │
  │─"Why fail?"─▶│              │            │               │            │
  │              │─process()───▶│            │               │            │
  │              │              │─ask()─────▶│               │            │
  │              │              │◀─tool_call─│               │            │
  │              │              │─execute()─────────────────▶│            │
  │              │              │            │               │─kubectl───▶│
  │              │              │            │               │◀──output───│
  │              │              │◀─result────────────────────│            │
  │              │              │─ask()─────▶│               │            │
  │              │              │◀─tool_call─│               │            │
  │              │              │─execute()─────────────────▶│            │
  │              │              │            │               │─kubectl───▶│
  │              │              │◀─result────────────────────│◀──output───│
  │              │              │─ask()─────▶│               │            │
  │              │              │◀─text──────│               │            │
  │              │◀─response────│            │               │            │
  │◀─display─────│              │            │               │            │
  │              │              │            │               │            │
```

---

## 8. Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | AI provider: `ollama` or `anthropic` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `K8S_BOT_MODEL` | `llama3.2:3b` | Model to use |
| `K8S_BOT_SAFE_MODE` | `true` | Require confirmation for dangerous ops |
| `K8S_BOT_DRY_RUN` | `false` | Show commands without executing |
| `K8S_BOT_TIMEOUT` | `30` | Command timeout in seconds |
| `KUBECONFIG` | `~/.kube/config` | Path to kubeconfig |

### Example Configurations

**Local Development (Free)**
```bash
LLM_PROVIDER=ollama
K8S_BOT_MODEL=llama3.2:3b
KUBECONFIG=~/.kube/config
```

**Production (Faster)**
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
K8S_BOT_MODEL=claude-sonnet-4-20250514
KUBECONFIG=/etc/kubernetes/admin.conf
```

---

## 9. Troubleshooting

### Common Issues

#### "Connection refused to localhost:11434"
```bash
# Ollama not running. Start it:
ollama serve
```

#### "Model not found"
```bash
# Download the model:
ollama pull llama3.2:3b
```

#### "Cannot connect to cluster"
```bash
# Check kubectl works:
kubectl get nodes

# Set KUBECONFIG in .env:
KUBECONFIG=/full/path/to/.kube/config
```

#### "Request timeout"
The 3B model on CPU takes 50-100 seconds per response. This is normal.

For faster responses:
- Use a GPU machine
- Use Anthropic Claude API

#### "Command blocked"
The bot blocks dangerous patterns like `;`, `|`, `&&` for security.

---

## Summary

### The Bot in One Paragraph

K8s IntelliBot is an **agentic AI chatbot** that uses an LLM (Ollama or Claude) to understand natural language questions about Kubernetes. When you ask a question, the **Agent** (`core.py`) enters a loop: it asks the **LLM** what to do, the LLM requests **tools** (kubectl commands), the **Executor** runs them safely, and the results go back to the LLM. This continues until the LLM has enough information to give a final answer. The **Memory** keeps track of the conversation, and the **Validator** ensures no dangerous commands are executed.

### Key Takeaways

1. **Entry Point**: `main.py` - handles CLI
2. **Brain**: `agent/core.py` - the thinking loop
3. **AI**: `llm/ollama_provider.py` - talks to the model
4. **Execution**: `k8s/executor.py` - runs kubectl
5. **Safety**: `k8s/validators.py` - blocks bad commands

That's everything you need to understand the K8s IntelliBot!
