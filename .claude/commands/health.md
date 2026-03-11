---
description: Check Kubernetes cluster health
---

Use the kubectl-ai MCP server to check cluster health.

Call `cluster_health` tool.

Present the health score with interpretation:
- 90-100: 🟢 Healthy
- 70-89: 🟡 Warning  
- 50-69: 🟠 Degraded
- 0-49: 🔴 Critical

List any issues found and recommend fixes.
