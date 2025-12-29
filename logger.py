import logging
import sys
import uuid
from datetime import datetime
from typing import Optional
from contextvars import ContextVar

# Context variable to store correlation ID across async operations
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record):
        record.correlation_id = correlation_id_var.get() or 'N/A'
        return True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record):
        log_data = {
            'level': record.levelname,
            'correlation_id': getattr(record, 'correlation_id', 'N/A'),
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add any extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Format as key=value pairs for easy parsing
        formatted_parts = [f"{k}={v}" for k, v in log_data.items()]
        return ' | '.join(formatted_parts)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a structured logger with correlation ID support.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Add correlation ID filter
    console_handler.addFilter(CorrelationIdFilter())
    
    # Add structured formatter
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
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
        correlation_id = str(uuid.uuid4())
    
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
