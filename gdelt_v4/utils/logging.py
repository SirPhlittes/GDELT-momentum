"""
GDELT v4.0 Logging Utilities
=============================
Centralized logging configuration and utilities.

Author: Philip Hendrik Littau
Version: 4.0.0
"""

from __future__ import annotations

import logging
import sys
from typing import Optional
from pathlib import Path


# Module-level logger cache
_loggers: dict[str, logging.Logger] = {}


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    date_format: Optional[str] = None,
    log_file: Optional[str] = None,
    json_format: bool = False,
) -> None:
    """
    Configure the root logger for GDELT v4.0.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format_string: Custom log message format.
        date_format: Custom date format.
        log_file: Optional path to log file.
        json_format: Whether to output JSON-formatted logs.
    """
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    
    if date_format is None:
        date_format = "%Y-%m-%d %H:%M:%S"
    
    # Create formatter
    if json_format:
        try:
            import json
            
            class JsonFormatter(logging.Formatter):
                def format(self, record):
                    log_dict = {
                        "timestamp": self.formatTime(record, date_format),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }
                    if record.exc_info:
                        log_dict["exception"] = self.formatException(record.exc_info)
                    return json.dumps(log_dict)
            
            formatter = JsonFormatter()
        except ImportError:
            formatter = logging.Formatter(format_string, date_format)
    else:
        formatter = logging.Formatter(format_string, date_format)
    
    # Get root logger for gdelt_v4
    root_logger = logging.getLogger("gdelt_v4")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.
    
    Args:
        name: The module name (usually __name__).
        
    Returns:
        A configured logger instance.
    """
    if name not in _loggers:
        # Prefix with gdelt_v4 for consistency
        if not name.startswith("gdelt_v4"):
            full_name = f"gdelt_v4.{name}"
        else:
            full_name = name
        
        _loggers[name] = logging.getLogger(full_name)
    
    return _loggers[name]


class LogContext:
    """
    Context manager for structured logging with additional context.
    
    Example:
        >>> with LogContext(logger, operation="query", experiment="AI"):
        ...     logger.info("Starting query")
        ...     # logs: "Starting query [operation=query, experiment=AI]"
    """
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self._old_factory = None
    
    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()
        context = self.context
        
        def record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            record.context = context
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._old_factory)
        return False


