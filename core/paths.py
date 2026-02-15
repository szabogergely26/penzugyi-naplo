#   penzugyi_naplo/core/paths.py
# ----------------------------------


from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import QStandardPaths

from penzugyi_naplo.config import DEV_MODE

APP_NAME: Final[str] = "PenzugyiNaplo"


def is_dev_mode(argv: list[str] | None = None) -> bool:
    if argv and "--dev" in argv:
        return True
    if argv and "--prod" in argv:
        return False
    return bool(DEV_MODE)


def project_base_dir() -> Path:
    """
    A penzugyi_naplo csomag gyökere (ahol a main.py van).
    Dev-ben ezt használjuk, mert ott a QSS/forrásfák is itt vannak.
    """
    return Path(__file__).resolve().parents[1]


def app_data_dir(dev: bool) -> Path:
    """
    Írható adatkönyvtár (DB, későbbi exportok, backupok).
    Dev-ben: <project>/data
    Release-ben: OS szerinti AppDataLocation alá kerül.
    """
    if dev:
        return project_base_dir() / "data"

    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    return base / APP_NAME


def db_path(dev: bool) -> Path:
    return app_data_dir(dev) / "transactions.sqlite3"


def backups_dir(dev: bool) -> Path:
    return app_data_dir(dev) / "backups"


def exports_dir(dev: bool) -> Path:
    return app_data_dir(dev) / "exports"
