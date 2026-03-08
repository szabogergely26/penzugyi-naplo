#   penzugyi_naplo/core/paths.py
# ----------------------------------


from __future__ import annotations

from pathlib import Path
from typing import Final

from PySide6.QtCore import QStandardPaths

from penzugyi_naplo.config import is_dev_mode

APP_NAME: Final[str] = "PenzugyiNaplo"


def resolve_dev_mode(argv: list[str] | None = None) -> bool:
    if argv and "--dev" in argv:
        return True
    if argv and "--prod" in argv:
        return False
    return bool(is_dev_mode)


def project_base_dir() -> Path:
    """
    A projekt gyökérkönyvtára, ahol a main.py van.
    Dev-ben ezt használjuk, mert ott a QSS/forrásfák is itt vannak.
    """
    return Path(__file__).resolve().parents[2]


def app_data_dir(dev: bool) -> Path:
    """
    Írható adatkönyvtár (DB, későbbi exportok, backupok).
    Dev-ben: <project>/data
    Release-ben: OS szerinti AppDataLocation alá kerül.
    """
    if dev:
        path = project_base_dir() / "data"
    else:
        path = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))

    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path(dev: bool) -> Path:
    return app_data_dir(dev) / "transactions.sqlite3"


def backups_dir(dev: bool) -> Path:
    path = app_data_dir(dev) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def exports_dir(dev: bool) -> Path:
    path = app_data_dir(dev) / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path
