"""
Structured logger with file rotation.

- Log file: <config_dir>/gimp-ai-mentor.log
- Rotation: 5 MB max, keep 3 backups (.log.1, .log.2, .log.3)
- Levels: DEBUG, INFO, WARNING, ERROR
"""

import os
import sys
import threading
import time
import traceback


LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}

MAX_BYTES = 5 * 1024 * 1024
MAX_BACKUPS = 3


class Logger:
    """Thread-safe rotating file logger."""

    def __init__(self, log_dir, level="INFO"):
        self._lock = threading.Lock()
        self._level = LEVELS.get(level.upper(), 20)
        self._log_path = os.path.join(log_dir, "gimp-ai-mentor.log")
        os.makedirs(log_dir, exist_ok=True)

    @property
    def level(self):
        return self._level

    def set_level(self, level_name):
        self._level = LEVELS.get(level_name.upper(), 20)

    def debug(self, module, message):
        self._write("DEBUG", module, message)

    def info(self, module, message):
        self._write("INFO", module, message)

    def warning(self, module, message):
        self._write("WARNING", module, message)

    def error(self, module, message):
        self._write("ERROR", module, message)
        # Also print errors to stderr for GIMP console visibility
        print(f"[AI-Mentor ERROR] [{module}] {message}", file=sys.stderr)

    def _write(self, level, module, message):
        if LEVELS[level] < self._level:
            return
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts}] [{level}] [{module}] {message}\n"
        with self._lock:
            try:
                self._rotate_if_needed()
                with open(self._log_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass  # never crash because of logging failure

    def _rotate_if_needed(self):
        try:
            if os.path.exists(self._log_path) and os.path.getsize(self._log_path) >= MAX_BYTES:
                for i in range(MAX_BACKUPS - 1, 0, -1):
                    src = f"{self._log_path}.{i}"
                    dst = f"{self._log_path}.{i + 1}"
                    if os.path.exists(src):
                        if os.path.exists(dst):
                            os.remove(dst)
                        os.rename(src, dst)
                bak = f"{self._log_path}.1"
                if os.path.exists(bak):
                    os.remove(bak)
                os.rename(self._log_path, bak)
        except Exception:
            pass

    def get_log_path(self):
        return self._log_path

    def get_recent_entries(self, count=50):
        """Return the last `count` lines from the log file."""
        try:
            with open(self._log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return "".join(lines[-count:])
        except Exception:
            return ""


# Module-level instance — initialized by dialog
_logger = None


def init(log_dir, level="INFO"):
    global _logger
    _logger = Logger(log_dir, level)
    return _logger


def get():
    return _logger


def debug(module, message):
    if _logger:
        _logger.debug(module, message)


def info(module, message):
    if _logger:
        _logger.info(module, message)


def warning(module, message):
    if _logger:
        _logger.warning(module, message)


def error(module, message):
    if _logger:
        _logger.error(module, message)
