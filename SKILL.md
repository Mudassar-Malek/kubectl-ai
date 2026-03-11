---
name: kubectl-ai
description: Kubernetes cluster management using natural language. Execute kubectl commands, diagnose pod issues, check cluster health, run security audits, and troubleshoot deployments. Use when managing Kubernetes clusters, debugging pods, checking deployment status, investigating container errors, or performing cluster health checks.
---

# kubectl-ai: Kubernetes IntelliBot

Perform autonomous Kubernetes operations using natural language. Diagnose issues, execute kubectl commands, and provide actionable recommendations without requiring kubectl syntax knowledge.

**Autonomous Investigation Rules:**
- NEVER present partial findings with an offer to investigate further. If deeper investigation is needed, DO IT before presenting.
- When a pod shows errors, AUTOMATICALLY check logs, events, and describe the resource.
- When investigating availability issues, check ALL related resources (pods, deployments, services, endpoints).
- The investigation is complete ONLY when root cause is identified with actionable fix.

## Prerequisites

- `user-kubectl-ai` MCP server (required) — kubectl command execution
- Valid `KUBECONFIG` environment variable pointing to cluster config
- For enterprise clusters: `eiamcli login` for authentication

**Verify MCP is ready:**
```
Check MCP tools/kubectl_get.json exists and contains the tool schema
```

## Quick-Start Decision Tree

```
User Query Type?
├── List resources ("show pods", "get deployments")
│   └── kubectl_get → format results → present summary
├── Resource details ("describe pod X", "why is pod failing")
│   └── kubectl_describe → analyze status → check events → check logs
├── Logs ("show logs for X", "what errors in X")
│   └── kubectl_logs → parse errors → identify patterns
├── Health check ("is cluster healthy", "cluster status")
│   └── cluster_health → analyze score → investigate issues
├── Security ("security audit", "check vulnerabilities")
│   └── security_audit → categorize issues → recommend fixes
├── Troubleshooting ("why is X failing", "debug X")
│   └── Multi-step: describe → events → logs → diagnose
├── Scaling ("scale X to N replicas")
│   └── kubectl_scale → verify → report status
└── Deployments ("rollout status", "restart deployment")
    └── kubectl_rollout → monitor → report completion
```

---

## Available MCP Tools

| Tool | Description | Required Parameters |
|------|-------------|---------------------|
| `kubectl_get` | List resources (pods, deployments, services, nodes) | `resource` |
| `kubectl_describe` | Get detailed resource information | `resource`, `name` |
| `kubectl_logs` | View container logs | `pod_name` |
| `kubectl_get_events` | Get cluster events | (none) |
| `kubectl_scale` | Scale deployments | `deployment`, `replicas` |
| `kubectl_rollout` | Manage rollouts | `action`, `deployment` |
| `cluster_health` | Get cluster health score (0-100) | (none) |
| `security_audit` | Run security vulnerability scan | (none) |
| `explain_error` | Diagnose pod/resource errors | `resource_type`, `name` |
| `list_contexts` | List available cluster contexts | (none) |
| `switch_context` | Switch to different cluster | `context_name` |
| `get_current_context` | Show current cluster context | (none) |

---

## Workflow

### Step 1: Identify the Request Type

Parse the user's natural language query to determine:
1. **Action**: list, describe, logs, scale, troubleshoot, audit
2. **Resource**: pods, deployments, services, nodes, etc.
3. **Scope**: namespace, label selector, specific name

### Step 2: Execute Appropriate Tool(s)

**For listing resources:**
```
kubectl_get(resource="pods", namespace="all")
```

**For troubleshooting:**
```
1. kubectl_describe(resource="pod", name="<POD_NAME>")
2. kubectl_logs(pod_name="<POD_NAME>", tail=100)
3. kubectl_get_events()
```

**For health checks:**
```
cluster_health()
```

### Step 3: Analyze Results

| Resource State | Analysis |
|----------------|----------|
| Running | Check READY count, RESTARTS |
| Pending | Check events for scheduling issues |
| CrashLoopBackOff | Check logs for crash reason |
| ImagePullBackOff | Check image name, registry access |
| ContainerCreating | Check events for mount/secret issues |
| Terminating | Check if stuck, force delete if needed |

### Step 4: Present Findings

Format results in tables with:
- Status indicators (✅ ⚠️ ❌)
- Counts and summaries
- Actionable recommendations
- Root cause identification

---

## Common Diagnosis Patterns

### Pattern 1: Pod Not Starting

```
Symptoms: Status = Pending, ContainerCreating, or Init:*
Steps:
1. kubectl_describe(resource="pod", name="<POD>")
2. Check Events section for:
   - FailedScheduling → Node resources, affinity, taints
   - FailedMount → Missing secrets, configmaps, PVCs
   - FailedCreate → Security context, service account
3. kubectl_get(resource="nodes") → Check node capacity
4. kubectl_get(resource="events", namespace="<NS>") → Recent events
```

### Pattern 2: Pod Crashing

```
Symptoms: Status = CrashLoopBackOff, Error, OOMKilled
Steps:
1. kubectl_describe(resource="pod", name="<POD>")
2. kubectl_logs(pod_name="<POD>", previous=true) → Last crash logs
3. Check:
   - Exit code 137 → OOMKilled, increase memory limits
   - Exit code 1 → Application error, check logs
   - Exit code 0 but restarting → Liveness probe failing
4. explain_error(resource_type="pod", name="<POD>")
```

### Pattern 3: Service Not Accessible

```
Symptoms: Connection refused, timeout, 503
Steps:
1. kubectl_get(resource="endpoints", name="<SERVICE>")
2. kubectl_describe(resource="service", name="<SERVICE>")
3. Check:
   - Endpoints empty → Selector mismatch, pods not ready
   - Endpoints exist → Pod health, network policies
4. kubectl_get(resource="pods", selector="<SERVICE_SELECTOR>")
```

### Pattern 4: Deployment Not Progressing

```
Symptoms: Deployment stuck, replicas not matching
Steps:
1. kubectl_describe(resource="deployment", name="<DEPLOY>")
2. kubectl_rollout(action="status", deployment="<DEPLOY>")
3. Check:
   - Insufficient replicas → Resource quota, node capacity
   - Progressing=False → Image pull, security context
4. kubectl_get(resource="events") → Recent deployment events
```

---

## Health Check Interpretation

### Cluster Health Score

| Score | Status | Meaning |
|-------|--------|---------|
| 90-100 | 🟢 Healthy | All components operational |
| 70-89 | 🟡 Warning | Minor issues, investigate |
| 50-69 | 🟠 Degraded | Multiple issues, action needed |
| 0-49 | 🔴 Critical | Major issues, immediate action |

### Health Check Components

```
cluster_health() checks:
├── Nodes: Ready vs NotReady
├── Pods: Running vs Failed/Pending
├── Deployments: Available vs Unavailable
├── Services: With endpoints vs Without
└── Storage: Bound PVCs vs Pending
```

---

## Security Audit Interpretation

### Severity Levels

| Severity | Examples | Action |
|----------|----------|--------|
| 🔴 Critical | Privileged containers | Fix immediately |
| 🟠 High | Running as root | Fix in next release |
| 🟡 Medium | No resource limits | Plan remediation |
| 🔵 Low | Default service account | Best practice |

### Common Security Findings

| Finding | Fix |
|---------|-----|
| Privileged container | Remove `privileged: true` |
| Running as root | Add `runAsNonRoot: true` |
| No resource limits | Add `resources.limits` |
| Default service account | Create dedicated SA |
| Writable root filesystem | Add `readOnlyRootFilesystem: true` |
| Missing network policies | Create NetworkPolicy |

---

## Multi-Cluster Support

### Switching Contexts

```
1. list_contexts() → Show available clusters
2. switch_context(context_name="<CONTEXT>") → Switch
3. get_current_context() → Verify switch
```

### Context Naming Patterns

| Pattern | Platform |
|---------|----------|
| `minikube` | Local Minikube |
| `docker-desktop` | Docker Desktop |
| `arn:aws:eks:*` | AWS EKS |
| `gke_*` | Google GKE |
| `*-aks-*` | Azure AKS |
| `kind-*` | Kind cluster |

---

## Output Format Guidelines

### Pod List Format

```
| Namespace | Pod | Ready | Status | Restarts | Age |
|-----------|-----|-------|--------|----------|-----|
| default | nginx-xyz | 1/1 | Running | 0 | 2d |
```

### Summary Statistics

```
Total: 50 pods
├── Running: 48 (96%)
├── Pending: 1 (2%)
└── Failed: 1 (2%)
```

### Issue Reporting

```
❌ ISSUE: Pod nginx-xyz in CrashLoopBackOff
   Reason: OOMKilled (Exit code 137)
   Evidence: Memory limit 256Mi exceeded
   Fix: Increase memory limit to 512Mi
   Command: kubectl set resources deployment/nginx --limits=memory=512Mi
```

---

## Key Rules

1. **Always verify context** — run `get_current_context()` before destructive operations.
2. **Check namespace** — default namespace may not contain target resources.
3. **Use labels for filtering** — `selector="app=nginx"` for targeted queries.
4. **Check events first** — events often explain pending/failed states faster than logs.
5. **Previous logs for crashes** — use `previous=true` to see logs from crashed container.
6. **Resource limits matter** — OOMKilled is common, always check memory usage.
7. **Describe before delete** — understand resource before removing it.
8. **Health score is summary** — low score requires component-level investigation.
9. **Security audit regularly** — run audit after deployments, before production.
10. **Multi-step diagnosis** — troubleshooting requires describe + logs + events.

---

## Error Messages Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `ImagePullBackOff` | Image not found or auth failed | Check image name, registry credentials |
| `CrashLoopBackOff` | Container keeps crashing | Check logs with `previous=true` |
| `Pending` | Cannot schedule | Check node resources, affinity |
| `ContainerCreating` | Stuck creating | Check secrets, configmaps, PVCs |
| `OOMKilled` | Out of memory | Increase memory limits |
| `Evicted` | Node pressure | Check node disk/memory |
| `FailedMount` | Volume mount failed | Check secret/configmap exists |
| `Forbidden` | RBAC denied | Check service account permissions |

---

## Example Investigations

### Example 1: "Why is my nginx pod failing?"

```
1. kubectl_get(resource="pods", selector="app=nginx")
   → Found: nginx-xyz in CrashLoopBackOff

2. kubectl_describe(resource="pod", name="nginx-xyz")
   → State: Waiting (CrashLoopBackOff)
   → Last State: Terminated (OOMKilled, Exit 137)
   → Limits: memory=128Mi

3. kubectl_logs(pod_name="nginx-xyz", previous=true)
   → [error] worker process 12 exited on signal 9

4. DIAGNOSIS:
   Root Cause: Memory limit too low (128Mi)
   Evidence: OOMKilled (signal 9, exit 137)
   Fix: Increase memory limit to 256Mi+
   Command: kubectl set resources deployment/nginx --limits=memory=256Mi
```

### Example 2: "Check cluster health"

```
1. cluster_health()
   → Score: 85/100 🟡
   → Nodes: 3/3 ready ✅
   → Pods: 47/50 running ⚠️ (3 pending)
   → Deployments: 10/10 available ✅
   → Services: 8/9 have endpoints ⚠️

2. kubectl_get(resource="pods", field_selector="status.phase=Pending")
   → Found: db-migration-xyz (Pending 2h)

3. kubectl_describe(resource="pod", name="db-migration-xyz")
   → Events: FailedScheduling - Insufficient cpu

4. DIAGNOSIS:
   Issue: 3 pods pending due to insufficient CPU
   Fix: Scale up nodes or reduce resource requests
   Affected: db-migration-xyz, worker-abc, cache-def
```

---

## Delivery Options

After completing analysis, offer:

1. **Summary** — Concise findings with action items
2. **Detailed Report** — Full investigation with evidence
3. **Commands** — Kubectl commands to fix issues
4. **YAML** — Fixed manifests for apply

---

## Additional References

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Debugging Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/)
- [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
