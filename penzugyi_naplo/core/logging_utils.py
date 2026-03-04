# penzugyi_naplo/core/logging_utils.py
# ---------------------------------------

# --- Importok ----

from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths


@dataclass(slots=True)
class DebugFlags:
    enabled: bool = False
    trace_page_stack: bool = False


def get_log_file_path() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    log_dir = base / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "penzugyi_naplo.log"


class Log:
    def __init__(self, flags: DebugFlags) -> None:
        self.flags = flags
        self.log_path = get_log_file_path()

    def _write(self, text: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    def d(self, *msg: Any) -> None:
        if not self.flags.enabled:
            return

        line = " ".join(str(m) for m in msg)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] {line}"

        print(formatted)
        self._write(formatted)

    def trace(self, title: str = "TRACE", limit: int = 8) -> None:
        if not self.flags.enabled:
            return

        stack = "".join(traceback.format_stack(limit=limit))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._write(f"\n[{timestamp}] {title}\n{stack}")
        print(f"{title}:\n{stack}")
