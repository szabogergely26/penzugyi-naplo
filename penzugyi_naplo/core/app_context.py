# penzugyi_naplo/core/app_content.py
# ---------------------------------------

from __future__ import annotations

from dataclasses import dataclass

from penzugyi_naplo.db.transaction_database import TransactionDatabase


@dataclass
class AppState:
    active_year: int = 2026
    active_page_key: str = "home"


@dataclass
class AppContext:
    db: TransactionDatabase
    state: AppState
    dev_mode: bool = False
