# penzugyi_naplo/config.py
# -----------------------------

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

APP_NAME: str = "PenzugyiNaplo"
ORG_NAME: str = "PenzugyiNaplo"

SETTINGS_KEY_DEV_MODE: str = "app/dev_mode"

DB_FILENAME_PROD: str = "transactions.sqlite3"
DB_FILENAME_DEV: str = "transactions_dev.sqlite3"


# -----------------------------
# Settings
# -----------------------------

def settings() -> QSettings:
    return QSettings(ORG_NAME, APP_NAME)


def is_dev_mode() -> bool:
    return settings().value(SETTINGS_KEY_DEV_MODE, False, type=bool)


def set_dev_mode(enabled: bool) -> None:
    settings().setValue(SETTINGS_KEY_DEV_MODE, bool(enabled))


# -----------------------------
# Project detection
# -----------------------------

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_dev_project() -> bool:
    """
    Fejlesztői projekt felismerése.
    Ezt később lehet finomítani (pl. marker fájl).
    """
    return (repo_root () / "data").exists()


# -----------------------------
# Data directories
# -----------------------------

def stable_data_dir() -> Path:
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    base.mkdir(parents=True, exist_ok=True)
    return base


def dev_project_data_dir() -> Path:
    data_dir = repo_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def active_data_dir() -> Path:
    return dev_project_data_dir() if is_dev_project() else stable_data_dir()


# -----------------------------
# DB
# -----------------------------

def active_db_filename() -> str:
    return DB_FILENAME_DEV if is_dev_mode() else DB_FILENAME_PROD


def active_db_path() -> Path:
    return active_data_dir() / active_db_filename()

# ------------------------------
# DB files
# -----------------------------

def prod_db_path() -> Path:
    return active_data_dir() / DB_FILENAME_PROD


def dev_db_path() -> Path:
    return active_data_dir() / DB_FILENAME_DEV