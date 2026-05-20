"""
logging_config.py
-----------------
Centralized structured logging configuration for the Binance Futures Trading Bot.

Provides:
  - Console handler with color-coded output (INFO+)
  - Rotating file handler writing to logs/trading_bot.log (DEBUG+)
  - A single `get_logger()` factory used across all modules
"""

import logging
import logging.handlers
import os
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
BACKUP_COUNT = 3               # keep last 3 rotated files

# ANSI colour codes for console output
_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"


class _ColourFormatter(logging.Formatter):
    """Adds ANSI colour to the level-name portion of console log lines."""

    FMT = "%(asctime)s  %(levelname)-8s  %(name)s  │  %(message)s"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        record.levelname = f"{colour}{record.levelname}{_RESET}"
        formatter = logging.Formatter(self.FMT, datefmt=self.DATE_FMT)
        return formatter.format(record)


class _PlainFormatter(logging.Formatter):
    """Plain text formatter for file output (no ANSI codes)."""

    FMT = "%(asctime)s  %(levelname)-8s  %(name)s  │  %(message)s"
    DATE_FMT = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        formatter = logging.Formatter(self.FMT, datefmt=self.DATE_FMT)
        return formatter.format(record)


def _setup_root_logger() -> None:
    """
    Configures the root logger once.  Subsequent calls are no-ops because
    the root logger already has handlers attached.
    """
    root = logging.getLogger()
    if root.handlers:
        return  # already initialised

    root.setLevel(logging.DEBUG)

    # ── File handler (DEBUG+, rotating) ─────────────────────────────────────
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_PlainFormatter())

    # ── Console handler (INFO+) ──────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_ColourFormatter())

    root.addHandler(file_handler)
    root.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  Call this at the top of every module:

        from src.logging_config import get_logger
        logger = get_logger(__name__)
    """
    _setup_root_logger()
    return logging.getLogger(name)
