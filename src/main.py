"""K8s IntelliBot - Interactive CLI entry point."""

import asyncio
import sys
from typing import Optional

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from src.agent.core import KubernetesAgent
from src.agent.tools import KUBERNETES_TOOLS, KUBERNETES_TOOLS_LITE
from src.k8s.contexts import ContextManager
from src.k8s.executor import ConfirmationRequest, KubectlExecutor, ToolExecutor
from src.k8s.validators import RiskLevel
from src.llm.providers import get_llm_provider
from src.utils.config import Config
from src.utils.logger import get_console, get_logger, setup_logger


console = Console()
logger = get_logger("cli")


def print_banner(config: Config):
    """Print the welcome banner with provider info."""
    provider_info = f"LLM: {config.llm_provider.upper()} ({config.model})"
    if config.is_using_ollama:
        provider_info += " [FREE]"

    banner = f"""
╔═══════════════════════════════════════════════════════════════╗
║             🤖 K8s IntelliBot - Kubernetes AI Assistant       ║
║                                                               ║
║  Ask questions about your cluster in natural language.        ║
║  Type 'help' for commands, 'quit' to exit.                    ║
║                                                               ║
║  {provider_info:<59} ║
╚═══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold blue")


def print_context_info(context_manager: ContextManager):
    """Print current context information."""
    ctx = context_manager.get_current_context()
    platform = context_manager.detect_platform()

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="green")

    table.add_row("Context:", ctx.name or "Not set")
    table.add_row("Cluster:", ctx.cluster or "Unknown")
    table.add_row("Platform:", platform.value)
    table.add_row("Namespace:", ctx.namespace or "default")

    console.print(Panel(table, title="Current Cluster", border_style="blue"))


def confirmation_handler(request: ConfirmationRequest) -> bool:
    """Handle confirmation requests for operations."""
    
    # Pre-hook: Show command and ask for approval (for SAFE commands when confirm_commands is enabled)
    if request.risk_level == RiskLevel.SAFE:
        console.print()
        console.print(
            Panel(
                f"[bold cyan]📋 Command to Execute[/]\n\n"
                f"[code]{request.command}[/code]",
                title="Command Approval",
                border_style="cyan",
            )
        )
        return Confirm.ask("Execute this command?", default=True)
    
    # Dangerous operations
    risk_colors = {
        RiskLevel.MODERATE: "yellow",
        RiskLevel.DANGEROUS: "orange1",
        RiskLevel.CRITICAL: "red",
    }

    color = risk_colors.get(request.risk_level, "yellow")

    console.print()
    console.print(
        Panel(
            f"[bold {color}]⚠️  {request.risk_level.value.upper()} OPERATION[/]\n\n"
            f"Command: [code]{request.command}[/code]\n\n"
            f"{request.description}",
            title="Confirmation Required",
            border_style=color,
        )
    )

    return Confirm.ask("Do you want to proceed?", default=False)


def print_help():
    """Print help information."""
    help_text = """
## Available Commands

| Command | Description |
|---------|-------------|
| `help` | Show this help message |
| `quit` / `exit` | Exit the chatbot |
| `clear` | Clear conversation history |
| `context` | Show current cluster context |
| `contexts` | List all available contexts |
| `switch <name>` | Switch to a different context |

## Example Queries

- "Show me all pods in the default namespace"
- "Why is my nginx deployment not working?"
- "List all services across all namespaces"
- "Get the logs from the api-server pod"
- "Scale the web deployment to 5 replicas"
- "Describe the ingress controller"
- "What's consuming the most memory?"

## Tips

- The bot will automatically gather information for troubleshooting
- Destructive operations (delete, scale, apply) require confirmation
- Use natural language - no need to know exact kubectl syntax
"""
    console.print(Markdown(help_text))


async def handle_command(
    command: str,
    agent: KubernetesAgent,
    context_manager: ContextManager,
) -> bool:
    """Handle special commands.

    Returns True if command was handled, False to process as query.
    """
    cmd = command.strip().lower()

    if cmd in ("quit", "exit", "q"):
        console.print("\n[dim]Goodbye! 👋[/dim]")
        return True

    if cmd == "help":
        print_help()
        return True

    if cmd == "clear":
        agent.reset_conversation()
        console.print("[dim]Conversation history cleared.[/dim]")
        return True

    if cmd == "context":
        print_context_info(context_manager)
        return True

    if cmd == "contexts":
        contexts = context_manager.list_contexts()
        table = Table(title="Available Contexts")
        table.add_column("", width=1)
        table.add_column("Name")
        table.add_column("Cluster")
        table.add_column("Platform")

        for ctx in contexts:
            marker = "*" if ctx.is_current else " "
            platform = context_manager.detect_platform(ctx.name)
            table.add_row(marker, ctx.name, ctx.cluster, platform.value)

        console.print(table)
        return True

    if cmd.startswith("switch "):
        context_name = command[7:].strip()
        if context_manager.switch_context(context_name):
            console.print(f"[green]Switched to context: {context_name}[/green]")
        else:
            console.print(f"[red]Failed to switch to context: {context_name}[/red]")
        return True

    return False


async def process_query(agent: KubernetesAgent, query: str, use_spinner: bool = True):
    """Process a user query through the agent."""
    if use_spinner:
        with console.status("[bold blue]Thinking...", spinner="dots"):
            response = await agent.run(query)
    else:
        console.print("[bold blue]Processing...[/bold blue]")
        response = await agent.run(query)

    if response.success:
        console.print()
        console.print(Panel(Markdown(response.text), border_style="green"))

        if response.tool_calls_made > 0:
            console.print(
                f"[dim]({response.tool_calls_made} tool calls made)[/dim]"
            )
    else:
        console.print()
        console.print(
            Panel(
                f"[red]{response.text}[/red]",
                title="Error",
                border_style="red",
            )
        )


async def interactive_loop(config: Config):
    """Main interactive chat loop."""
    # Validate LLM provider first
    llm_provider = get_llm_provider(config)
    llm_available, llm_msg = llm_provider.is_available()

    if not llm_available:
        console.print(f"[red]LLM Error: {llm_msg}[/red]")
        if config.is_using_ollama:
            console.print("\n[yellow]To set up Ollama (free, local LLM):[/yellow]")
            console.print("  1. Install: https://ollama.ai")
            console.print("  2. Start:   ollama serve")
            console.print(f"  3. Pull:    ollama pull {config.model}")
            console.print("\n[dim]Or set ANTHROPIC_API_KEY to use Claude API[/dim]")
        sys.exit(1)

    context_manager = ContextManager(config.kubeconfig)
    kubectl_executor = KubectlExecutor(config, confirmation_handler=confirmation_handler)
    tool_executor = ToolExecutor(kubectl_executor, context_manager)

    # Use lite tools for Ollama (smaller context, faster inference)
    tools = KUBERNETES_TOOLS_LITE if config.is_using_ollama else KUBERNETES_TOOLS

    agent = KubernetesAgent(
        config=config,
        tools=tools,
        tool_executor=tool_executor.execute,
        console=console,
        llm_provider=llm_provider,
    )

    print_banner(config)
    console.print(f"[green]✓ {llm_msg}[/green]\n")
    print_context_info(context_manager)

    valid, msg = context_manager.validate_connection()
    if not valid:
        console.print(f"[yellow]Warning: {msg}[/yellow]")
        console.print("[dim]Some commands may not work without cluster access.[/dim]\n")

    console.print()

    while True:
        try:
            query = Prompt.ask("[bold cyan]You[/bold cyan]")

            if not query.strip():
                continue

            if query.strip().lower() in ("quit", "exit", "q"):
                console.print("\n[dim]Goodbye! 👋[/dim]")
                break

            handled = await handle_command(query, agent, context_manager)
            if not handled:
                # Disable spinner when confirm_commands is enabled (spinner blocks input)
                use_spinner = not config.confirm_commands
                await process_query(agent, query, use_spinner=use_spinner)

            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Use 'quit' to exit.[/dim]")
        except EOFError:
            console.print("\n[dim]Goodbye! 👋[/dim]")
            break


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    "-c",
    "config_file",
    type=click.Path(exists=True),
    help="Path to .env configuration file",
)
@click.option(
    "--safe-mode/--no-safe-mode",
    default=True,
    help="Require confirmation for destructive operations",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Run in dry-run mode (no actual changes)",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
@click.pass_context
def cli(ctx, config_file: Optional[str], safe_mode: bool, dry_run: bool, debug: bool):
    """K8s IntelliBot - AI-powered Kubernetes assistant.

    Start an interactive session to manage your Kubernetes clusters
    using natural language.
    """
    config = Config.load(config_file)

    if safe_mode is not None:
        config.safe_mode = safe_mode
    if dry_run:
        config.dry_run = dry_run
    if debug:
        config.log_level = "DEBUG"

    setup_logger("k8s-bot", config.log_level)
    setup_logger("agent", config.log_level)
    setup_logger("executor", config.log_level)

    errors = config.validate()
    if errors:
        for error in errors:
            console.print(f"[red]Configuration error: {error}[/red]")
        sys.exit(1)

    ctx.ensure_object(dict)
    ctx.obj["config"] = config

    if ctx.invoked_subcommand is None:
        asyncio.run(interactive_loop(config))


@cli.command()
@click.pass_context
def chat(ctx):
    """Start interactive chat mode.

    Example: k8s-bot chat
    """
    config = ctx.obj["config"]
    asyncio.run(interactive_loop(config))


@cli.command()
@click.argument("query", nargs=-1, required=True)
@click.pass_context
def ask(ctx, query: tuple[str, ...]):
    """Ask a single question without entering interactive mode.

    Example: k8s-bot ask "show me all pods"
    """
    config = ctx.obj["config"]
    full_query = " ".join(query)

    async def run_single_query():
        # Validate LLM provider
        llm_provider = get_llm_provider(config)
        llm_available, llm_msg = llm_provider.is_available()
        if not llm_available:
            console.print(f"[red]LLM Error: {llm_msg}[/red]")
            return

        context_manager = ContextManager(config.kubeconfig)
        kubectl_executor = KubectlExecutor(config, confirmation_handler=confirmation_handler)
        tool_executor = ToolExecutor(kubectl_executor, context_manager)

        # Use lite tools for Ollama
        tools = KUBERNETES_TOOLS_LITE if config.is_using_ollama else KUBERNETES_TOOLS

        agent = KubernetesAgent(
            config=config,
            tools=tools,
            tool_executor=tool_executor.execute,
            console=console,
            llm_provider=llm_provider,
        )

        # Disable spinner when confirm_commands is enabled
        use_spinner = not config.confirm_commands
        await process_query(agent, full_query, use_spinner=use_spinner)

    asyncio.run(run_single_query())


@cli.command()
@click.pass_context
def contexts(ctx):
    """List all available Kubernetes contexts."""
    config = ctx.obj["config"]
    context_manager = ContextManager(config.kubeconfig)

    contexts_list = context_manager.list_contexts()
    table = Table(title="Available Contexts")
    table.add_column("Current", width=1)
    table.add_column("Name")
    table.add_column("Cluster")
    table.add_column("Platform")

    for ctx_item in contexts_list:
        marker = "*" if ctx_item.is_current else ""
        platform = context_manager.detect_platform(ctx_item.name)
        table.add_row(marker, ctx_item.name, ctx_item.cluster, platform.value)

    console.print(table)


@cli.command()
@click.argument("context_name")
@click.pass_context
def switch(ctx, context_name: str):
    """Switch to a different Kubernetes context."""
    config = ctx.obj["config"]
    context_manager = ContextManager(config.kubeconfig)

    if context_manager.switch_context(context_name):
        console.print(f"[green]Switched to context: {context_name}[/green]")
        print_context_info(context_manager)
    else:
        console.print(f"[red]Failed to switch to context: {context_name}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate LLM provider, cluster connection, and configuration."""
    config = ctx.obj["config"]
    context_manager = ContextManager(config.kubeconfig)
    has_errors = False

    console.print("[bold]Validating configuration...[/bold]\n")

    config_errors = config.validate()
    if config_errors:
        console.print("[red]Configuration errors:[/red]")
        for error in config_errors:
            console.print(f"  - {error}")
        has_errors = True
    else:
        console.print("[green]✓ Configuration valid[/green]")

    # Validate LLM provider
    console.print("\n[bold]Validating LLM provider...[/bold]\n")
    llm_provider = get_llm_provider(config)
    llm_valid, llm_msg = llm_provider.is_available()
    if llm_valid:
        console.print(f"[green]✓ {llm_msg}[/green]")
    else:
        console.print(f"[red]✗ {llm_msg}[/red]")
        if config.is_using_ollama:
            console.print("\n[yellow]To set up Ollama:[/yellow]")
            console.print("  1. Install: https://ollama.ai")
            console.print("  2. Start:   ollama serve")
            console.print(f"  3. Pull:    ollama pull {config.model}")
        has_errors = True

    console.print("\n[bold]Validating cluster connection...[/bold]\n")
    valid, msg = context_manager.validate_connection()
    if valid:
        console.print(f"[green]✓ {msg}[/green]")
        print_context_info(context_manager)
    else:
        console.print(f"[red]✗ {msg}[/red]")
        has_errors = True

    if has_errors:
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Check cluster health and get a health score.
    
    Example: k8s-bot health
    """
    import asyncio
    from src.k8s.health import ClusterHealthChecker
    
    config = ctx.obj["config"]
    
    console.print("[bold]Checking cluster health...[/bold]\n")
    
    checker = ClusterHealthChecker(config.kubeconfig)
    report = asyncio.run(checker.get_health_report())
    
    console.print(report.to_string())


@cli.command()
@click.pass_context
def security(ctx):
    """Run security audit on the cluster.
    
    Example: k8s-bot security
    """
    import asyncio
    from src.k8s.health import SecurityAuditor
    
    config = ctx.obj["config"]
    
    console.print("[bold]Running security audit...[/bold]\n")
    
    auditor = SecurityAuditor(config.kubeconfig)
    report = asyncio.run(auditor.get_audit_report())
    
    console.print(report.to_string())


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
