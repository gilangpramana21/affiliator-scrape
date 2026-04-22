"""Structured logging setup using structlog."""

import logging
import logging.handlers
import sys
from typing import Optional

import structlog


def configure_logging(log_level: str = "INFO", log_file: str = "logs/scraper.log") -> None:
    """Configure structured logging with console and file handlers.

    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to the log file for rotating file handler.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors for all renderers
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    # Remove existing handlers to avoid duplicates on reconfiguration
    root_logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=shared_processors,
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler with JSON output
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog BoundLogger bound to the given component name.

    Args:
        name: Logger / component name.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)


def log_progress(current: int, total: int, component: str) -> None:
    """Log scraping progress.

    Args:
        current: Number of items processed so far.
        total: Total number of items to process.
        component: Name of the component reporting progress.
    """
    logger = get_logger(component)
    if total > 0:
        percentage = (current / total) * 100
        logger.info(
            "progress",
            current=current,
            total=total,
            percentage=round(percentage, 1),
        )
    else:
        logger.info("progress", current=current, total=total, percentage=0.0)
