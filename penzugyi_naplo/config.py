# penzugyi_naplo/config.py
# -----------------------------

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

APP_NAME: str = "PenzugyiNaplo"
ORG_NAME: str = "PenzugyiNaplo"

SETTINGS_KEY_DEV_MODE: str = "app/dev_mode"



SETTINGS_KEY_STYLE_MODE: str = "ui/style_mode"

STYLE_CLASSIC: str = "classic"
STYLE_MODERN: str = "modern"
STYLE_MODERN_HOME: str = "modern_home"

DEFAULT_STYLE_MODE: str = STYLE_CLASSIC

AVAILABLE_STYLE_MODES: tuple[str, ...] = (
    STYLE_CLASSIC,
    STYLE_MODERN,
    STYLE_MODERN_HOME,
)


DB_FILENAME_PROD: str = "transactions.sqlite3"
DB_FILENAME_DEV: str = "transactions_dev.sqlite3"


# A keresés alapértelmezett hatóköre.
# Ezt a Beállítások ablak menti, a keresősáv pedig induláskor visszaolvassa.
SETTINGS_KEY_SEARCH_SCOPE = "search/default_scope"

# Csak az aktív év tranzakcióiban keresünk.
SEARCH_SCOPE_ACTIVE_YEAR = "active_year"

# Az összes év tranzakcióiban keresünk.
SEARCH_SCOPE_ALL_YEARS = "all_years"

# Alapértelmezett keresési hatókör, ha még nincs beállítás mentve.
DEFAULT_SEARCH_SCOPE = SEARCH_SCOPE_ACTIVE_YEAR












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



# ---------------------------------
# Search
# ---------------------------------


def get_default_search_scope() -> str:
    """
    A keresés alapértelmezett hatókörének betöltése.

    Visszatérés:
        - "active_year": csak az aktív évben keres
        - "all_years": minden évben keres

    Ha még nincs elmentett érték, akkor az aktív év az alapértelmezett.
    """
    settings = QSettings(ORG_NAME, APP_NAME)

    value = settings.value(
        SETTINGS_KEY_SEARCH_SCOPE,
        DEFAULT_SEARCH_SCOPE,
        type=str,
    )

    if value not in {
        SEARCH_SCOPE_ACTIVE_YEAR,
        SEARCH_SCOPE_ALL_YEARS,
    }:
        return DEFAULT_SEARCH_SCOPE

    return value


def set_default_search_scope(scope: str) -> None:
    """
    A keresés alapértelmezett hatókörének mentése.

    Ezt a Beállítások ablak használja.
    """
    if scope not in {
        SEARCH_SCOPE_ACTIVE_YEAR,
        SEARCH_SCOPE_ALL_YEARS,
    }:
        scope = DEFAULT_SEARCH_SCOPE

    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(SETTINGS_KEY_SEARCH_SCOPE, scope)