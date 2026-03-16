"""Slack integration for K8s IntelliBot."""

import asyncio
import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
except ImportError:
    print("Slack dependencies not installed. Run: pip install slack-bolt slack-sdk")
    exit(1)

from src.agent.core import KubernetesAgent
from src.agent.tools import KUBERNETES_TOOLS_LITE
from src.k8s.contexts import ContextManager
from src.k8s.executor import KubectlExecutor, ToolExecutor
from src.llm.providers import get_llm_provider
from src.utils.config import Config


def get_env_or_exit(key: str) -> str:
    """Get environment variable or exit with error."""
    value = os.environ.get(key)
    if not value:
        print(f"❌ Missing required environment variable: {key}")
        print(f"   Add it to your .env file")
        exit(1)
    return value


# Validate Slack tokens
SLACK_BOT_TOKEN = get_env_or_exit("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = get_env_or_exit("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = get_env_or_exit("SLACK_SIGNING_SECRET")

# Initialize Slack app
app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# Initialize K8s bot components
config = Config()
llm_provider = get_llm_provider(config)
context_manager = ContextManager(config.kubeconfig)

# Simple confirmation handler that auto-approves safe commands
def auto_confirm(request) -> bool:
    """Auto-approve safe commands, reject dangerous ones in Slack."""
    from src.k8s.validators import RiskLevel
    if request.risk_level in [RiskLevel.DANGEROUS, RiskLevel.CRITICAL]:
        return False
    return True

kubectl_executor = KubectlExecutor(config, confirmation_handler=auto_confirm)
tool_executor = ToolExecutor(kubectl_executor, context_manager)

# Create agent (will be recreated per-request for conversation isolation)
def create_agent() -> KubernetesAgent:
    """Create a fresh agent for each request."""
    return KubernetesAgent(
        config=config,
        tools=KUBERNETES_TOOLS_LITE,
        tool_executor=tool_executor.execute,
        llm_provider=llm_provider,
    )


def clean_message(text: str) -> str:
    """Remove bot mention and clean up message."""
    # Remove <@BOTID> mentions
    text = re.sub(r'<@[A-Z0-9]+>', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text.strip()


def format_response(response: str, max_length: int = 3000) -> str:
    """Format response for Slack."""
    # Truncate if too long
    if len(response) > max_length:
        response = response[:max_length] + "\n... (truncated)"
    return response


@app.event("app_mention")
def handle_mention(event, say, logger):
    """Handle @k8s-bot mentions in channels."""
    user = event["user"]
    channel = event["channel"]
    text = clean_message(event.get("text", ""))
    
    logger.info(f"Mention from {user} in {channel}: {text}")
    
    if not text:
        say(
            f"Hi <@{user}>! 👋 I'm K8s IntelliBot.\n\n"
            "Ask me anything about Kubernetes. Examples:\n"
            "• `@k8s-bot show me all pods`\n"
            "• `@k8s-bot why is my deployment failing?`\n"
            "• `@k8s-bot describe pod nginx`"
        )
        return
    
    # Show typing indicator
    say(f"🔍 Looking into that for you, <@{user}>...")
    
    # Process query with fresh agent
    try:
        agent = create_agent()
        result = asyncio.run(agent.run(text))
        formatted = format_response(result.text)
        say(f"<@{user}>\n```\n{formatted}\n```")
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        say(f"<@{user}> Sorry, I encountered an error: {str(e)}")


@app.event("message")
def handle_dm(event, say, logger):
    """Handle direct messages."""
    # Ignore bot's own messages and message_changed events
    if event.get("bot_id") or event.get("subtype"):
        return
    
    # Only handle DMs (channel type 'im')
    if event.get("channel_type") != "im":
        return
    
    text = event.get("text", "").strip()
    user = event.get("user", "unknown")
    
    logger.info(f"DM from {user}: {text}")
    
    if not text:
        return
    
    # Process query with fresh agent
    try:
        agent = create_agent()
        result = asyncio.run(agent.run(text))
        formatted = format_response(result.text)
        say(f"```\n{formatted}\n```")
    except Exception as e:
        logger.error(f"Error processing DM: {e}")
        say(f"Sorry, I encountered an error: {str(e)}")


@app.command("/k8s")
def handle_slash_command(ack, respond, command, logger):
    """Handle /k8s slash command."""
    ack()  # Acknowledge immediately
    
    text = command.get("text", "").strip()
    user = command.get("user_id")
    
    logger.info(f"Slash command from {user}: {text}")
    
    if not text:
        respond(
            "Usage: `/k8s <your question>`\n\n"
            "Examples:\n"
            "• `/k8s show me all pods`\n"
            "• `/k8s what's wrong with my deployment?`"
        )
        return
    
    respond(f"🔍 Processing your request...")
    
    try:
        agent = create_agent()
        result = asyncio.run(agent.run(text))
        formatted = format_response(result.text)
        respond(f"```\n{formatted}\n```")
    except Exception as e:
        logger.error(f"Error processing slash command: {e}")
        respond(f"Sorry, I encountered an error: {str(e)}")


def main():
    """Start the Slack bot."""
    print("=" * 50)
    print("⚡ K8s IntelliBot Slack Integration")
    print("=" * 50)
    
    # Validate LLM
    available, msg = llm_provider.is_available()
    if not available:
        print(f"❌ LLM not available: {msg}")
        exit(1)
    print(f"✓ LLM: {llm_provider.name}")
    
    # Validate cluster
    try:
        current = context_manager.get_current_context()
        print(f"✓ Cluster: {current}")
    except Exception as e:
        print(f"❌ Cluster error: {e}")
        exit(1)
    
    print("✓ Slack tokens configured")
    print("-" * 50)
    print("Bot is ready! Listening for messages...")
    print("  • Mention @k8s-bot in any channel")
    print("  • Send direct messages")
    print("  • Use /k8s slash command")
    print("-" * 50)
    
    # Start socket mode handler
    handler = SocketModeHandler(app=app, app_token=SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()
