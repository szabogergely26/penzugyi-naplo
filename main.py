# pénzügyi_napló/main.py
# ----------------------------

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

import sys
from pathlib import Path

# VSCode "Run file" esetére: a projekt gyökerét tegyük sys.path-ra
PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication  # noqa: E402

from penzugyi_naplo.config import APP_NAME  # noqa: E402
from penzugyi_naplo.core.paths import db_path, is_dev_mode  # noqa: E402
from penzugyi_naplo.db.transaction_database import TransactionDatabase  # noqa: E402
from penzugyi_naplo.ui.main_window import MainWindow  # noqa: E402
from penzugyi_naplo.ui.stylesheet import NAV_QSS  # noqa: E402

# - Importok vége -


def load_styles(app) -> None:
    qss_path = Path(__file__).parent / "ui" / "style.qss"
    print("QSS path:", qss_path)
    print("QSS exists:", qss_path.exists())

    if qss_path.exists():
        qss = qss_path.read_text(encoding="utf-8")
        qss = qss + "\n" + NAV_QSS
        print("QSS length (+NAV):", len(qss))
        app.setStyleSheet(qss)
        print("App stylesheet length after set:", len(app.styleSheet()))


def main() -> int:
    """
    Application entry point. - Belépési pont az alkalmazáshoz:
    Ide kerül minden olyan inicializáció,
    ami a teljes alkalmazásra vonatkozik.
    """

    app = QApplication(sys.argv)

    # fontos: itt, az app létrehozása UTÁN
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    load_styles(app)

    dev = is_dev_mode(sys.argv)
    path = db_path(dev)
    path.parent.mkdir(parents=True, exist_ok=True)

    print("DEV mode:", dev)
    print("DB path:", path)
    print("DB exists:", path.exists())

    db = TransactionDatabase(str(path))
    win = MainWindow(db=db)
    if dev:
        win.setWindowTitle(win.windowTitle() + " — FEJLESZTŐI MÓD!!")
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
