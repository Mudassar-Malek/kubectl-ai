# K8s IntelliBot - Quick Reference Guide

A one-page cheat sheet for understanding and explaining the bot.

---

## What Does It Do? (30-second explanation)

> "K8s IntelliBot is an AI chatbot that lets you manage Kubernetes using plain English. Instead of typing `kubectl get pods -n production -l app=nginx`, you just say 'show me nginx pods in production'. The AI figures out the command, runs it, and explains the results."

---

## How Does It Work? (1-minute explanation)

```
YOU: "Why is my app crashing?"
         │
         ▼
    ┌─────────┐
    │   AI    │ ← Thinks: "I need to check pods, then logs..."
    └─────────┘
         │
         ▼
    ┌─────────────────────────────────────┐
    │  1. kubectl get pods                │
    │  2. kubectl describe pod app-xyz    │
    │  3. kubectl logs app-xyz            │
    └─────────────────────────────────────┘
         │
         ▼
    ┌─────────┐
    │   AI    │ ← Analyzes results
    └─────────┘
         │
         ▼
BOT: "Your app is crashing because of an
      OOMKilled error. It needs more memory.
      Try increasing the memory limit to 512Mi."
```

---

## Key Components

| Component | File | What It Does |
|-----------|------|--------------|
| **CLI** | `src/main.py` | Terminal interface, user input/output |
| **Agent** | `src/agent/core.py` | AI brain, decides what to do |
| **Tools** | `src/agent/tools.py` | Defines available kubectl commands |
| **Executor** | `src/k8s/executor.py` | Safely runs kubectl |
| **LLM** | `src/llm/*.py` | Talks to AI (Ollama or Claude) |

---

## The Agentic Loop (Why It's Smart)

Traditional bot:
```
You: "Check pods" → Bot runs 1 command → Shows output
You: "Now logs" → Bot runs 1 command → Shows output
You: "What's wrong?" → Bot: "I don't know"
```

Agentic AI:
```
You: "What's wrong with my app?"
Bot: (runs 5 commands automatically)
Bot: "Found it! Here's the problem and solution..."
```

**Key insight:** The AI decides WHAT commands to run, not just HOW to run them.

---

## Supported Commands

```
┌─────────────────────────────────────────────────────────┐
│                    SAFE (run immediately)               │
├─────────────────────────────────────────────────────────┤
│ kubectl_get      │ List pods, deployments, services    │
│ kubectl_describe │ Detailed resource info              │
│ kubectl_logs     │ Container logs                      │
│ kubectl_events   │ Cluster events                      │
│ kubectl_top      │ CPU/memory usage                    │
│ kubectl_explain  │ API documentation                   │
│ list_contexts    │ Show available clusters             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│             DANGEROUS (needs confirmation)              │
├─────────────────────────────────────────────────────────┤
│ kubectl_scale    │ Change replica count                │
│ kubectl_rollout  │ Restart/undo deployments            │
│ kubectl_apply    │ Create/update resources             │
│ kubectl_delete   │ Remove resources                    │
│ kubectl_exec     │ Run commands in pods                │
│ switch_context   │ Change clusters                     │
└─────────────────────────────────────────────────────────┘
```

---

## LLM Options

| Provider | Cost | Speed | Quality | Setup |
|----------|------|-------|---------|-------|
| **Ollama** | Free | Slower | Good | `ollama pull llama3.1:8b` |
| **Claude** | ~$0.003/query | Fast | Best | API key required |

---

## Configuration Quick Reference

```bash
# .env file

# Choose provider
LLM_PROVIDER=ollama          # or "anthropic"

# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
K8S_BOT_MODEL=llama3.1:8b    # or mistral:7b, qwen2.5:7b

# Claude settings (if using)
# ANTHROPIC_API_KEY=sk-ant-...
# K8S_BOT_MODEL=claude-sonnet-4-20250514

# Safety
K8S_BOT_SAFE_MODE=true       # Confirm dangerous ops
K8S_BOT_DRY_RUN=false        # Test mode (no changes)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect to Ollama" | Run `ollama serve` |
| "Model not found" | Run `ollama pull llama3.1:8b` |
| "Kubeconfig not found" | Check `~/.kube/config` exists |
| "Connection refused to cluster" | Run `minikube start` |
| "Forbidden" errors | Check RBAC permissions |

---

## Example Conversations

**Basic Usage:**
```
You: Show me all pods
You: What namespaces exist?
You: List deployments in kube-system
```

**Troubleshooting:**
```
You: Why is my nginx pod failing?
You: Debug the CrashLoopBackOff in api-server
You: What's using the most memory?
```

**Operations:**
```
You: Scale web deployment to 5 replicas
You: Restart the api deployment
You: Switch to my production cluster
```

---

## File Structure At-a-Glance

```
k8s-bot/
├── src/
│   ├── main.py          ← Start here! Entry point
│   ├── agent/
│   │   ├── core.py      ← THE BRAIN (agentic loop)
│   │   └── tools.py     ← What AI can do
│   ├── llm/
│   │   ├── ollama_provider.py   ← Free AI
│   │   └── anthropic_provider.py ← Paid AI
│   └── k8s/
│       ├── executor.py  ← Runs kubectl safely
│       └── contexts.py  ← Multi-cluster support
├── docs/
│   ├── ARCHITECTURE.md  ← Full deep-dive
│   └── QUICK_REFERENCE.md ← This file!
└── README.md            ← Getting started
```

---

## One-Liner Explanations

**For engineers:**
> "It's a ReAct-style agent using Claude/Ollama that autonomously executes kubectl commands through a tool-use interface."

**For managers:**
> "It's an AI assistant that lets anyone manage Kubernetes without memorizing commands."

**For demos:**
> "Watch - I'll ask 'why is my app slow' and it automatically investigates and tells me the answer."

---

## Quick Demo Commands

```bash
# 1. Start Ollama
ollama serve

# 2. Start Minikube  
minikube start

# 3. Deploy test apps
kubectl create deployment nginx --image=nginx
kubectl create deployment buggy --image=busybox -- sh -c "exit 1"

# 4. Run the bot
python -m src.main

# 5. Try these queries:
#    "Show me all pods"
#    "Why is buggy deployment failing?"
#    "Get nginx logs"
#    "Scale nginx to 3 replicas"
```
