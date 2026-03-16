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

---

## Advanced Operations

### Resource Optimization Analysis

When analyzing resource usage:

```
1. kubectl_get(resource="pods", output="wide") → Get resource requests/limits
2. Compare actual usage vs requests:
   - Over-provisioned: requests >> usage → Reduce requests
   - Under-provisioned: usage >> limits → Increase limits
3. Check for pods without limits → Security/stability risk
```

**Resource Efficiency Metrics:**

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| CPU Utilization | 60-80% | <40% or >90% | <20% or >95% |
| Memory Utilization | 70-85% | <50% or >90% | <30% or >95% |
| Request/Limit Ratio | 0.5-0.8 | <0.3 or >0.9 | No limits set |

### Network Debugging

For service connectivity issues:

```
1. kubectl_get(resource="endpoints") → Verify endpoints exist
2. kubectl_describe(resource="service") → Check selector matches
3. kubectl_get(resource="networkpolicies") → Check network restrictions
4. Check DNS resolution:
   - Service DNS: <svc>.<namespace>.svc.cluster.local
   - Pod DNS: <pod-ip>.<namespace>.pod.cluster.local
```

**Network Issue Decision Tree:**

```
Connection Failed?
├── No endpoints → Check pod labels match service selector
├── Endpoints exist but timeout → Check NetworkPolicy
├── DNS resolution fails → Check CoreDNS pods
├── Intermittent failures → Check pod readiness probes
└── Cross-namespace fails → Check NetworkPolicy egress/ingress
```

### Performance Troubleshooting

For slow application response:

```
1. Check pod resource usage vs limits
2. Analyze container metrics:
   - High CPU throttling → Increase CPU limits
   - Memory near limit → Risk of OOMKill
   - High restart count → Instability
3. Check HPA status if auto-scaling enabled
4. Review node resource pressure
```

**Latency Analysis:**

| Symptom | Likely Cause | Investigation |
|---------|--------------|---------------|
| Consistent slow | Under-resourced | Check CPU/memory limits |
| Spiky latency | GC pauses, resource contention | Check JVM flags, node load |
| Degrading over time | Memory leak, connection leak | Check memory growth, connections |
| Slow after deploy | New code issue, config change | Compare with previous version |

### Multi-Cluster Operations

For managing multiple clusters:

```
1. list_contexts() → Show all available clusters
2. Verify cluster before operations:
   - Production clusters: Extra confirmation required
   - Staging/Dev: Standard operations
3. Cross-cluster patterns:
   - Federated deployments
   - Disaster recovery failover
   - Blue-green across clusters
```

**Cluster Context Patterns:**

| Pattern | Example | Environment |
|---------|---------|-------------|
| `*-prod-*`, `*-prd-*` | eks-prod-usw2 | Production |
| `*-stg-*`, `*-staging-*` | aks-stg-east | Staging |
| `*-dev-*`, `*-qal-*` | gke-dev-central | Development |
| `minikube`, `docker-desktop` | minikube | Local |

### Advanced Security Analysis

Beyond basic security audit:

```
1. RBAC Analysis:
   - Check ServiceAccount permissions
   - Identify over-privileged roles
   - Audit ClusterRoleBindings

2. Network Security:
   - Default deny NetworkPolicies
   - Ingress/Egress restrictions
   - Service mesh mTLS status

3. Secrets Management:
   - Secrets encryption at rest
   - External secrets integration
   - Secret rotation status

4. Pod Security:
   - Pod Security Standards (Restricted/Baseline/Privileged)
   - Security Context constraints
   - Image vulnerability scanning
```

**Security Checklist:**

| Category | Check | Risk if Missing |
|----------|-------|-----------------|
| Pod Security | runAsNonRoot | Container escape |
| Pod Security | readOnlyRootFilesystem | Malware persistence |
| Pod Security | No privileged | Full node access |
| RBAC | Least privilege SA | Lateral movement |
| Network | NetworkPolicies | Unrestricted traffic |
| Secrets | Encryption at rest | Data exposure |

### Deployment Strategies

For managing rollouts:

```
1. kubectl_rollout(action="status") → Current rollout state
2. Deployment strategies:
   - RollingUpdate: Gradual replacement (default)
   - Recreate: All at once (downtime)
   - Blue-Green: Switch traffic instantly
   - Canary: Gradual traffic shift

3. Rollback patterns:
   - kubectl_rollout(action="undo") → Previous version
   - Check rollout history for versions
```

**Rollout Health Indicators:**

| Status | Meaning | Action |
|--------|---------|--------|
| Progressing | Rollout in progress | Monitor |
| Available | All replicas ready | Success |
| ReplicaFailure | Pods failing to start | Investigate pods |
| Stalled | No progress | Check resources, images |

### Capacity Planning

For cluster scaling decisions:

```
1. Node utilization analysis:
   - CPU/Memory allocation vs capacity
   - Pod density per node
   - Resource fragmentation

2. Scaling indicators:
   - Pending pods due to resources
   - HPA at max replicas frequently
   - Node pressure conditions

3. Recommendations:
   - Add nodes: Consistent resource pressure
   - Larger nodes: High pod density needed
   - Smaller nodes: Better bin-packing
```

**Capacity Thresholds:**

| Metric | Scale Up | Scale Down |
|--------|----------|------------|
| Node CPU | >80% sustained | <30% sustained |
| Node Memory | >85% sustained | <40% sustained |
| Pending Pods | >0 for >5min | N/A |
| HPA Replicas | At max frequently | At min frequently |

### Disaster Recovery

For backup and recovery:

```
1. Critical resources to backup:
   - Secrets and ConfigMaps
   - PersistentVolumeClaims
   - Custom Resources (CRDs)
   - RBAC configurations

2. Recovery priorities:
   - Namespace recreation
   - Secrets restoration
   - StatefulSet data
   - Application deployments

3. Validation after recovery:
   - Pod health checks
   - Service connectivity
   - Data integrity
```

### Cost Optimization

For reducing cluster costs:

```
1. Identify waste:
   - Unused PVCs
   - Over-provisioned pods
   - Idle namespaces
   - Orphaned resources

2. Right-sizing:
   - Analyze actual vs requested resources
   - Implement VPA recommendations
   - Use spot/preemptible nodes

3. Scheduling optimization:
   - Pod priority classes
   - Node affinity for cost zones
   - Cluster autoscaler tuning
```

**Cost Reduction Opportunities:**

| Finding | Potential Savings | Action |
|---------|-------------------|--------|
| CPU request 4x usage | 30-50% | Reduce requests |
| Unused PVCs | Storage costs | Delete or resize |
| Always-on dev clusters | 60-70% | Schedule downtime |
| No spot instances | 50-70% | Use spot for stateless |

---

## Advanced Queries

- "Analyze resource utilization for namespace X"
- "Show network policies affecting pod Y"
- "Compare deployment versions"
- "Find over-provisioned pods"
- "Check RBAC permissions for service account Z"
- "Show rollout history for deployment"
- "Identify unused resources"
- "Capacity analysis for cluster"
- "Security deep-dive for namespace"
- "Cost optimization recommendations"
