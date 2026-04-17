from __future__ import annotations


import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths

_LOG_FILE_PATH: Path | None = None

@dataclass(slots=True)
class DebugFlags:
    enabled: bool = False
    trace_page_stack: bool = False


def get_log_dir() -> Path:
    base = Path(
        QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
    )
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> Path:
    return get_log_dir() / "penzugyi_naplo.log"


class Log:
    def __init__(self, flags: DebugFlags) -> None:
        self.flags = flags
        self.log_path = get_log_file_path()

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

        print(formatted)
        self._write(formatted)

    def session_start(self, title: str = "APP START") -> None:
        text = (
            f"\n{'=' * 90}\n"
            f"[{self._timestamp()}] {title}\n"
            f"log file: {self.log_path}\n"
            f"{'=' * 90}"
        )
        print(text)
        self._write(text)

    def d(self, *msg: Any) -> None:
        self._emit("DEBUG", *msg)

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
        if not self.flags.enabled:
            return

        stack = "".join(traceback.format_stack(limit=limit))
        text = f"\n[{self._timestamp()}] {title}\n{stack}"
        print(text)
        self._write(text)


    # Lekérdező:

    def set_log_file_path(path: str | Path) -> None:
        global _LOG_FILE_PATH
        _LOG_FILE_PATH = Path(path)


    def get_log_file_path() -> str:
        if _LOG_FILE_PATH is None:
            return ""
        return str(_LOG_FILE_PATH)