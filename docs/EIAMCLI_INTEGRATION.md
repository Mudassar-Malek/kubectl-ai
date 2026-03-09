# Integrating K8s IntelliBot with eiamcli

This guide explains how to use K8s IntelliBot with your existing `eiamcli` authentication workflow.

---

## Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   eiamcli   │────▶│  kubeconfig │────▶│  K8s Bot    │────▶│  Cluster    │
│  (auth)     │     │  (updated)  │     │  (queries)  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**How it works:**
1. `eiamcli` authenticates you and updates your kubeconfig
2. K8s IntelliBot reads the kubeconfig and uses the active context
3. Bot executes kubectl commands using your authenticated session

---

## Option 1: Use After eiamcli Login (Simplest)

### Step 1: Authenticate with eiamcli
```bash
# Login to your cluster using eiamcli
eiamcli login --cluster my-cluster

# Or whatever your eiamcli command is
eiamcli configure --environment prod
```

### Step 2: Verify kubectl works
```bash
kubectl get nodes
```

### Step 3: Run the bot
```bash
cd /path/to/k8s-bot
source venv/bin/activate
python -m src.main chat
```

The bot will automatically use the kubeconfig that eiamcli configured.

---

## Option 2: Wrapper Script (Recommended)

Create a wrapper script that runs eiamcli first, then starts the bot.

### Create wrapper script

Create `k8s-bot-cli.sh`:

```bash
#!/bin/bash

# k8s-bot-cli.sh - K8s IntelliBot with eiamcli integration

set -e

# Configuration
BOT_DIR="${BOT_DIR:-/path/to/k8s-bot}"
CLUSTER="${1:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  K8s IntelliBot with eiamcli${NC}"
echo -e "${GREEN}========================================${NC}"

# Step 1: Check if cluster is specified
if [ -z "$CLUSTER" ]; then
    echo -e "${YELLOW}Available clusters:${NC}"
    # List available clusters (adjust command based on your eiamcli)
    eiamcli list-clusters 2>/dev/null || kubectl config get-contexts -o name
    echo ""
    read -p "Enter cluster name: " CLUSTER
fi

# Step 2: Authenticate with eiamcli
echo -e "\n${YELLOW}Authenticating with eiamcli...${NC}"
if ! eiamcli login --cluster "$CLUSTER"; then
    echo -e "${RED}Failed to authenticate with eiamcli${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authenticated to $CLUSTER${NC}"

# Step 3: Verify connection
echo -e "\n${YELLOW}Verifying cluster connection...${NC}"
if ! kubectl get nodes > /dev/null 2>&1; then
    echo -e "${RED}Cannot connect to cluster${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to cluster${NC}"

# Step 4: Start the bot
echo -e "\n${YELLOW}Starting K8s IntelliBot...${NC}"
cd "$BOT_DIR"
source venv/bin/activate
python -m src.main chat
```

### Make it executable
```bash
chmod +x k8s-bot-cli.sh
```

### Usage
```bash
# With cluster name
./k8s-bot-cli.sh my-prod-cluster

# Interactive (prompts for cluster)
./k8s-bot-cli.sh
```

---

## Option 3: Integrate eiamcli into the Bot

Modify the bot to call eiamcli automatically before connecting.

### Step 1: Create eiamcli integration module

Create `src/auth/eiamcli.py`:

```python
"""eiamcli integration for K8s IntelliBot."""

import subprocess
import shutil
from typing import Optional, Tuple

from src.utils.logger import get_logger

logger = get_logger("eiamcli")


class EiamCliAuth:
    """Handles authentication via eiamcli."""
    
    def __init__(self):
        self.eiamcli_path = shutil.which("eiamcli")
        
    def is_available(self) -> bool:
        """Check if eiamcli is installed."""
        return self.eiamcli_path is not None
    
    def list_clusters(self) -> list[str]:
        """List available clusters."""
        try:
            result = subprocess.run(
                ["eiamcli", "list-clusters"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            return []
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            return []
    
    def login(self, cluster: str) -> Tuple[bool, str]:
        """
        Authenticate to a cluster using eiamcli.
        
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Authenticating to cluster: {cluster}")
        
        try:
            result = subprocess.run(
                ["eiamcli", "login", "--cluster", cluster],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully authenticated to {cluster}")
                return True, f"Authenticated to {cluster}"
            else:
                error = result.stderr or result.stdout or "Unknown error"
                logger.error(f"Authentication failed: {error}")
                return False, error
                
        except subprocess.TimeoutExpired:
            return False, "Authentication timed out"
        except FileNotFoundError:
            return False, "eiamcli not found in PATH"
        except Exception as e:
            return False, str(e)
    
    def get_current_identity(self) -> Optional[str]:
        """Get current authenticated identity."""
        try:
            result = subprocess.run(
                ["eiamcli", "whoami"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None


# Singleton instance
eiamcli = EiamCliAuth()
```

### Step 2: Create auth __init__.py

Create `src/auth/__init__.py`:

```python
"""Authentication module."""

from src.auth.eiamcli import EiamCliAuth, eiamcli

__all__ = ["EiamCliAuth", "eiamcli"]
```

### Step 3: Add login command to CLI

Update `src/main.py` to add a login command:

```python
# Add this import at the top
from src.auth.eiamcli import eiamcli

# Add this command
@cli.command()
@click.argument("cluster", required=False)
def login(cluster: str):
    """Authenticate to a cluster using eiamcli.
    
    Example: k8s-bot login my-prod-cluster
    """
    if not eiamcli.is_available():
        console.print("[red]eiamcli is not installed or not in PATH[/red]")
        return
    
    # If no cluster specified, show list
    if not cluster:
        clusters = eiamcli.list_clusters()
        if clusters:
            console.print("[yellow]Available clusters:[/yellow]")
            for c in clusters:
                console.print(f"  • {c}")
            cluster = Prompt.ask("Enter cluster name")
        else:
            cluster = Prompt.ask("Enter cluster name")
    
    # Authenticate
    console.print(f"[yellow]Authenticating to {cluster}...[/yellow]")
    success, message = eiamcli.login(cluster)
    
    if success:
        console.print(f"[green]✓ {message}[/green]")
        
        # Show current identity
        identity = eiamcli.get_current_identity()
        if identity:
            console.print(f"[dim]Identity: {identity}[/dim]")
    else:
        console.print(f"[red]✗ Authentication failed: {message}[/red]")
```

### Step 4: Add auto-login option

Update `src/utils/config.py`:

```python
# Add to Config class
@property
def eiamcli_auto_login(self) -> bool:
    """Auto-login with eiamcli before connecting."""
    return os.getenv("EIAMCLI_AUTO_LOGIN", "false").lower() == "true"

@property
def eiamcli_cluster(self) -> Optional[str]:
    """Default cluster for eiamcli."""
    return os.getenv("EIAMCLI_CLUSTER")
```

### Step 5: Update .env

Add to your `.env`:

```bash
# eiamcli Integration
EIAMCLI_AUTO_LOGIN=true
EIAMCLI_CLUSTER=my-default-cluster
```

---

## Option 4: Use eiamcli exec-credential

If your eiamcli works as an exec credential plugin in kubeconfig, no changes are needed!

### Check your kubeconfig

```yaml
# ~/.kube/config
users:
- name: my-cluster-user
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: eiamcli
      args:
        - get-token
        - --cluster
        - my-cluster
```

If your kubeconfig is set up like this, kubectl (and the bot) will automatically call eiamcli to get fresh tokens.

### Verify it works
```bash
# This should automatically authenticate via eiamcli
kubectl get nodes

# Then the bot will work the same way
python -m src.main chat
```

---

## Quick Reference

### Commands

```bash
# Option 1: Manual workflow
eiamcli login --cluster prod
python -m src.main chat

# Option 2: Wrapper script
./k8s-bot-cli.sh prod

# Option 3: Integrated command (after adding to main.py)
python -m src.main login prod
python -m src.main chat

# Option 4: Auto (exec-credential in kubeconfig)
python -m src.main chat  # Just works!
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `KUBECONFIG` | Path to kubeconfig | `~/.kube/config` |
| `EIAMCLI_AUTO_LOGIN` | Auto-login on startup | `true` |
| `EIAMCLI_CLUSTER` | Default cluster | `my-prod-cluster` |

---

## Troubleshooting

### "eiamcli: command not found"
```bash
# Check if eiamcli is in PATH
which eiamcli

# Add to PATH if needed
export PATH=$PATH:/path/to/eiamcli
```

### "Authentication expired"
```bash
# Re-authenticate
eiamcli login --cluster my-cluster

# Then run the bot
python -m src.main chat
```

### "Unable to connect to server"
```bash
# Verify authentication
eiamcli whoami

# Check kubectl works
kubectl get nodes

# Check kubeconfig path
echo $KUBECONFIG
```

### Token refresh issues
If tokens expire during a long chat session, you can:

1. Exit and re-authenticate:
   ```bash
   eiamcli login --cluster my-cluster
   python -m src.main chat
   ```

2. Or use the exec-credential approach (Option 4) which auto-refreshes tokens.

---

## Summary

| Option | Best For | Effort |
|--------|----------|--------|
| **Option 1** | Quick testing | None |
| **Option 2** | Daily use | Low (create script) |
| **Option 3** | Seamless integration | Medium (code changes) |
| **Option 4** | Auto token refresh | None (if already configured) |

**Recommended:** Start with Option 1 or 2. If you need tighter integration, implement Option 3.
