---
name: kubectl-ai
description: Kubernetes cluster management using natural language. Execute kubectl commands, diagnose pod issues, check cluster health, run security audits, and troubleshoot deployments.
invocation: auto
# auto = Claude uses when relevant
# user = Only when user invokes /kubectl-ai
# subagent = Run in isolated subagent
---

# kubectl-ai: Kubernetes IntelliBot

Perform autonomous Kubernetes operations using natural language. Diagnose issues, execute kubectl commands, and provide actionable recommendations.

## When to Use This Skill

Use this skill when the user asks about:
- Kubernetes pods, deployments, services, nodes
- Cluster health or status
- Container logs or errors
- Security vulnerabilities in K8s
- Scaling or rollout operations
- Troubleshooting K8s issues

## Prerequisites

- `user-kubectl-ai` MCP server must be configured
- Valid KUBECONFIG pointing to target cluster
- For enterprise clusters: `eiamcli login` for authentication

## Available Tools

### Core kubectl Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `kubectl_get` | List resources | "show all pods" |
| `kubectl_describe` | Resource details | "describe pod nginx" |
| `kubectl_logs` | Container logs | "show logs for nginx" |
| `kubectl_scale` | Scale deployments | "scale nginx to 3" |
| `kubectl_rollout` | Manage rollouts | "restart deployment" |

### Diagnostic Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `cluster_health` | Health score (0-100) | "is cluster healthy?" |
| `security_audit` | Security scan | "run security audit" |
| `explain_error` | Diagnose errors | "why is pod failing?" |
| `kubectl_get_events` | Cluster events | "show recent events" |

### Context Management

| Tool | Purpose | Example |
|------|---------|---------|
| `list_contexts` | Available clusters | "list clusters" |
| `switch_context` | Change cluster | "switch to prod" |
| `get_current_context` | Current cluster | "which cluster?" |

## Workflow

### Step 1: Parse Request

Identify from user query:
- **Action**: list, describe, logs, scale, troubleshoot
- **Resource**: pods, deployments, services, nodes
- **Filters**: namespace, labels, name

### Step 2: Execute Tools

```
# Listing resources
kubectl_get(resource="pods", namespace="all")

# Troubleshooting (multi-step)
1. kubectl_describe(resource="pod", name="<NAME>")
2. kubectl_logs(pod_name="<NAME>", tail=100)
3. kubectl_get_events()

# Health check
cluster_health()
```

### Step 3: Analyze & Present

Format results with:
- Status indicators: ✅ ⚠️ ❌
- Summary tables
- Root cause identification
- Actionable recommendations

## Common Diagnosis Patterns

### Pod Not Starting (Pending/ContainerCreating)

```
1. kubectl_describe → Check Events section
2. Look for:
   - FailedScheduling → Node resources
   - FailedMount → Missing secrets/configmaps
   - ImagePullBackOff → Wrong image/registry
3. Provide fix command
```

### Pod Crashing (CrashLoopBackOff)

```
1. kubectl_describe → Check Last State
2. kubectl_logs(previous=true) → Crash logs
3. Check:
   - Exit 137 → OOMKilled → Increase memory
   - Exit 1 → App error → Check logs
4. Provide fix command
```

### Service Not Working

```
1. kubectl_get(resource="endpoints") → Check if empty
2. kubectl_describe(resource="service") → Check selector
3. If endpoints empty → Selector mismatch
4. Provide corrected selector
```

## Health Score Interpretation

| Score | Status | Action |
|-------|--------|--------|
| 90-100 | 🟢 Healthy | No action needed |
| 70-89 | 🟡 Warning | Investigate warnings |
| 50-69 | 🟠 Degraded | Action required |
| 0-49 | 🔴 Critical | Immediate action |

## Security Audit Severities

| Severity | Example | Fix Priority |
|----------|---------|--------------|
| 🔴 Critical | Privileged containers | Immediate |
| 🟠 High | Running as root | Next release |
| 🟡 Medium | No resource limits | Plan fix |
| 🔵 Low | Default service account | Best practice |

## Output Format

### Pod Summary Table

```
| Pod | Ready | Status | Restarts | Age |
|-----|-------|--------|----------|-----|
| nginx-xyz | 1/1 | Running | 0 | 2d |
```

### Issue Report

```
❌ ISSUE: Pod nginx-xyz in CrashLoopBackOff
   Reason: OOMKilled (Exit code 137)
   Evidence: Memory limit 256Mi exceeded
   Fix: kubectl set resources deploy/nginx --limits=memory=512Mi
```

## Key Rules

1. **Verify context first** before destructive operations
2. **Check events** - often faster than logs for diagnosis
3. **Use previous=true** for crash logs
4. **Multi-step diagnosis** - describe + logs + events
5. **Provide fix commands** - not just diagnosis
6. **Format tables** for readability
7. **Show root cause** not just symptoms

## Error Quick Reference

| Error | Cause | Fix |
|-------|-------|-----|
| ImagePullBackOff | Bad image/auth | Check image name, registry creds |
| CrashLoopBackOff | App crashing | Check logs with previous=true |
| Pending | Can't schedule | Check node resources, affinity |
| OOMKilled | Out of memory | Increase memory limits |
| FailedMount | Volume issue | Check secret/configmap exists |

## Example Queries

- "Show all pods in default namespace"
- "Why is my nginx pod failing?"
- "Check cluster health"
- "Run security audit"
- "Scale web deployment to 5 replicas"
- "Show logs for api-server pod"
- "Switch to production cluster"
- "Describe the failing deployment"
