# penzugyi_naplo/ui/main_window/aranyszamla/module_page.py
# ---------------------------------------------------------

"""
Aranyszámla modul konténeroldal.

Feladata:
- saját belső nav_bar biztosítása
- Kezdő / Kereskedés oldalak közötti váltás
- az Aranyszámla modul egyben tartása a MainWindow felé
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.ui.main_window.aranyszamla.home_page import AranyszamlaHomePage
from penzugyi_naplo.ui.main_window.aranyszamla.trading_page import (
    AranyszamlaTradingPage,
)


class AranyszamlaModulePage(QWidget):
    """Az Aranyszámla modul saját belső navigációval."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("aranyszamlaModulePage")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 24)
        main_layout.setSpacing(16)

        self.nav_bar = QFrame()
        self.nav_bar.setObjectName("aranyszamlaNavBar")

        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

        self.btn_home = QPushButton("Kezdő")
        self.btn_home.setObjectName("aranyszamlaNavButton")
        self.btn_home.setCheckable(True)

        self.btn_trading = QPushButton("Kereskedés")
        self.btn_trading.setObjectName("aranyszamlaNavButton")
        self.btn_trading.setCheckable(True)

        nav_layout.addWidget(self.btn_home)
        nav_layout.addWidget(self.btn_trading)
        nav_layout.addStretch(1)

        self.stack = QStackedWidget()
        self.stack.setObjectName("aranyszamlaInnerStack")

        self.home_page = AranyszamlaHomePage(self.stack)
        self.trading_page = AranyszamlaTradingPage(self.stack)

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.trading_page)

        main_layout.addWidget(self.nav_bar)
        main_layout.addWidget(self.stack, 1)

        self.btn_home.clicked.connect(self.show_home)
        self.btn_trading.clicked.connect(self.show_trading)

        self.show_home()

    def show_home(self) -> None:
        """Átvált az Aranyszámla kezdőoldalára."""

        self.stack.setCurrentWidget(self.home_page)
        self.btn_home.setChecked(True)
        self.btn_trading.setChecked(False)

    def show_trading(self) -> None:
        """Átvált az Aranyszámla kereskedés oldalára."""

        self.stack.setCurrentWidget(self.trading_page)
        self.btn_home.setChecked(False)
        self.btn_trading.setChecked(True)