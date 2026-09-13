"""
Wonderland Online Logging & Diagnostic Subsystem
Provides thread-safe rotating file persistence and unified streaming handlers.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: Optional[str] = None,
    log_filename: str = "server.log",
    level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB per file
    backup_count: int = 5,
) -> str:
    """
    Configures unified rotating file logging and console streaming.
    Returns the absolute path to the active log file.
    """
    if log_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "logs")

    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.abspath(os.path.join(log_dir, log_filename))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    # Avoid duplicate file handlers on reload
    has_file_handler = False
    for handler in root_logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            if os.path.abspath(getattr(handler, "baseFilename", "")) == log_file_path:
                has_file_handler = True
                break

    if not has_file_handler:
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Ensure console handler exists
    has_stream = False
    for handler in root_logger.handlers:
        if type(handler) is logging.StreamHandler:
            has_stream = True
            break

    if not has_stream:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)

    return log_file_path
