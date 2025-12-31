"""
Centralized logging module for KG-Assignment.
Provides MCP-safe structured logging with correlation ID support.

Key features:
- MCP-safe: Logs to stderr (not stdout) to avoid interfering with MCP protocol
- Structured logging with correlation IDs for request tracing
- Configurable via environment variables
- @mcp_tool_logged decorator for automatic correlation ID management
"""

import logging
import sys
import os
import uuid
import time
import functools
from datetime import datetime
from typing import Optional, Callable, Any
from contextvars import ContextVar
from pathlib import Path

# Context variable to store correlation ID across async operations
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

# Environment variable configuration
MCP_LOGGING_MODE = os.getenv("MCP_LOGGING_MODE", "stderr")  # stderr, file, disabled
MCP_LOG_FILE = os.getenv("MCP_LOG_FILE", "mcp_server.log")
MCP_LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO")

# Cache for configured loggers
_configured_loggers: dict = {}


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record):
        record.correlation_id = correlation_id_var.get() or 'N/A'
        return True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record):
        correlation_id = getattr(record, 'correlation_id', None)
        
        log_data = {
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Only include correlation_id if it has a real value
        if correlation_id and correlation_id != 'N/A':
            log_data['correlation_id'] = correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Format as key=value pairs for easy parsing
        formatted_parts = [f"{k}={v}" for k, v in log_data.items()]
        return ' | '.join(formatted_parts)


def _get_log_level() -> int:
    """Get logging level from environment variable."""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return level_map.get(MCP_LOG_LEVEL.upper(), logging.INFO)


def setup_logger(name: str, level: int = None) -> logging.Logger:
    """
    Set up a structured logger with correlation ID support.
    Uses stderr by default for MCP compatibility.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: from MCP_LOG_LEVEL env var)
    
    Returns:
        Configured logger instance
    """
    if level is None:
        level = _get_log_level()
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Check if logging is disabled
    if MCP_LOGGING_MODE == "disabled":
        logger.addHandler(logging.NullHandler())
        return logger
    
    # Add correlation ID filter
    correlation_filter = CorrelationIdFilter()
    
    # Add structured formatter
    formatter = StructuredFormatter()
    
    # Console handler (stderr for MCP safety)
    if MCP_LOGGING_MODE in ("stderr", "both"):
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.addFilter(correlation_filter)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if MCP_LOGGING_MODE in ("file", "both"):
        try:
            file_handler = logging.FileHandler(MCP_LOG_FILE, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.addFilter(correlation_filter)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, fall back to stderr
            if MCP_LOGGING_MODE == "file":
                console_handler = logging.StreamHandler(sys.stderr)
                console_handler.setLevel(level)
                console_handler.addFilter(correlation_filter)
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
                logger.warning(f"Failed to create log file, falling back to stderr: {e}")
    
    return logger


def get_mcp_safe_logger(name: str, level: int = None) -> logging.Logger:
    """
    Get a logger configured for MCP-safe operation.
    This is the recommended function for MCP servers.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: from MCP_LOG_LEVEL env var)
    
    Returns:
        MCP-safe configured logger instance
    """
    if name in _configured_loggers:
        return _configured_loggers[name]
    
    logger = setup_logger(name, level)
    _configured_loggers[name] = logger
    return logger


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set a correlation ID for the current context.
    
    Args:
        correlation_id: Optional correlation ID. If not provided, generates a new UUID.
    
    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]  # Short UUID for readability
    
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.
    
    Returns:
        Current correlation ID or None if not set
    """
    return correlation_id_var.get()


def clear_correlation_id():
    """Clear the correlation ID from the current context."""
    correlation_id_var.set(None)


class LogContext:
    """Context manager for logging with correlation IDs."""
    
    def __init__(self, correlation_id: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """
        Initialize log context.
        
        Args:
            correlation_id: Optional correlation ID. If not provided, generates a new UUID.
            logger: Optional logger to log entry/exit
        """
        self.correlation_id = correlation_id
        self.logger = logger
        self.previous_correlation_id = None
    
    def __enter__(self):
        self.previous_correlation_id = get_correlation_id()
        self.correlation_id = set_correlation_id(self.correlation_id)
        
        if self.logger:
            self.logger.debug(f"Starting context with correlation_id={self.correlation_id}")
        
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.logger:
            if exc_type:
                self.logger.error(f"Context ended with error: {exc_val}", exc_info=True)
            else:
                self.logger.debug(f"Context ended successfully with correlation_id={self.correlation_id}")
        
        # Restore previous correlation ID
        if self.previous_correlation_id:
            correlation_id_var.set(self.previous_correlation_id)
        else:
            clear_correlation_id()


def log_with_context(logger: logging.Logger, level: int, message: str, **kwargs):
    """
    Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Logging level
        message: Log message
        **kwargs: Additional fields to include in log
    """
    extra = {'extra_fields': kwargs}
    logger.log(level, message, extra=extra)


def mcp_tool_logged(func: Callable) -> Callable:
    """
    Decorator for MCP tool functions that automatically:
    1. Generates a unique correlation ID for each tool invocation
    2. Attaches correlation ID to all log messages within the tool
    3. Logs tool entry/exit with timing information
    
    Usage:
        @mcp.tool()
        @mcp_tool_logged
        def my_tool(arg1: str) -> str:
            # All logs here will include the correlation ID
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        correlation_id = set_correlation_id()
        logger = get_mcp_safe_logger(func.__module__)
        
        # Log tool invocation
        args_preview = str(args)[:100] if args else ""
        kwargs_preview = str(kwargs)[:100] if kwargs else ""
        logger.info(
            f"Tool invoked: {func.__name__}",
            extra={'extra_fields': {
                'tool': func.__name__,
                'args': args_preview,
                'kwargs': kwargs_preview
            }}
        )
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(
                f"Tool completed: {func.__name__}",
                extra={'extra_fields': {
                    'tool': func.__name__,
                    'elapsed_ms': int(elapsed * 1000),
                    'status': 'success'
                }}
            )
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"Tool failed: {func.__name__}: {str(e)}",
                extra={'extra_fields': {
                    'tool': func.__name__,
                    'elapsed_ms': int(elapsed * 1000),
                    'status': 'error',
                    'error': str(e)
                }}
            )
            raise
        finally:
            clear_correlation_id()
    
    return wrapper


def configure_mcp_logging():
    """
    Configure logging for MCP server environment.
    Call this at the start of your MCP server to suppress
    any logging that might interfere with MCP protocol.
    
    This function:
    1. Suppresses all root logger output to stdout
    2. Configures the logging system to use stderr only
    """
    # Disable any existing root handlers that might write to stdout
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            root_logger.removeHandler(handler)
    
    # Set root logger to only output critical errors
    root_logger.setLevel(logging.CRITICAL)
    
    # Configure basicConfig to use stderr
    logging.basicConfig(
        level=logging.CRITICAL,
        format="",
        stream=sys.stderr,
        force=True
    )


# Initialize MCP-safe configuration when module is imported
if MCP_LOGGING_MODE != "disabled":
    configure_mcp_logging()
