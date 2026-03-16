---
description: List all Kubernetes pods
---

Use the kubectl-ai MCP server to list all pods.

Call `kubectl_get` with resource="pods" and namespace="all".

Present results in a table with: Namespace, Pod Name, Ready, Status, Restarts, Age.

Add summary: Total pods, Running count, Issues count.
