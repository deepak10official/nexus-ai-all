"""
Application logging.

WHAT COUNTS AS A "RUN"
A run is one scan cycle, not one process. The dev server stays up for
hours under --reload, so a file stamped with boot time would grow into a
single endless trace. Instead, pressing "Scan now" (or the first scan
after startup) closes the previous file and opens a new one. Everything
downstream of that scan — scoring, drafting, retries, image generation,
review decisions — lands in that same file, so one file reads as one
complete story from trend fetch to final approval.

FILE LOCATION
Resolved from this module's own path, not the working directory, so logs
land in <project root>/logs whether uvicorn was launched from backend/,
from the repo root, or from an IDE.

CONFIGURATION (all optional, via .env)
    LOG_LEVEL       DEBUG | INFO | WARNING | ERROR      default INFO
    LOG_DIR         path, absolute or relative to root  default logs
    LOG_TO_FILE     true | false                        default true
    LOG_TO_CONSOLE  true | false                        default true
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from pathlib import Path

# backend/utils/logging.py -> backend/utils -> backend -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

LOGGER_NAME = "trendradar"

_lock = threading.Lock()
_file_handler: logging.FileHandler | None = None
_current_path: Path | None = None
_run_id: str = "boot"
_configured = False


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _log_dir() -> Path:
    raw = os.getenv("LOG_DIR", "logs").strip() or "logs"
    p = Path(raw)
    return p if p.is_absolute() else PROJECT_ROOT / p


class _RunIdFilter(logging.Filter):
    """Stamps every record with the active run, so interleaved requests
    stay attributable even when several are in flight."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = _run_id
        return True


_FORMAT = "%(asctime)s | %(levelname)-7s | %(run_id)s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure() -> None:
    """
    Install console logging and capture uvicorn's own loggers.

    Deliberately does NOT open a log file. Opening one here would stamp it
    with process boot time, which is the thing this module exists to
    avoid. The first start_run() opens the first file.
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # handlers do the real filtering

    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    fmt = logging.Formatter(_FORMAT, datefmt=_DATEFMT)
    run_filter = _RunIdFilter()

    for h in list(root.handlers):
        root.removeHandler(h)

    if _env_bool("LOG_TO_CONSOLE", True):
        console = logging.StreamHandler()
        console.setLevel(level)
        console.setFormatter(fmt)
        console.addFilter(run_filter)
        root.addHandler(console)

    # uvicorn installs its own handlers; strip them so its records
    # propagate to root and land in our file rather than being duplicated
    # or lost.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    # httpx logs every outbound request at INFO, which drowns the trace.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)

    _configured = True
    get_logger("logging").info(
        "logging configured | level=%s | dir=%s | file=%s | console=%s",
        logging.getLevelName(level),
        _log_dir(),
        _env_bool("LOG_TO_FILE", True),
        _env_bool("LOG_TO_CONSOLE", True),
    )


def start_run(reason: str = "scan") -> Path | None:
    """
    Close the current run's file and open a new one.

    Returns the new path, or None when file logging is disabled. Safe to
    call concurrently — two simultaneous scans will not interleave into a
    half-closed handler.
    """
    global _file_handler, _current_path, _run_id

    configure()

    if not _env_bool("LOG_TO_FILE", True):
        _run_id = datetime.now().strftime("%H%M%S")
        return None

    with _lock:
        root = logging.getLogger()

        if _file_handler is not None:
            get_logger("logging").info("run ended, closing %s", _current_path)
            root.removeHandler(_file_handler)
            _file_handler.close()
            _file_handler = None

        directory = _log_dir()
        directory.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        stem = now.strftime("%Y-%m-%d_%H-%M-%S")
        path = directory / f"{stem}.log"
        # Two runs inside the same second would otherwise share a file and
        # silently merge their traces.
        n = 2
        while path.exists():
            path = directory / f"{stem}_{n}.log"
            n += 1

        level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))
        handler.addFilter(_RunIdFilter())
        root.addHandler(handler)

        _file_handler = handler
        _current_path = path
        _run_id = now.strftime("%H%M%S")

    log = get_logger("logging")
    log.info("=" * 70)
    log.info("RUN START | reason=%s | file=%s", reason, path.name)
    log.info("=" * 70)
    return path


def current_log_file() -> Path | None:
    return _current_path


def get_logger(suffix: str = "") -> logging.Logger:
    """Namespaced child logger: get_logger('agent') -> trendradar.agent."""
    return logging.getLogger(f"{LOGGER_NAME}.{suffix}" if suffix else LOGGER_NAME)


# --- Compatibility aliases -------------------------------------------------
# MOD02 was written against get_log_file()/start_run_log(); MOD03 against
# current_log_file()/start_run(). Both names are kept so neither module's call
# sites had to change during the merge.

def get_log_file():
    """Alias of :func:`current_log_file` (MOD02 naming)."""

    return current_log_file()


def start_run_log(label: str = ""):
    """Alias of :func:`start_run` (MOD02 naming)."""

    return start_run(label or "run")
