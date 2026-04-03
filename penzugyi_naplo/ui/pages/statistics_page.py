# - penzugyi_naplo/ui/pages/statistics_page.py
# -----------------------------------------------

"""
Statisztika oldal a fő alkalmazásban
(ui/pages/statistics_page.py).

Cél:
    - diagramok, kimutatások és összegzések megjelenítése

Állapot:
    - jelenleg váz (placeholder)
    - a diagram-rajzolás logikája külön modulban: ui/charts.py (ChartManager)

Topology (UI):
    MainWindow
      └─ StatisticsPage  ← this
           └─ ChartManager (ui/charts.py)
"""


# ----- Importok -------

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

# ----- Importok vége ----


class StatisticsPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        title = QLabel("Statisztika")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setObjectName("pageTitle")

        hint = QLabel("Itt lesznek a diagramok, kimutatások, összegzések.")
        hint.setWordWrap(True)
        hint.setObjectName("pageHint")

        root.addWidget(title)
        root.addWidget(hint)
        root.addStretch(1)
