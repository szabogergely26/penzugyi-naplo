# penzugyi_naplo/config.py
# -----------------------------


from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

APP_NAME: str = "PenzugyiNaplo"
ORG_NAME: str = "PenzugyiNaplo"

# QSettings kulcs
SETTINGS_KEY_DEV_MODE: str = "app/dev_mode"

# DB fájlnevek
DB_FILENAME_PROD: str = "transactions.sqlite3"
DB_FILENAME_DEV: str = "transactions_dev.sqlite3"


def settings() -> QSettings:
    return QSettings(ORG_NAME, APP_NAME)


def is_dev_mode() -> bool:
    # default: False (normál mód)
    return settings().value(SETTINGS_KEY_DEV_MODE, False, type=bool)


def set_dev_mode(enabled: bool) -> None:
    settings().setValue(SETTINGS_KEY_DEV_MODE, bool(enabled))


def prod_db_path() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    base.mkdir(parents=True, exist_ok=True)
    return base / DB_FILENAME_PROD


def dev_db_path() -> Path:
    # repo/data/transactions_dev.sqlite3
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / DB_FILENAME_DEV


def active_db_path() -> Path:
    return dev_db_path() if is_dev_mode() else prod_db_path()
