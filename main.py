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

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

import penzugyi_naplo.config.config as config
from penzugyi_naplo.core.logging_utils import DebugFlags, Log
from penzugyi_naplo.db.transaction_database import TransactionDatabase
from penzugyi_naplo.ui.main_window import MainWindow

# VSCode "Run file" esetére: a projekt gyökerét tegyük sys.path-ra
PKG_DIR = Path(__file__).resolve().parent
ROOT_DIR = PKG_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# - Importok vége -


def _qt_message_handler(msg_type, context, message: str) -> None:
    """
    Qt üzenet-szűrő.

    A QSS-stílusaink mindenhol px-ben adják meg a font-size-t, pt-alapú
    alap-font nélkül. Emiatt Qt belső stíluslap-feldolgozása időnként egy
    "ismeretlen" pontméretet -1-gyel próbál beállítani (ez maga a Qt/PySide
    CSS-motorja, nem a mi kódunk hívja), és ez a jól ismert, ártalmatlan
    "QFont::setPointSize: Point size <= 0 (-1)" figyelmeztetést dobja
    minden oldalváltásnál. Ez nem hibát, csak konzolzajt jelent, ezért itt
    szűrjük ki, minden más Qt üzenetet változatlanul továbbengedve.
    """
    if "QFont::setPointSize" in message and "-1" in message:
        return
    if msg_type == QtMsgType.QtDebugMsg or msg_type == QtMsgType.QtInfoMsg:
        print(message)
    elif msg_type == QtMsgType.QtWarningMsg:
        print("WARNING:", message)
    elif msg_type == QtMsgType.QtCriticalMsg:
        print("CRITICAL:", message)
    elif msg_type == QtMsgType.QtFatalMsg:
        print("FATAL:", message)


def _resolve_app_font() -> QFont:
    """
    Az app globális fontjának kiválasztása.

    Végigmegy a config.APP_FONT_FALLBACKS listán, és az első ténylegesen
    telepített betűtípust használja (QFontDatabase.families() alapján
    ellenőrizve). Ha egyik sem elérhető - ami rendkívül valószínűtlen,
    mert a lista utolsó eleme (DejaVu Sans) szinte minden Linux
    disztribúción alapból ott van -, Qt saját alapértelmezett fontjára
    esik vissza.

    Ez váltja ki a korábbi, Windows-specifikus "Segoe UI" hardcode-olást,
    ami Linuxon egy kiszámíthatatlan rendszer-fallback-hez vezetett
    gépenként/frissítésenként eltérő megjelenéssel.
    """
    available = set(QFontDatabase.families())

    for family in config.APP_FONT_FALLBACKS:
        if family in available:
            return QFont(family, config.APP_FONT_SIZE_PT)

    # Egyik preferált font sem található - Qt alapértelmezett családja,
    # de a méretet így is egységesen tartjuk.
    return QFont(QApplication.font().family(), config.APP_FONT_SIZE_PT)


def main() -> int:
    """
    Application entry point. - Belépési pont az alkalmazáshoz:
    Ide kerül minden olyan inicializáció,
    ami a teljes alkalmazásra vonatkozik.
    """

    qInstallMessageHandler(_qt_message_handler)

    app = QApplication(sys.argv)

    # Érvényes, pt-alapú alap-font beállítása, mielőtt bármilyen QSS
    # (amely mindenhol px-ben ad meg font-size-t) alkalmazásra kerülne.
    # Enélkül Qt-nek nincs érvényes pontméret-fallback-je, ami hozzájárul
    # a "QFont::setPointSize: Point size <= 0 (-1)" figyelmeztetésekhez.
    #
    # A betűtípus forrása: config.APP_FONT_FALLBACKS (egyetlen hely,
    # ahol az app fontja meg van adva) - itt csak a tényleges, a gépen
    # elérhető font kiválasztása történik.
    app.setFont(_resolve_app_font())

    app_icon_path = Path(__file__).resolve().parent / "icons" / "app_icon_preview.png"
    app_icon = QIcon(str(app_icon_path))

    print("APP ICON PATH:", app_icon_path)
    print("APP ICON EXISTS:", app_icon_path.exists())
    print("APP ICON NULL:", app_icon.isNull())

    app.setWindowIcon(app_icon)

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
