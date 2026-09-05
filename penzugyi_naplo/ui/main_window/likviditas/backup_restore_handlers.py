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

import contextlib
import shutil
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from penzugyi_naplo.db.transaction_database import TransactionDatabase


def _reopen_db(
    window,
    db_path: Path,
    *,
    last_backup_ts: str | None = None,
    last_restore_ts: str | None = None,
) -> None:
    """
    Közös segédfüggvény: DB újranyitása egy adott fájlon, és a MainWindow
    ehhez tartozó állapotainak frissítése.

    Ide tartozik:
        - window.db / window.ctx.db lecserélése az új példányra
        - a statusbar jelzéseinek újra-feliratkoztatása, mert egy új
          TransactionDatabase példánynak üres a feliratkozó-listája
          (lásd TransactionDatabase.on_save / on_backup / on_restore)
        - a last_backup_ts / last_restore_ts átvitele az új példányra,
          mert enélkül egy friss TransactionDatabase-nél None-ra ugrana
          vissza a "Utolsó mentés" / "Utoljára betöltve" statusbar-jelzés
          minden egyes DB-újranyitáskor (pl. backup után)
        - oldalak újrakötése az új DB-re

    Ezt a lépéssort eddig backup/restore műveletenként külön-külön
    kellett volna megismételni; így egy helyen van, egy új restore-szerű
    művelet sem felejtheti ki a statusbar bekötését.
    """
    old_db = getattr(window, "db", None)

    # Ha a hívó nem adott át explicit időbélyeget, örököljük a régi
    # DB-példány állapotát, hogy DB-újranyitáskor (pl. sima _reopen_db
    # hívás hiba után) ne vesszen el a meglévő "Utolsó mentés" /
    # "Utoljára betöltve" infó.
    if last_backup_ts is None and old_db is not None:
        last_backup_ts = getattr(old_db, "last_backup_ts", None)
    if last_restore_ts is None and old_db is not None:
        last_restore_ts = getattr(old_db, "last_restore_ts", None)

    window.db = TransactionDatabase(str(db_path))
    window.ctx.db = window.db

    window.db.last_backup_ts = last_backup_ts
    window.db.last_restore_ts = last_restore_ts

    if hasattr(window, "_on_db_saved"):
        window.db.on_save(window._on_db_saved)
    if hasattr(window, "_on_db_backup"):
        window.db.on_backup(window._on_db_backup)
    if hasattr(window, "_on_db_restore"):
        window.db.on_restore(window._on_db_restore)

    window._rebind_db_to_pages()


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

    backup_ts: str | None = None

    try:
        if hasattr(window.db, "close"):
            window.db.close()

        shutil.copy2(str(db_path), target)

        # Explicit jelzés: a statusbar "Utolsó mentés" feliratát KIZÁRÓLAG
        # ez a hívás frissíti - nem a sima commit()-ok. A régi window.db
        # példányon hívjuk meg, mert ahhoz vannak kötve a statusbar
        # callback-jei; az időbélyeget lentebb átvisszük az új példányra is.
        backup_ts = window.db.mark_backup_done()

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
        _reopen_db(window, db_path, last_backup_ts=backup_ts)


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
        # A régi last_backup_ts-t átvisszük, mert ez a mező a kézi mentés
        # állapotát tükrözi, amit egy restore önmagában nem érint.
        old_backup_ts = getattr(window.db, "last_backup_ts", None)

        if hasattr(window.db, "close"):
            window.db.close()

        if db_path.exists():
            safety = db_path.with_suffix(db_path.suffix + ".pre_restore.bak")
            shutil.copy2(str(db_path), str(safety))

        shutil.copy2(str(source_path), str(db_path))

        window.db = TransactionDatabase(str(db_path))
        window.ctx.db = window.db
        window.db.last_backup_ts = old_backup_ts

        if hasattr(window, "_on_db_saved"):
            window.db.on_save(window._on_db_saved)
        if hasattr(window, "_on_db_backup"):
            window.db.on_backup(window._on_db_backup)
        if hasattr(window, "_on_db_restore"):
            window.db.on_restore(window._on_db_restore)

        # Explicit jelzés: a statusbar "Utoljára betöltve" feliratát
        # KIZÁRÓLAG ez a hívás frissíti - nem az app-indításkori DB-megnyitás
        # és nem a sima adatbetöltés/reload_all_pages().
        window.db.mark_restore_done()

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

        with contextlib.suppress(Exception):
            _reopen_db(window, db_path)
