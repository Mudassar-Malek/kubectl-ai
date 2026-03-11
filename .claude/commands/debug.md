---
description: Debug a failing Kubernetes resource
arguments:
  - name: resource
    description: Resource to debug (e.g., "pod nginx-xyz")
    required: true
---

Use the kubectl-ai MCP server to debug the specified resource.

Steps:
1. Parse the resource type and name from: $ARGUMENTS
2. Call `kubectl_describe` for the resource
3. If it's a pod, call `kubectl_logs` with previous=true if crashed
4. Call `kubectl_get_events` for recent events
5. Analyze the data to identify root cause
6. Present findings with:
   - ❌ Issue identified
   - 📋 Evidence from logs/events
   - 🔧 Fix command to resolve
