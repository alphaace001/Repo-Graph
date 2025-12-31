"""
Local logger setup for Analyst MCP server.
Simplified version for containerized deployment.
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with the specified name and level.

    Args:
        name: Name of the logger (typically __name__)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create console handler with formatting
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger
