# penzugyi_naplo/ui/main_window/likviditas/actions.py
# -----------------------------------------------------

"""
Likviditás nézethez tartozó QAction objektumok létrehozása.

Felelősség:
    - A MainWindow által használt QAction objektumok létrehozása.
    - Az actionök összekötése a MainWindow callback metódusaival.
    - A toolbar mód action csoportjának beállítása.

Fontos:
    - A callback metódusok továbbra is a MainWindow-ban maradnak.
    - Ez a modul csak az action objektumokat hozza létre és köti be.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QActionGroup


def create_likviditas_actions(window) -> None:
    """Likviditás nézethez tartozó actionök létrehozása."""

    # Beállítások megnyitása.
    window.act_settings = QAction("Beállítások", window)
    window.act_settings.triggered.connect(window.show_settings_dialog)


    window.act_exit = QAction("Kilépés", window)
    window.act_exit.triggered.connect(window.close)

    window.act_import = QAction("Import", window)
    window.act_import.triggered.connect(window.on_import)

    window.act_export = QAction("Export", window)
    window.act_export.triggered.connect(window.on_export)

    window.act_backup_db = QAction("Mentés (backup)…", window)
    window.act_backup_db.triggered.connect(window.on_backup_database)

    window.act_restore_db = QAction("Betöltés (restore)…", window)
    window.act_restore_db.triggered.connect(window.on_restore_database)

    window.act_new_tx = QAction("Új tranzakció", window)
    window.act_new_tx.triggered.connect(window.on_new_transaction)

    window.act_toolbar_menubar = QAction("Menüsor mód", window, checkable=True)
    window.act_toolbar_ribbon = QAction("Szalag mód", window, checkable=True)

    window.act_toolbar_menubar.triggered.connect(
        lambda: window.set_toolbar_mode("menubar")
    )
    window.act_toolbar_ribbon.triggered.connect(
        lambda: window.set_toolbar_mode("ribbon")
    )

    window.toolbar_mode_group = QActionGroup(window)
    window.toolbar_mode_group.setExclusive(True)

    window.act_toolbar_menubar.setActionGroup(window.toolbar_mode_group)
    window.act_toolbar_ribbon.setActionGroup(window.toolbar_mode_group)

    window.act_reset_db = QAction("Adatbázis törlése…", window)
    window.act_reset_db.triggered.connect(window.on_reset_database)

    window.act_about = QAction("Névjegy", window)
    window.act_about.triggered.connect(window._show_about)

    window.act_version_info = QAction("Verzió infók", window)
    window.act_version_info.triggered.connect(window._show_version_info)

    window.act_log_viewer = QAction("Alkalmazásnapló", window)
    window.act_log_viewer.triggered.connect(window.show_log_viewer)

    window.act_version_history = QAction("Verziótörténet", window)
    window.act_version_history.triggered.connect(window._show_version_history)