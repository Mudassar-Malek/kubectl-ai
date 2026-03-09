# Slack Integration Guide

Integrate K8s IntelliBot with Slack so your team can query Kubernetes from any Slack channel.

---

## Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Slack     │────▶│  K8s Bot     │────▶│  Kubernetes  │
│   Channel    │◀────│  (Python)    │◀────│   Cluster    │
└──────────────┘     └──────────────┘     └──────────────┘
```

**How it works:**
1. User mentions `@k8s-bot` in Slack
2. Slack sends the message to your bot
3. Bot processes using the Agent (same as CLI)
4. Bot replies in Slack

---

## Step 1: Create a Slack App

### 1.1 Go to Slack API
Visit: https://api.slack.com/apps

### 1.2 Create New App
1. Click **"Create New App"**
2. Choose **"From scratch"**
3. Name: `K8s IntelliBot`
4. Select your workspace
5. Click **"Create App"**

---

## Step 2: Configure App Permissions

### 2.1 Add Bot Scopes
Go to **OAuth & Permissions** → **Scopes** → **Bot Token Scopes**

Add these scopes:
| Scope | Purpose |
|-------|---------|
| `app_mentions:read` | Receive @mentions |
| `chat:write` | Send messages |
| `channels:history` | Read channel messages |
| `groups:history` | Read private channel messages |
| `im:history` | Read direct messages |

### 2.2 Install to Workspace
1. Go to **OAuth & Permissions**
2. Click **"Install to Workspace"**
3. Authorize the app
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

---

## Step 3: Enable Socket Mode

### 3.1 Enable Socket Mode
1. Go to **Socket Mode** (left sidebar)
2. Toggle **"Enable Socket Mode"** ON
3. Create an App-Level Token:
   - Name: `k8s-bot-socket`
   - Scope: `connections:write`
4. Copy the **App Token** (starts with `xapp-`)

### 3.2 Enable Events
1. Go to **Event Subscriptions**
2. Toggle **"Enable Events"** ON
3. Under **Subscribe to bot events**, add:
   - `app_mention`
   - `message.im` (for direct messages)

---

## Step 4: Get Signing Secret

1. Go to **Basic Information**
2. Under **App Credentials**, copy the **Signing Secret**

---

## Step 5: Configure Environment

Add to your `.env` file:

```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
```

---

## Step 6: Install Slack Dependencies

```bash
pip install slack-bolt slack-sdk
```

Or add to requirements.txt:
```
slack-bolt>=1.18.0
slack-sdk>=3.21.0
```

---

## Step 7: Create Slack Bot Code

Create `src/slack_bot.py`:

```python
"""Slack integration for K8s IntelliBot."""

import asyncio
import os
import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.agent.core import KubernetesAgent
from src.agent.tools import KUBERNETES_TOOLS_LITE
from src.k8s.contexts import ContextManager
from src.k8s.executor import KubectlExecutor, ToolExecutor
from src.llm.providers import get_llm_provider
from src.utils.config import Config

# Initialize Slack app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Initialize K8s bot components
config = Config()
llm_provider = get_llm_provider(config)
context_manager = ContextManager(config.kubeconfig)
kubectl_executor = KubectlExecutor(config)
tool_executor = ToolExecutor(kubectl_executor, context_manager)

# Create agent
agent = KubernetesAgent(
    config=config,
    tools=KUBERNETES_TOOLS_LITE,
    tool_executor=tool_executor.execute,
    llm_provider=llm_provider,
)


def clean_message(text: str) -> str:
    """Remove bot mention from message."""
    # Remove <@BOTID> mentions
    return re.sub(r'<@[A-Z0-9]+>', '', text).strip()


@app.event("app_mention")
def handle_mention(event, say):
    """Handle @k8s-bot mentions in channels."""
    user = event["user"]
    text = clean_message(event["text"])
    
    if not text:
        say(f"Hi <@{user}>! Ask me anything about Kubernetes. Example: `@k8s-bot show me all pods`")
        return
    
    # Show typing indicator
    say(f"🔍 Looking into that for you, <@{user}>...")
    
    # Process query
    try:
        response = asyncio.run(agent.process(text))
        say(f"<@{user}>\n```\n{response}\n```")
    except Exception as e:
        say(f"<@{user}> Sorry, I encountered an error: {str(e)}")


@app.event("message")
def handle_dm(event, say):
    """Handle direct messages."""
    # Ignore bot's own messages
    if event.get("bot_id"):
        return
    
    text = event.get("text", "")
    
    if not text:
        return
    
    # Process query
    try:
        response = asyncio.run(agent.process(text))
        say(f"```\n{response}\n```")
    except Exception as e:
        say(f"Sorry, I encountered an error: {str(e)}")


def main():
    """Start the Slack bot."""
    print("⚡ K8s IntelliBot Slack integration starting...")
    
    # Validate setup
    available, msg = llm_provider.is_available()
    if not available:
        print(f"❌ LLM not available: {msg}")
        return
    
    print(f"✓ LLM: {llm_provider.name}")
    print(f"✓ Cluster: {context_manager.get_current_context()}")
    print("✓ Slack bot ready! Listening for messages...")
    
    # Start socket mode handler
    handler = SocketModeHandler(
        app=app,
        app_token=os.environ.get("SLACK_APP_TOKEN")
    )
    handler.start()


if __name__ == "__main__":
    main()
```

---

## Step 8: Run the Slack Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the Slack bot
python -m src.slack_bot
```

Expected output:
```
⚡ K8s IntelliBot Slack integration starting...
✓ LLM: Ollama (llama3.2:3b)
✓ Cluster: minikube
✓ Slack bot ready! Listening for messages...
```

---

## Step 9: Test in Slack

### In a Channel
```
@k8s-bot show me all pods
```

### Direct Message
Just message the bot directly:
```
show me all pods in kube-system
```

---

## Usage Examples

| Message | What it does |
|---------|--------------|
| `@k8s-bot show me all pods` | Lists pods |
| `@k8s-bot why is my nginx pod failing?` | Investigates pod issues |
| `@k8s-bot describe deployment web-app` | Shows deployment details |
| `@k8s-bot what events happened recently?` | Shows cluster events |

---

## Running in Production

### Option 1: Systemd Service

Create `/etc/systemd/system/k8s-slack-bot.service`:

```ini
[Unit]
Description=K8s IntelliBot Slack Integration
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/k8s-bot
Environment="PATH=/opt/k8s-bot/venv/bin"
EnvironmentFile=/opt/k8s-bot/.env
ExecStart=/opt/k8s-bot/venv/bin/python -m src.slack_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable k8s-slack-bot
sudo systemctl start k8s-slack-bot
```

### Option 2: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "src.slack_bot"]
```

```bash
docker build -t k8s-slack-bot .
docker run -d --env-file .env k8s-slack-bot
```

---

## Architecture with Slack

```
┌─────────────────────────────────────────────────────────────┐
│                      SLACK WORKSPACE                         │
│                                                              │
│  #dev-ops channel                                            │
│  ┌────────────────────────────────────────────────────┐     │
│  │ @alice: @k8s-bot why is my pod crashing?          │     │
│  │                                                    │     │
│  │ @k8s-bot: Looking into that for you...            │     │
│  │                                                    │     │
│  │ @k8s-bot: Your pod my-app is crashing because     │     │
│  │ the config file is missing. Here's how to fix it: │     │
│  │ ...                                                │     │
│  └────────────────────────────────────────────────────┘     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            │ Socket Mode (WebSocket)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    slack_bot.py                              │
│                                                              │
│   @app.event("app_mention")                                  │
│   def handle_mention(event, say):                            │
│       query = clean_message(event["text"])                   │
│       response = agent.process(query)  ◄──────┐              │
│       say(response)                           │              │
│                                               │              │
└───────────────────────────────────────────────┼──────────────┘
                                                │
                                                │ Same agent
                                                │ as CLI
                                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent + LLM + Executor                  │
│                                                              │
│   (Exactly the same code as the CLI version)                │
│                                                              │
└───────────────────────────────────────────────┬─────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Checklist

- [ ] Created Slack App at api.slack.com
- [ ] Added bot scopes (app_mentions:read, chat:write, etc.)
- [ ] Enabled Socket Mode
- [ ] Created App-Level Token
- [ ] Enabled Event Subscriptions (app_mention, message.im)
- [ ] Copied Bot Token, App Token, Signing Secret
- [ ] Added tokens to `.env`
- [ ] Installed slack-bolt and slack-sdk
- [ ] Created `src/slack_bot.py`
- [ ] Tested with `@k8s-bot hello`

---

## Troubleshooting

### "invalid_auth" error
Your `SLACK_BOT_TOKEN` is incorrect. Get a new one from OAuth & Permissions.

### "not_allowed_token_type" error
You're using the wrong token. Make sure:
- `SLACK_BOT_TOKEN` starts with `xoxb-`
- `SLACK_APP_TOKEN` starts with `xapp-`

### Bot doesn't respond to mentions
1. Check Event Subscriptions are enabled
2. Verify `app_mention` event is subscribed
3. Ensure bot is invited to the channel: `/invite @k8s-bot`

### Socket connection fails
1. Verify Socket Mode is enabled
2. Check `SLACK_APP_TOKEN` is correct
3. Ensure firewall allows outbound WebSocket connections

---

That's it! Your K8s IntelliBot is now available in Slack.
