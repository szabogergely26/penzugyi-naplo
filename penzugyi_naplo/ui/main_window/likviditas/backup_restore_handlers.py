"""
penzugyi_naplo/ui/main_window/likviditas/backup_restore_handlers.py

Likviditás nézethez tartozó adatbázis mentés/betöltés műveletek.

Felelősség:
- adatbázis biztonsági mentése
- adatbázis visszatöltése backup fájlból
- DB újranyitása restore után
- oldalak újrakötése és frissítése

Fontos:
- ez UI-szintű handler
- a MainWindow csak meghívja ezeket a műveleteket
- az adatbázis tényleges működését továbbra is a TransactionDatabase kezeli
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from penzugyi_naplo.db.transaction_database import TransactionDatabase


def handle_backup_database(window) -> None:
    """Adatbázis biztonsági mentése fájlba."""

    db_path = Path(window.db.db_name)

    if not db_path.exists():
        QMessageBox.warning(
            window,
            "Mentés",
            f"A DB fájl nem található:\n{db_path}",
        )
        return

    suggested = f"{db_path.stem}_backup.sqlite3"

    target, _ = QFileDialog.getSaveFileName(
        window,
        "Adatbázis mentése (backup)",
        str(db_path.with_name(suggested)),
        "SQLite DB (*.sqlite3 *.db);;Minden fájl (*)",
    )

    if not target:
        return

    try:
        if hasattr(window.db, "close"):
            window.db.close()

        shutil.copy2(str(db_path), target)

        QMessageBox.information(
            window,
            "Mentés kész",
            f"Backup elkészült:\n{target}",
        )

    except Exception as exc:
        QMessageBox.critical(
            window,
            "Mentés hiba",
            f"Nem sikerült menteni:\n{exc}",
        )

    finally:
        window.db = TransactionDatabase(str(db_path))
        window.ctx.db = window.db
        window._rebind_db_to_pages()


def handle_restore_database(window) -> None:
    """Adatbázis visszatöltése backup fájlból."""

    db_path = Path(window.db.db_name)

    source, _ = QFileDialog.getOpenFileName(
        window,
        "Adatbázis betöltése (restore)",
        str(db_path.parent),
        "SQLite DB (*.sqlite3 *.db);;Minden fájl (*)",
    )

    if not source:
        return

    ret = QMessageBox.warning(
        window,
        "Betöltés (restore)",
        "Biztosan betöltöd ezt a backupot?\n\n"
        "A jelenlegi adatbázis felül lesz írva.\n"
        "A művelet nem visszavonható.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )

    if ret != QMessageBox.StandardButton.Yes:
        return

    source_path = Path(source)

    if not source_path.exists():
        QMessageBox.warning(
            window,
            "Betöltés",
            f"A kiválasztott fájl nem létezik:\n{source}",
        )
        return

    try:
        if hasattr(window.db, "close"):
            window.db.close()

        if db_path.exists():
            safety = db_path.with_suffix(db_path.suffix + ".pre_restore.bak")
            shutil.copy2(str(db_path), str(safety))

        shutil.copy2(str(source_path), str(db_path))

        window.db = TransactionDatabase(str(db_path))
        window.ctx.db = window.db

        window._rebind_db_to_pages()
        window.reload_all_pages()

        QMessageBox.information(
            window,
            "Betöltés kész",
            "A backup betöltve, az oldalak frissítve.",
        )

    except Exception as exc:
        QMessageBox.critical(
            window,
            "Betöltés hiba",
            f"Nem sikerült betölteni:\n{exc}",
        )

        try:
            window.db = TransactionDatabase(str(db_path))
            window.ctx.db = window.db
            window._rebind_db_to_pages()
        except Exception:
            pass