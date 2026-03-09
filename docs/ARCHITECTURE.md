# K8s IntelliBot - Architecture & Code Walkthrough

This document explains how K8s IntelliBot works, step by step. Perfect for understanding the codebase or explaining it to others.

---

## Table of Contents

1. [What is K8s IntelliBot?](#what-is-k8s-intellibot)
2. [High-Level Architecture](#high-level-architecture)
3. [How a Query Flows Through the System](#how-a-query-flows-through-the-system)
4. [The Agentic AI Loop Explained](#the-agentic-ai-loop-explained)
5. [Project Structure](#project-structure)
6. [Module Deep Dive](#module-deep-dive)
7. [LLM Providers](#llm-providers)
8. [Safety Features](#safety-features)
9. [Common Questions](#common-questions)

---

## What is K8s IntelliBot?

K8s IntelliBot is an **AI-powered chatbot** that lets you manage Kubernetes clusters using natural language instead of memorizing kubectl commands.

**Example:**
- Instead of: `kubectl get pods -n production -l app=nginx --sort-by=.status.startTime`
- You say: "Show me nginx pods in production sorted by start time"

The bot understands your intent, figures out which kubectl commands to run, executes them, and explains the results.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER                                       │
│                     "Why is my pod failing?"                         │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI (src/main.py)                             │
│                   Beautiful terminal interface                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AGENT (src/agent/core.py)                         │
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │   Memory     │    │  LLM Client  │    │    Tools     │          │
│   │ (History)    │    │ (Ollama/     │    │ (kubectl_get │          │
│   │              │    │  Claude)     │    │  describe,   │          │
│   │              │    │              │    │  logs, etc)  │          │
│   └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                      │
│                    🔄 AGENTIC LOOP                                   │
│         Think → Act → Observe → Think → Act → Respond                │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   EXECUTOR (src/k8s/executor.py)                     │
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │  Validator   │    │  Kubectl     │    │   Parser     │          │
│   │  (Safety)    │───▶│  Executor    │───▶│  (Format)    │          │
│   └──────────────┘    └──────────────┘    └──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                                │
│              (Minikube / EKS / AKS / GKE)                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How a Query Flows Through the System

Let's trace what happens when you ask: **"Why is my nginx pod failing?"**

### Step 1: User Input (CLI)
```
File: src/main.py

You: Why is my nginx pod failing?
```
The CLI captures your input and passes it to the Agent.

### Step 2: Agent Receives Query
```
File: src/agent/core.py

agent.run("Why is my nginx pod failing?")
```
The agent adds your message to conversation memory.

### Step 3: Agent Asks LLM for Help
```
File: src/agent/core.py → src/llm/ollama_provider.py

The agent sends to the LLM:
- System prompt (explaining it's a K8s expert)
- Available tools (kubectl_get, describe, logs, etc.)
- Your question
- Conversation history
```

### Step 4: LLM Decides to Use a Tool
```
LLM Response:
"I need to check the pod status first. Let me use kubectl_get."

Tool Call:
{
  "name": "kubectl_get",
  "input": {"resource": "pods", "name": "nginx"}
}
```

### Step 5: Agent Executes the Tool
```
File: src/k8s/executor.py

1. Validates command is safe
2. Builds: kubectl get pods nginx
3. Executes command
4. Returns output to agent
```

### Step 6: Agent Gets Results, May Call More Tools
```
Output: "nginx-abc123   0/1   CrashLoopBackOff   5   10m"

LLM thinks: "It's in CrashLoopBackOff. Let me check logs."

Tool Call:
{
  "name": "kubectl_logs",
  "input": {"pod": "nginx-abc123", "previous": true}
}
```

### Step 7: Agent Continues Until Done
This loop continues until the LLM has enough information to answer.

### Step 8: Final Response
```
Agent Response:
"Your nginx pod is failing due to a configuration error.
The logs show: 'nginx: [emerg] unknown directive "servr"'

There's a typo in your nginx config - 'servr' should be 'server'.

To fix:
1. Check your ConfigMap: kubectl describe configmap nginx-config
2. Fix the typo and reapply"
```

---

## The Agentic AI Loop Explained

The "agentic" part means the AI can **autonomously decide** what actions to take.

```python
# Simplified version of src/agent/core.py

async def run(self, user_query):
    messages = [{"role": "user", "content": user_query}]
    
    while True:  # ← THE AGENTIC LOOP
        # 1. Ask LLM what to do
        response = llm.create_message(messages, tools=KUBERNETES_TOOLS)
        
        # 2. Check if LLM wants to use a tool
        if response.stop_reason == "tool_use":
            # LLM wants to run kubectl commands
            for tool_call in response.tool_calls:
                result = execute_tool(tool_call.name, tool_call.input)
                messages.append({"role": "tool", "content": result})
            
            # Loop again - LLM will see the results
            continue
        
        # 3. LLM is done - return final answer
        if response.stop_reason == "end_turn":
            return response.text
```

### Why is this "Agentic"?

| Traditional Chatbot | Agentic AI |
|---------------------|------------|
| You: "Check my pods" | You: "Why is my app slow?" |
| Bot: "Here are your pods" | Bot: (thinks) "Let me check pods..." |
| You: "Now check logs" | Bot: (thinks) "Pods look OK, check CPU..." |
| Bot: "Here are logs" | Bot: (thinks) "High CPU! Check which pod..." |
| You: "What's wrong?" | Bot: "Found it! Pod X is using 95% CPU because..." |

The agentic AI **decides on its own** what information it needs.

---

## Project Structure

```
k8s-bot/
│
├── src/
│   ├── main.py                 # 🚀 Entry point - CLI interface
│   │
│   ├── agent/                  # 🧠 The "brain"
│   │   ├── core.py             # Main agent loop
│   │   ├── tools.py            # Tool definitions for LLM
│   │   ├── prompts.py          # System prompts
│   │   └── memory.py           # Conversation history
│   │
│   ├── llm/                    # 🤖 LLM providers
│   │   ├── providers.py        # Abstract interface
│   │   ├── ollama_provider.py  # Free local LLM
│   │   └── anthropic_provider.py # Paid Claude API
│   │
│   ├── k8s/                    # ☸️ Kubernetes operations
│   │   ├── executor.py         # Safe kubectl execution
│   │   ├── contexts.py         # Multi-cluster management
│   │   ├── validators.py       # Command safety checks
│   │   └── parser.py           # Output formatting
│   │
│   └── utils/                  # 🔧 Utilities
│       ├── config.py           # Configuration loading
│       └── logger.py           # Logging setup
│
├── tests/                      # 🧪 Unit tests
├── docs/                       # 📚 Documentation
├── .env.example                # Configuration template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image
└── README.md                   # Getting started guide
```

---

## Module Deep Dive

### 1. CLI (`src/main.py`)

**What it does:** Provides the beautiful terminal interface.

```python
# Key functions:

print_banner()          # Shows the welcome message
print_context_info()    # Shows current cluster
interactive_loop()      # Main chat loop
process_query()         # Sends query to agent
confirmation_handler()  # Asks "Are you sure?" for dangerous ops
```

**User interaction flow:**
```
1. User types query
2. CLI shows "Thinking..." spinner
3. Agent processes query
4. CLI displays formatted response
5. Repeat
```

### 2. Agent Core (`src/agent/core.py`)

**What it does:** The brain - orchestrates everything.

```python
class KubernetesAgent:
    def __init__(self, config, tools, tool_executor, llm_provider):
        self.llm = llm_provider      # Ollama or Claude
        self.tools = tools           # Available kubectl tools
        self.tool_executor = tool_executor  # Function to run tools
        self.memory = ConversationMemory()  # Chat history
    
    async def run(self, user_query) -> AgentResponse:
        # The agentic loop lives here
        # Returns: text response + metadata
```

### 3. Tools (`src/agent/tools.py`)

**What it does:** Defines what the LLM can do.

Each tool has:
- **name**: `kubectl_get`, `kubectl_logs`, etc.
- **description**: What it does (LLM reads this!)
- **input_schema**: What parameters it accepts

```python
{
    "name": "kubectl_get",
    "description": "List Kubernetes resources like pods, deployments...",
    "input_schema": {
        "type": "object",
        "properties": {
            "resource": {"type": "string", "description": "pods, deployments..."},
            "namespace": {"type": "string", "description": "Namespace to query"}
        },
        "required": ["resource"]
    }
}
```

**Available tools:**
| Tool | Purpose |
|------|---------|
| `kubectl_get` | List resources |
| `kubectl_describe` | Detailed info |
| `kubectl_logs` | Container logs |
| `kubectl_get_events` | Cluster events |
| `kubectl_top` | Resource usage |
| `kubectl_scale` | Scale deployments |
| `kubectl_rollout` | Manage rollouts |
| `kubectl_exec` | Run commands in pods |
| `kubectl_apply` | Apply manifests |
| `kubectl_delete` | Delete resources |
| `list_contexts` | Show clusters |
| `switch_context` | Change cluster |

### 4. Executor (`src/k8s/executor.py`)

**What it does:** Safely runs kubectl commands.

```python
class KubectlExecutor:
    async def execute(self, command, timeout, dry_run):
        # 1. Validate command (block dangerous patterns)
        # 2. Check if needs confirmation
        # 3. Build full kubectl command
        # 4. Run with timeout
        # 5. Parse and return output
```

**Safety features:**
- Blocks command injection (`;`, `|`, `&&`)
- Requires confirmation for delete/apply
- Supports dry-run mode
- Enforces timeouts

### 5. LLM Providers (`src/llm/`)

**What it does:** Abstracts different AI providers.

```python
# Both providers implement this interface:
class LLMProvider:
    def create_message(self, messages, system, tools) -> LLMResponse:
        """Send messages to LLM and get response"""
    
    def is_available(self) -> tuple[bool, str]:
        """Check if provider is ready"""
```

**Ollama (Free):**
- Runs locally on your machine
- No internet required after model download
- Models: llama3.1, mistral, qwen, etc.

**Anthropic (Paid):**
- Cloud API
- Requires API key
- Models: claude-sonnet-4-20250514, etc.

### 6. Memory (`src/agent/memory.py`)

**What it does:** Remembers conversation history.

```python
class ConversationMemory:
    messages: list[Message]     # Chat history
    context_info: dict          # Current namespace, etc.
    
    def add_user_message(self, content): ...
    def add_assistant_message(self, content): ...
    def get_messages(self) -> list: ...
    def clear(self): ...
```

Why it matters:
```
You: Show me pods in production
Bot: [shows pods]

You: Scale the nginx one to 5 replicas
Bot: I'll scale nginx in production to 5 replicas
     ↑ Remembers "production" from context!
```

---

## LLM Providers

### How Ollama Works

```
┌──────────────┐     HTTP      ┌──────────────┐
│  K8s Bot     │◄────────────►│   Ollama     │
│  (Python)    │  localhost    │   Server     │
└──────────────┘   :11434      └──────────────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │  LLM Model   │
                               │  (llama3.1)  │
                               │   ~8GB RAM   │
                               └──────────────┘
```

1. Ollama runs as a local server
2. Bot sends HTTP requests to `localhost:11434`
3. Ollama runs the AI model on your CPU/GPU
4. Response comes back

### How Anthropic Works

```
┌──────────────┐    HTTPS      ┌──────────────┐
│  K8s Bot     │◄────────────►│  Anthropic   │
│  (Python)    │  api.anthropic│   Cloud      │
└──────────────┘     .com      └──────────────┘
```

1. Bot sends API request to Anthropic cloud
2. Claude model runs on Anthropic's servers
3. Response comes back
4. You pay per token

---

## Safety Features

### Risk Levels

```python
# From src/k8s/validators.py

SAFE = "get", "describe", "logs", "top"
↳ Execute immediately

MODERATE = "scale", "exec"
↳ Execute with warning

DANGEROUS = "apply", "create", "patch"
↳ Requires confirmation

CRITICAL = "delete", "drain", "cordon"
↳ Requires confirmation + shows warning
```

### Blocked Patterns

These are **always blocked** to prevent command injection:

```python
BLOCKED = [
    ";",      # Command chaining
    "|",      # Piping
    "&&",     # AND operator
    "||",     # OR operator
    "$(",     # Command substitution
    "`",      # Backtick substitution
    ">",      # Output redirection
]
```

### Confirmation Flow

```
You: Delete the nginx deployment

┌─────────────────────────────────────────────────┐
│ ⚠️  CRITICAL OPERATION                          │
│                                                 │
│ Command: delete deployment nginx                │
│                                                 │
│ This action may affect running workloads.       │
└─────────────────────────────────────────────────┘

Do you want to proceed? [y/N]: 
```

---

## Common Questions

### Q: How does the bot know which kubectl command to run?

**A:** The LLM reads the tool descriptions and your question, then decides. It's trained on millions of examples of people asking about Kubernetes, so it knows patterns like:

- "show me pods" → `kubectl_get(resource="pods")`
- "why is X failing" → `kubectl_describe` + `kubectl_logs` + `kubectl_get_events`

### Q: What happens if the LLM hallucinates a wrong command?

**A:** Several safeguards:

1. Tools have strict schemas - LLM can only pass valid parameters
2. Executor validates all commands before running
3. Blocked patterns prevent injection
4. Destructive ops need confirmation

### Q: Can it run arbitrary shell commands?

**A:** No. The bot can ONLY run the predefined kubectl tools. There's no "run any command" tool.

### Q: How does multi-cluster work?

**A:** The `ContextManager` class reads your `~/.kube/config` file:

```python
# Shows all available clusters
contexts = context_manager.list_contexts()

# Switches to EKS cluster
context_manager.switch_context("my-eks-cluster")

# All subsequent kubectl commands go to that cluster
```

### Q: Why use Ollama instead of always using Claude?

**A:** 
| Ollama | Claude |
|--------|--------|
| Free forever | ~$0.003 per query |
| Works offline | Requires internet |
| Data stays local | Data sent to cloud |
| Slower (local CPU) | Faster (cloud GPUs) |
| Good enough for most tasks | Best quality |

### Q: How do I add a new kubectl tool?

**A:** 
1. Add tool definition in `src/agent/tools.py`
2. Add handler in `src/k8s/executor.py` → `ToolExecutor` class
3. The LLM will automatically start using it!

---

## Sequence Diagram

```
User          CLI           Agent         LLM          Executor      K8s
 │             │              │            │              │           │
 │─"Why pod   │              │            │              │           │
 │  failing?"─▶│              │            │              │           │
 │             │──run()──────▶│            │              │           │
 │             │              │──create    │              │           │
 │             │              │  message()▶│              │           │
 │             │              │            │              │           │
 │             │              │◀─tool_use──│              │           │
 │             │              │  kubectl_  │              │           │
 │             │              │  get pods  │              │           │
 │             │              │            │              │           │
 │             │              │──execute()─────────────▶│           │
 │             │              │            │              │──kubectl──▶│
 │             │              │            │              │◀──output──│
 │             │              │◀─result────────────────│           │
 │             │              │            │              │           │
 │             │              │──create    │              │           │
 │             │              │  message()▶│              │           │
 │             │              │  (w/result)│              │           │
 │             │              │            │              │           │
 │             │              │◀─tool_use──│              │           │
 │             │              │  kubectl_  │              │           │
 │             │              │  logs      │              │           │
 │             │              │            │              │           │
 │             │              │──execute()─────────────▶│           │
 │             │              │            │              │──kubectl──▶│
 │             │              │            │              │◀──logs────│
 │             │              │◀─result────────────────│           │
 │             │              │            │              │           │
 │             │              │──create    │              │           │
 │             │              │  message()▶│              │           │
 │             │              │            │              │           │
 │             │              │◀─end_turn──│              │           │
 │             │              │  "Your pod │              │           │
 │             │              │   failed   │              │           │
 │             │              │   because.."│              │           │
 │             │              │            │              │           │
 │             │◀─response────│            │              │           │
 │◀─display────│              │            │              │           │
 │  response   │              │            │              │           │
```

---

## Summary

1. **User asks question** → CLI captures it
2. **Agent sends to LLM** with tools and history
3. **LLM decides what to do** → returns tool calls or final answer
4. **Agent executes tools** → kubectl commands run safely
5. **Loop continues** until LLM has enough info
6. **Final answer** displayed to user

The magic is in the **agentic loop** - the AI autonomously decides what information it needs, gathers it, and synthesizes an answer. You just ask questions naturally!
