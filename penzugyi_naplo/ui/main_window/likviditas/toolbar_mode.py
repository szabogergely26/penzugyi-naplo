# penzugyi_naplo/ui/main_window/likviditas/toolbar_mode.py
"""
Likviditás nézet toolbar mód kezelése.

Felelősség:
    - Menüsor mód és szalag mód közötti váltás.
    - A választott toolbar mód mentése QSettings-be.
    - A MainWindow menüsor/ribbon láthatóságának frissítése.
    - A bal oldali évválasztó eltolásának újraszámoltatása.

Fontos:
    - A tényleges menü és ribbon felépítése nem itt történik.
    - Ez a modul csak a már létrehozott UI elemek láthatóságát kezeli.
"""






from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QSettings, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QToolBar

from penzugyi_naplo.config import APP_NAME, ORG_NAME


def set_likviditas_toolbar_mode(window, mode: str) -> None:
    """Toolbar mód beállítása: klasszikus menüsor vagy szalag."""
    s = QSettings(ORG_NAME, APP_NAME)
    s.setValue("ui/toolbar_mode", mode)

    is_ribbon = mode == "ribbon"

    # A menüsor mindig létezhet, de szalag módban elrejtjük.
    window.menuBar().setVisible(not is_ribbon)

    if hasattr(window, "ribbon") and window.ribbon:
        window.ribbon.setVisible(is_ribbon)

    if hasattr(window, "likviditas_standard_toolbar"):
        window.likviditas_standard_toolbar.setVisible(not is_ribbon)

    window.act_toolbar_menubar.setChecked(not is_ribbon)
    window.act_toolbar_ribbon.setChecked(is_ribbon)

    # A ribbon/menüsor magassága csak a layout frissülése után biztos,
    # ezért egy Qt event loop körrel később igazítjuk az évválasztó sávot.
    QTimer.singleShot(0, window._sync_left_year_offset)


def load_likviditas_toolbar_mode(window) -> None:
    """Toolbar mód betöltése QSettings-ből."""
    s = QSettings(ORG_NAME, APP_NAME)
    mode = str(s.value("ui/toolbar_mode", "menubar"))

    if mode not in ("menubar", "ribbon"):
        mode = "menubar"

    set_likviditas_toolbar_mode(window, mode)


def create_likviditas_standard_toolbar(window) -> QToolBar:
    """
    Menüsoros / standard nézet alatti egyszerű eszköztár létrehozása.

    Ide kerülnek azok a gyakori műveletek, amelyekhez nem akarunk
    külön Fájl menübe bemenni.
    """
    toolbar = QToolBar("Likviditás eszköztár", window)
    toolbar.setObjectName("likviditasStandardToolbar")
    toolbar.setMovable(False)
    toolbar.setFloatable(False)

   # Ikon felül, szöveg alatta.
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

    # Ikonméret.
    toolbar.setIconSize(QSize(30, 30))

    # A toolbar minimum / maximum magassága.
    toolbar.setMinimumHeight(90)
    toolbar.setMaximumHeight(90)

    # A gombok saját mérete/paddingje is számít, nem csak a toolbar magassága.
    toolbar.setStyleSheet("""
    QToolBar#likviditasStandardToolbar {
        spacing: 4px;
        padding: 4px 8px;
    }

    QToolBar#likviditasStandardToolbar QToolButton {
        min-width: 92px;
        min-height: 58px;
        padding: 4px 6px;
    }
    """)

    new_transaction_action = QAction(
        QIcon.fromTheme("document-new"),
        "Tranzakció Varázsló",
        window,
    )
    new_transaction_action.setObjectName("actionTransactionWizardToolbar")
    new_transaction_action.triggered.connect(window.on_new_transaction)

    toolbar.addAction(new_transaction_action)

    return toolbar