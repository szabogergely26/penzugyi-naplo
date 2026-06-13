from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, QStandardPaths

from penzugyi_naplo.config.config import APP_NAME, ORG_NAME


LOG_MODE_BASIC = "basic"
LOG_MODE_DEBUG = "debug"
LOG_MODE_FULL = "full"

DEFAULT_LOG_MODE = LOG_MODE_BASIC
SETTINGS_KEY_LOG_MODE = "logging/mode"

VALID_LOG_MODES = {
    LOG_MODE_BASIC,
    LOG_MODE_DEBUG,
    LOG_MODE_FULL,
}

_LOG_FILE_PATH: Path | None = None


@dataclass(slots=True)
class DebugFlags:
    enabled: bool = False
    trace_page_stack: bool = False
    mode: str = DEFAULT_LOG_MODE


def normalize_log_mode(value: object) -> str:
    mode = str(value or DEFAULT_LOG_MODE)

    if mode not in VALID_LOG_MODES:
        return DEFAULT_LOG_MODE

    return mode


def read_log_mode_from_settings() -> str:
    settings = QSettings(ORG_NAME, APP_NAME)
    return normalize_log_mode(settings.value(SETTINGS_KEY_LOG_MODE, DEFAULT_LOG_MODE))


def is_debug_mode(mode: str) -> bool:
    return normalize_log_mode(mode) in (LOG_MODE_DEBUG, LOG_MODE_FULL)


def is_full_mode(mode: str) -> bool:
    return normalize_log_mode(mode) == LOG_MODE_FULL


def set_log_file_path(path: str | Path) -> None:
    global _LOG_FILE_PATH
    _LOG_FILE_PATH = Path(path)


def get_log_dir() -> Path:
    base_str = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )

    if base_str:
        base = Path(base_str)
    else:
        base = Path.home() / ".local" / "share" / ORG_NAME / APP_NAME

    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> Path:
    if _LOG_FILE_PATH is not None:
        return _LOG_FILE_PATH

    return get_log_dir() / "penzugyi_naplo.log"


class Log:
    def __init__(self, flags: DebugFlags | None = None) -> None:
        self.flags = flags or DebugFlags()
        self.log_path = get_log_file_path()
        self.set_mode(self.flags.mode)

    def set_mode(self, mode: str) -> None:
        self.flags.mode = normalize_log_mode(mode)
        self.flags.enabled = is_debug_mode(self.flags.mode)

    def get_mode(self) -> str:
        return normalize_log_mode(self.flags.mode)

    def is_debug_enabled(self) -> bool:
        return is_debug_mode(self.flags.mode)

    def is_full_enabled(self) -> bool:
        return is_full_mode(self.flags.mode)

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write(self, text: str) -> None:
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            print(f"[LOG WRITE ERROR] {e}")

    def _emit(self, level: str, *msg: Any, force: bool = False) -> None:
        if not force and not self.flags.enabled:
            return

        line = " ".join(str(m) for m in msg)
        formatted = f"[{self._timestamp()}] {level}: {line}"

        # Konzol / VSCode terminál / Konsole
        print(formatted)

        # Log fájl
        self._write(formatted)

    def session_start(self, title: str = "APP START") -> None:
        text = (
            f"\n{'=' * 90}\n"
            f"[{self._timestamp()}] {title}\n"
            f"log file: {self.log_path}\n"
            f"log mode: {self.get_mode()}\n"
            f"{'=' * 90}"
        )
        print(text)
        self._write(text)

    def d(self, *msg: Any) -> None:
        self._emit("DEBUG", *msg)

    def full(self, *msg: Any) -> None:
        if not self.is_full_enabled():
            return

        self._emit("FULL", *msg, force=True)

    def info(self, *msg: Any) -> None:
        self._emit("INFO", *msg, force=True)

    def warning(self, *msg: Any) -> None:
        self._emit("WARNING", *msg, force=True)

    def error(self, *msg: Any) -> None:
        self._emit("ERROR", *msg, force=True)

    def exception(self, *msg: Any) -> None:
        prefix = " ".join(str(m) for m in msg) if msg else "Unhandled exception"
        exc_text = traceback.format_exc()
        text = f"[{self._timestamp()}] ERROR: {prefix}\n{exc_text}"

        print(text)
        self._write(text)

    def trace(self, title: str = "TRACE", limit: int = 8) -> None:
        if not self.is_full_enabled():
            return

        stack = "".join(traceback.format_stack(limit=limit))
        text = f"\n[{self._timestamp()}] {title}\n{stack}"

        print(text)
        self._write(text)
