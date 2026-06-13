# Fejlesztői -  pénzügyi_napló/main.py
# ------------------------------------

"""
Alkalmazás belépési pont
(penzugyi_naplo/main.py).

Felelősség:
    - QApplication létrehozása
    - globális stílus betöltése
    - TransactionDatabase inicializálása
    - MainWindow példányosítása és indítása

Ez a modul nem tartalmaz üzleti logikát,
csak az alkalmazás indulási és összekötési pontja.

Topology:
    main.py  ← this
        └─ MainWindow (ui/main_window.py)
             ├─ Pages (Home, Transactions, Statistics, Bills, Settings)
             └─ TransactionDatabase (db/transaction_database.py)

"""


# - Importok -

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

import penzugyi_naplo.config.config as config

from penzugyi_naplo.core.logging_utils import (
    DebugFlags,
    Log,
    read_log_mode_from_settings,
)

from penzugyi_naplo.db.transaction_database import TransactionDatabase
from penzugyi_naplo.ui.main_window import MainWindow


# VSCode "Run file" esetére: a projekt gyökerét tegyük sys.path-ra
PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))





# - Importok vége -


def main() -> int:
    """
    Application entry point. - Belépési pont az alkalmazáshoz:
    Ide kerül minden olyan inicializáció,
    ami a teljes alkalmazásra vonatkozik.
    """


    app = QApplication(sys.argv)

    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.ORG_NAME)

    # 1) DEV állapot a beállításból
    dev_mode = config.is_dev_mode()

    # 2) Naplózási mód QSettingsből
    log_mode = read_log_mode_from_settings()

    log = Log(
        DebugFlags(
            mode=log_mode,
            trace_page_stack=False,
        )
    )
    log.session_start("Pénzügyi Napló - app start")

    icon_name = "app_icon_dev.png" if dev_mode else "app_icon_main.png"
    app_icon_path = Path(__file__).resolve().parent / "icons" / icon_name

    if not app_icon_path.exists():
        fallback_icon_path = Path(__file__).resolve().parent / "icons" / "app_icon.png"
        log.warning("Elsődleges app ikon nem található:", app_icon_path)
        log.warning("Fallback app ikon próbálása:", fallback_icon_path)
        app_icon_path = fallback_icon_path

    app_icon = QIcon(str(app_icon_path))

    log.d("APP ICON PATH:", app_icon_path)
    log.d("APP ICON EXISTS:", app_icon_path.exists())
    log.d("APP ICON NULL:", app_icon.isNull())

    app.setWindowIcon(app_icon)


    # 2) aktív DB path
    path = config.active_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    log.info("DEV mode:", dev_mode)
    log.info("DB path:", path)
    log.info("DB exists:", path.exists())

    log.d("repo_root exists:", config.repo_root().exists())
    log.d("data exists:", (config.repo_root() / "data").exists())

    db = TransactionDatabase(str(path))
    win = MainWindow(db=db, dev_mode=dev_mode)
    win.setWindowIcon(app_icon)
    win.showMaximized()


    log.info("APP EXEC START")
    rc = app.exec()
    log.info("APP EXEC END", rc)

    logging.shutdown()

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
