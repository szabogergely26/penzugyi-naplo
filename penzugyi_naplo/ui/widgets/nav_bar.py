# ui/widgets/nav_bar.py
# -------------------------

"""
Felső navigációs sáv (NavBar)
(ui/widgets/nav_bar.py).

Felelősség:
    - oldalgombok megjelenítése (home / transactions / statistics / settings)
    - navigáció kérése a MainWindow felé: pageRequested(str)

Nem felelőssége:
    - oldalváltás végrehajtása (ezt a MainWindow intézi)
    - DB/üzleti logika

Topology (UI):
    MainWindow
      ├─ NavBar  ← this
      └─ QStackedWidget (pages)
"""


# - Importok

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

# - Importok vége


class NavBar(QWidget):
    pageRequested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setObjectName("navBar")  # <-- EZ KELL
        self.setMinimumHeight(44)  # opcionális, de jó

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        self.btn_home = self._mk_btn("Kezdőoldal", "home")
        self.btn_tx = self._mk_btn("Tranzakciók", "transactions")
        self.btn_stats = self._mk_btn("Statisztika", "statistics")
        self.btn_settings = self._mk_btn("Beállítások", "settings")

        layout.addWidget(self.btn_home)
        layout.addWidget(self.btn_tx)
        layout.addWidget(self.btn_stats)
        layout.addStretch(1)
        layout.addWidget(self.btn_settings)

    def _mk_btn(self, text: str, key: str) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("navButton")
        b.setCheckable(True)
        b.setAutoExclusive(True)
        b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        b.clicked.connect(lambda checked, k=key: self.pageRequested.emit(k))
        return b

    def set_active(self, key: str) -> None:
        mapping = {
            "home": self.btn_home,
            "transactions": self.btn_tx,
            "statistics": self.btn_stats,
            "settings": self.btn_settings,
        }
        btn = mapping.get(key)
        if btn:
            btn.setChecked(True)
