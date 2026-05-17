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

from PySide6.QtWidgets import QApplication

import penzugyi_naplo.config as config

# Demo DB:
from penzugyi_naplo.core.demo_database import ensure_demo_database_for_active_mode
from penzugyi_naplo.core.logging_utils import DebugFlags, Log
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

    log = Log(
    DebugFlags(
        enabled=dev_mode,
        trace_page_stack=False,
        )
    )
    log.session_start("Pénzügyi Napló - app start")



    # 2) aktív DB path
    path = config.active_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    ensure_demo_database_for_active_mode(
        dev_mode=dev_mode,
        target_db_path=path,
    )


    log.info("DEV mode:", dev_mode)
    log.info("DB path:", path)
    log.info("DB exists:", path.exists())

    log.d("repo_root exists:", config.repo_root().exists())
    log.d("data exists:", (config.repo_root() / "data").exists())

    db = TransactionDatabase(str(path))
    win = MainWindow(db=db, dev_mode=dev_mode)
    win.show()

    log.info("APP EXEC START")
    rc = app.exec()
    log.info("APP EXEC END", rc)

    logging.shutdown()

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
