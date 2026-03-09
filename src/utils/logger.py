"""Structured logging for K8s IntelliBot."""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

_loggers: dict[str, logging.Logger] = {}
_console: Optional[Console] = None


def get_console() -> Console:
    """Get or create the shared Rich console."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def setup_logger(
    name: str = "k8s-bot",
    level: str = "INFO",
    rich_output: bool = True,
) -> logging.Logger:
    """Set up and return a configured logger.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        rich_output: Use Rich for formatted output

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    if rich_output:
        handler = RichHandler(
            console=get_console(),
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(handler)
    _loggers[name] = logger

    return logger


def get_logger(name: str = "k8s-bot") -> logging.Logger:
    """Get an existing logger or create a new one with defaults."""
    if name not in _loggers:
        return setup_logger(name)
    return _loggers[name]
