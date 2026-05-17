from __future__ import annotations

import shutil
import sys
from pathlib import Path


def app_base_path() -> Path:
    """
    Az alkalmazás alapkönyvtára.

    Normál Python futtatáskor a projekt gyökerét adja vissza.
    PyInstaller EXE esetén a becsomagolt, ideiglenesen kibontott mappát.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]

    return Path(__file__).resolve().parents[2]


def demo_resource_dir() -> Path:
    """
    A becsomagolt demo adatbázisok könyvtára.
    """
    return app_base_path() / "penzugyi_naplo" / "resources" / "demo"


def copy_demo_database_if_missing(
    *,
    target_db_path: Path,
    demo_db_name: str,
) -> None:
    """
    Demo adatbázis bemásolása, ha a cél adatbázis még nem létezik.

    Meglévő adatbázist nem ír felül.
    """
    if target_db_path.exists():
        return

    source_db_path = demo_resource_dir() / demo_db_name

    if not source_db_path.exists():
        raise FileNotFoundError(f"Hiányzó demo adatbázis: {source_db_path}")

    target_db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db_path, target_db_path)


def ensure_demo_database_for_active_mode(
    *,
    dev_mode: bool,
    target_db_path: Path,
) -> None:
    """
    Első indításkor bemásolja az aktuális módhoz tartozó demo adatbázist,
    ha az aktív adatbázis még nem létezik.
    """
    demo_db_name = (
        "transactions_dev_demo.sqlite3"
        if dev_mode
        else "transactions_demo.sqlite3"
    )

    copy_demo_database_if_missing(
        target_db_path=target_db_path,
        demo_db_name=demo_db_name,
    )