# K8s IntelliBot - Code Walkthrough

A simple guide to understand how the bot works.

---

## How It Works (30-Second Summary)

```
User asks: "Show me all pods"
    ↓
Bot sends question to LLM (Ollama/Claude)
    ↓
LLM decides: "I need to run kubectl_get"
    ↓
Bot executes: kubectl get pods
    ↓
Bot sends output back to LLM
    ↓
LLM generates human-friendly response
    ↓
User sees: "You have 2 pods running..."
```

---

## Project Structure (What Each File Does)

```
src/
├── main.py              # Entry point - CLI commands (chat, ask, validate)
├── agent/
│   ├── core.py          # Brain - the agentic loop that talks to LLM
│   ├── tools.py         # List of kubectl commands the bot can use
│   ├── prompts.py       # Instructions given to the LLM
│   └── memory.py        # Stores conversation history
├── llm/
│   ├── providers.py     # Abstract interface for LLM providers
│   ├── ollama_provider.py   # Ollama implementation (free, local)
│   └── anthropic_provider.py # Claude implementation (paid API)
├── k8s/
│   ├── executor.py      # Runs kubectl commands safely
│   ├── validators.py    # Checks if commands are safe
│   ├── parser.py        # Formats kubectl output
│   └── contexts.py      # Manages cluster connections
└── utils/
    ├── config.py        # Loads settings from .env
    └── logger.py        # Logging setup
```

---

## The Core Flow (Step by Step)

### Step 1: User Input (`main.py`)

```python
# User types a question
query = "show me all pods"

# main.py creates the agent and calls process()
response = await agent.process(query)
```

### Step 2: Agent Loop (`agent/core.py`)

This is the "brain" - it loops until it has an answer:

```python
class KubernetesAgent:
    async def process(self, query):
        # Add user message to conversation
        self.memory.add_message("user", query)
        
        while True:
            # 1. Ask LLM what to do
            response = self.llm.create_message(
                messages=self.memory.messages,
                system=SYSTEM_PROMPT,
                tools=KUBERNETES_TOOLS
            )
            
            # 2. Check if LLM wants to use a tool
            if response.has_tool_calls:
                # Execute the kubectl command
                result = self.tool_executor(tool_call)
                # Send result back to LLM
                self.memory.add_tool_result(result)
                continue  # Loop again
            
            # 3. LLM has final answer - return it
            return response.text
```

### Step 3: Tool Execution (`k8s/executor.py`)

When the LLM requests a tool:

```python
# LLM says: {"tool": "kubectl_get", "arguments": {"resource": "pods"}}

# executor.py builds the command
command = ["kubectl", "get", "pods"]

# Validates it's safe
validator.validate(command)  # Checks for dangerous patterns

# Runs it
result = subprocess.run(command)

# Returns output to agent
return result.stdout
```

### Step 4: Response Generation

The LLM sees the kubectl output and generates a friendly response:

```
kubectl output: "NAME          READY   STATUS    ..."
LLM response:   "You have 2 pods. my-nginx-pod is running normally..."
```

---

## Key Components Explained

### 1. LLM Provider (`llm/ollama_provider.py`)

Talks to the AI model:

```python
class OllamaProvider:
    def create_message(self, messages, system, tools):
        # Send request to Ollama
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": "llama3.2:3b", "messages": messages}
        )
        
        # Parse response - check if it's a tool call or text
        return self._parse_response(response)
```

### 2. Tools Definition (`agent/tools.py`)

Defines what kubectl commands the bot can use:

```python
KUBERNETES_TOOLS_LITE = [
    {
        "name": "kubectl_get",
        "description": "List Kubernetes resources",
        "input_schema": {
            "properties": {
                "resource": {"type": "string"},  # pods, deployments, etc.
                "namespace": {"type": "string"}
            }
        }
    },
    # ... more tools
]
```

### 3. Safety Validator (`k8s/validators.py`)

Prevents dangerous commands:

```python
class CommandValidator:
    BLOCKED_PATTERNS = [";", "|", "&&", "$("]  # No shell injection
    
    DANGEROUS_COMMANDS = ["delete", "drain", "cordon"]
    
    def validate(self, command):
        # Block dangerous patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in command:
                raise SecurityError("Blocked!")
        
        # Require confirmation for destructive ops
        if "delete" in command:
            return RiskLevel.DANGEROUS
```

### 4. System Prompt (`agent/prompts.py`)

Instructions that tell the LLM how to behave:

```python
SYSTEM_PROMPT = """
You are a Kubernetes assistant. You help users manage their clusters.

Rules:
1. Use kubectl tools to get real data
2. Always verify before destructive operations
3. Explain what you're doing

Available tools: kubectl_get, kubectl_describe, kubectl_logs...
"""
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                               │
│  (CLI: handles user input, displays output)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    agent/core.py                             │
│  (KubernetesAgent: orchestrates the conversation loop)       │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   memory.py  │    │  prompts.py  │    │   tools.py   │   │
│  │  (history)   │    │ (system msg) │    │ (tool defs)  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐
│     llm/providers     │   │      k8s/executor     │
│  (Ollama or Claude)   │   │  (runs kubectl cmds)  │
│                       │   │                       │
│  - Send messages      │   │  - validators.py      │
│  - Parse tool calls   │   │  - parser.py          │
│  - Get responses      │   │  - contexts.py        │
└───────────────────────┘   └───────────────────────┘
```

---

## Example: Complete Request Trace

**User:** "Why is my pod crashing?"

```
1. main.py receives "Why is my pod crashing?"

2. agent/core.py:
   - Adds to memory: {role: "user", content: "Why is my pod crashing?"}
   - Calls LLM with system prompt + tools + conversation

3. LLM responds: 
   {"tool": "kubectl_get", "arguments": {"resource": "pods"}}

4. k8s/executor.py:
   - Builds: kubectl get pods
   - Validates: Safe command ✓
   - Executes: Returns pod list with CrashLoopBackOff status

5. agent/core.py:
   - Adds tool result to memory
   - Calls LLM again

6. LLM responds:
   {"tool": "kubectl_logs", "arguments": {"pod": "my-app"}}

7. k8s/executor.py:
   - Executes: kubectl logs my-app
   - Returns: Error logs showing "Connection refused"

8. agent/core.py:
   - Adds tool result to memory
   - Calls LLM again

9. LLM responds (final answer):
   "Your pod my-app is crashing because it can't connect 
    to the database. The logs show 'Connection refused' 
    on port 5432. Check if your database service is running."

10. main.py displays the response to user
```

---

## Quick Reference: Key Functions

| File | Function | Purpose |
|------|----------|---------|
| `main.py` | `chat()` | Interactive mode |
| `main.py` | `ask()` | Single query mode |
| `agent/core.py` | `process()` | Main agent loop |
| `agent/core.py` | `_execute_tool_calls()` | Run kubectl tools |
| `llm/ollama_provider.py` | `create_message()` | Call Ollama API |
| `llm/ollama_provider.py` | `_extract_tool_call()` | Parse tool from response |
| `k8s/executor.py` | `execute()` | Run kubectl safely |
| `k8s/validators.py` | `validate()` | Check command safety |

---

## Configuration Flow

```
.env file
    ↓
config.py loads environment variables
    ↓
Creates Config object with:
  - llm_provider: "ollama" or "anthropic"
  - model: "llama3.2:3b"
  - safe_mode: true
  - kubeconfig: path to cluster config
    ↓
Passed to KubernetesAgent
```

---

## That's It!

The bot is essentially:
1. **A loop** that talks to an LLM
2. **Tools** that execute kubectl commands
3. **Safety checks** to prevent dangerous operations
4. **Memory** to maintain conversation context

The LLM decides when to use tools and when to respond, making it "agentic" - it can take multiple steps autonomously to answer a question.
