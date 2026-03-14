"""Centralized logging configuration for Auto-Sentinel."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


APP_LOGGER_NAME = "auto_sentinel"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(log_dir: Path | None = None) -> logging.Logger:
    """Configures application-wide logging.

    Args:
        log_dir: Optional custom directory for log files.

    Returns:
        logging.Logger: The root application logger.
    """

    resolved_log_dir = log_dir or Path.cwd() / "logs"
    resolved_log_dir.mkdir(parents=True, exist_ok=True)
    log_path = resolved_log_dir / "auto_sentinel.log"

    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    logger.propagate = False
    logging.captureWarnings(True)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Creates a child logger under the application namespace.

    Args:
        name: The child logger suffix.

    Returns:
        logging.Logger: A namespaced child logger.
    """

    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")
