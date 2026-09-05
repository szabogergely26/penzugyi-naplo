# penzugyi_naplo/config/config.py
# -----------------------------------

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


# -----------------------------
# Globális alkalmazás-font
# -----------------------------
#
# Ez az EGYETLEN hely, ahol az app betűtípusát megadjuk.
# A main.py ezt olvassa be és app.setFont(...)-tal állítja be, mielőtt
# bármilyen QSS betöltődne - így minden oldal, dialógus és widget
# ugyanazt a fontot kapja, függetlenül attól, hogy az adott gépen
# éppen mi a rendszer alapértelmezett betűtípusa.
#
# Fontos: "Segoe UI" Windows-specifikus font, Linuxon nem létezik -
# ha ez volt beállítva, Qt egy előre nem kiszámítható rendszer-fallback-re
# váltott, ami gépenként/frissítésenként eltérő megjelenést okozott.
#
# APP_FONT_FALLBACKS: sorrendben kipróbált betűtípus-lista.
# Az első elérhető (a gépen ténylegesen telepített) fontot használja Qt,
# az utolsó elem (DejaVu Sans) szinte minden Linux disztribúción
# alapból telepítve van, ez a végső biztonsági háló.
APP_FONT_FALLBACKS: tuple[str, ...] = (
    "Noto Sans",
    "Ubuntu",
    "Cantarell",
    "DejaVu Sans",
)

APP_FONT_SIZE_PT: int = 9


def app_font_family() -> str:
    """
    Az app-ban használt betűtípus neve.

    Jelenleg az APP_FONT_FALLBACKS első elemét adja vissza - a tényleges
    "van-e telepítve" ellenőrzést és a lista bejárását a main.py végzi
    QFontDatabase segítségével, mert az Qt-inicializálást igényel.
    Itt csak a preferencia-sorrend forrása van megadva.
    """
    return APP_FONT_FALLBACKS[0]


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
    """
    Projektgyökér keresése marker fájl/mappa alapján.

    Fejlesztői környezetben a projektgyökér az a mappa,
    ahol például a .git vagy a pyproject.toml található.
    """
    current = Path(__file__).resolve()

    for parent in current.parents:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent

    # Biztonsági fallback a jelenlegi csomagszerkezethez.
    return Path(__file__).resolve().parents[2]


def is_dev_project() -> bool:
    """
    Fejlesztői projekt felismerése.
    Ezt később lehet finomítani (pl. marker fájl).
    """
    return (repo_root() / "data").exists()


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


# ---------------------------------
# Statusbar: kézi mentés (backup) / betöltés (restore) időbélyegek
# ---------------------------------
#
# Ezek a "Utolsó mentés" / "Utoljára betöltve" statusbar-feliratok
# perzisztenciáját szolgálják - hogy app-újraindítás után is megmaradjon
# a legutóbbi kézi biztonsági mentés / visszatöltés időpontja.
#
# Tudatosan itt van, nem a transaction_database.py-ban: a DB réteg
# szándékosan Qt-mentes marad (nincs benne QSettings import), ezért a
# lemezre írást/olvasást a UI réteg (main_window.py) végzi, ezeken a
# helpereken keresztül.
#
# DB-fájlonként külön kulcs alatt tárolunk (a db_path fájlnevéből képzett
# kulcs-résszel), hogy pl. a dev és a stabil adatbázis, vagy egy egyéni
# restore-olt fájl ne írja felül egymás időbélyegét.

SETTINGS_KEY_LAST_BACKUP_PREFIX: str = "db_status/last_backup_ts"
SETTINGS_KEY_LAST_RESTORE_PREFIX: str = "db_status/last_restore_ts"


def _db_status_key(prefix: str, db_path: Path | str) -> str:
    """
    QSettings-kulcs összeállítása egy adott DB-fájlhoz.

    A db_path fájlnevét (kiterjesztés nélkül) használjuk elkülönítő
    részként, pl. "transactions" vagy "transactions_dev" - ez elég ahhoz,
    hogy a stabil és a dev adatbázis időbélyege ne keveredjen össze,
    anélkül hogy a teljes (gépfüggő) abszolút útvonalat kulcsként kellene
    tárolni.
    """
    stem = Path(db_path).stem
    return f"{prefix}/{stem}"


def get_last_backup_ts(db_path: Path | str) -> str | None:
    """
    A megadott DB-fájlhoz tartozó, legutóbb mentett kézi biztonsági
    mentés (backup) időbélyegének beolvasása. None, ha még nincs elmentve.
    """
    value = settings().value(_db_status_key(SETTINGS_KEY_LAST_BACKUP_PREFIX, db_path))
    return str(value) if value else None


def set_last_backup_ts(db_path: Path | str, ts: str) -> None:
    """A megadott DB-fájlhoz tartozó "utolsó mentés" időbélyeg elmentése."""
    settings().setValue(_db_status_key(SETTINGS_KEY_LAST_BACKUP_PREFIX, db_path), ts)


def get_last_restore_ts(db_path: Path | str) -> str | None:
    """
    A megadott DB-fájlhoz tartozó, legutóbb mentett kézi visszatöltés
    (restore) időbélyegének beolvasása. None, ha még nincs elmentve.
    """
    value = settings().value(_db_status_key(SETTINGS_KEY_LAST_RESTORE_PREFIX, db_path))
    return str(value) if value else None


def set_last_restore_ts(db_path: Path | str, ts: str) -> None:
    """A megadott DB-fájlhoz tartozó "utoljára betöltve" időbélyeg elmentése."""
    settings().setValue(_db_status_key(SETTINGS_KEY_LAST_RESTORE_PREFIX, db_path), ts)


def clear_backup_restore_status(db_path: Path | str) -> None:
    """
    A megadott DB-fájlhoz tartozó "utolsó mentés" és "utoljára betöltve"
    időbélyegek törlése a perzisztens tárolóból.

    Ezt olyankor kell hívni, amikor a DB-fájl tartalma úgy változik meg,
    hogy a korábbi mentés/betöltés előzmény már nem értelmezhető rá -
    jelenleg ez az adatbázis törlése (lásd MainWindow.on_reset_database).
    Enélkül egy korábbi, lemezen maradt időbélyeg tévesen "visszaszivárogna"
    a következő induláskor, holott az új, üres DB-nek nincs ilyen előzménye.
    """
    s = settings()
    s.remove(_db_status_key(SETTINGS_KEY_LAST_BACKUP_PREFIX, db_path))
    s.remove(_db_status_key(SETTINGS_KEY_LAST_RESTORE_PREFIX, db_path))
