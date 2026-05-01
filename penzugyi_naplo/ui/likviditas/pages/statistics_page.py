# - penzugyi_naplo/ui/pages/statistics_page.py
# -----------------------------------------------

"""
Statisztika oldal a fő alkalmazásban
(ui/pages/statistics_page.py).

Cél:
    - diagramok, kimutatások és összegzések megjelenítése
    - általános pénzügyi összefoglaló előkészítése
    - éves és havi bontású statisztikai nézetek előkészítése

Állapot:
    - jelenleg tabos UI-váz
    - a diagram-rajzolás logikája később külön modulban: ui/charts.py (ChartManager)

Topology (UI):
    MainWindow
      └─ StatisticsPage  ← this
           ├─ Általános fül
           └─ Diagramok fül
"""


# ----- Importok -------

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ----- Importok vége ----


class StatisticsPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Statisztika")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setObjectName("pageTitle")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("statisticsTabs")

        self.general_tab = self._build_general_tab()
        self.charts_tab = self._build_charts_tab()

        self.tabs.addTab(self.general_tab, "Általános")
        self.tabs.addTab(self.charts_tab, "Diagramok")

        root.addWidget(self.tabs, 1)

    def _build_general_tab(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        period_label = QLabel("Időszak:")
        period_label.setObjectName("fieldLabel")

        self.period_combo = QComboBox()
        self.period_combo.setObjectName("statisticsPeriodCombo")
        self.period_combo.addItems(
            [
                "Aktív év",
                "Utolsó 3 hónap",
                "Utolsó 6 hónap",
                "Teljes adatbázis",
            ]
        )

        top_row.addWidget(period_label)
        top_row.addWidget(self.period_combo)
        top_row.addStretch(1)

        layout.addLayout(top_row)

        summary_card = QFrame()
        summary_card.setObjectName("statisticsSummaryCard")

        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(8)

        summary_title = QLabel("Általános összefoglaló")
        summary_title.setObjectName("cardTitleStrong")

        self.summary_text = QLabel(
            "Itt jelenik majd meg az automatikusan generált szöveges összegzés.\n\n"
            "Például:\n"
            "– hogyan alakult a bevétel\n"
            "– nőtt vagy csökkent a kiadás\n"
            "– mennyi volt a megtakarítás\n"
            "– van-e feltűnő eltérés az előző időszakhoz képest"
        )
        self.summary_text.setObjectName("statisticsSummaryText")
        self.summary_text.setWordWrap(True)

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_text)

        layout.addWidget(summary_card)

        trend_card = QFrame()
        trend_card.setObjectName("statisticsChartCard")

        trend_layout = QVBoxLayout(trend_card)
        trend_layout.setContentsMargins(16, 14, 16, 14)
        trend_layout.setSpacing(8)

        trend_title = QLabel("Trenddiagram")
        trend_title.setObjectName("cardTitleStrong")

        trend_placeholder = QLabel("Ide kerül majd az egyszerű vonaldiagram.")
        trend_placeholder.setObjectName("chartPlaceholder")
        trend_placeholder.setAlignment(Qt.AlignCenter)

        trend_layout.addWidget(trend_title)
        trend_layout.addWidget(trend_placeholder, 1)

        layout.addWidget(trend_card, 1)

        return page

    def _build_charts_tab(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        yearly_card = QFrame()
        yearly_card.setObjectName("statisticsChartCard")

        yearly_layout = QVBoxLayout(yearly_card)
        yearly_layout.setContentsMargins(16, 14, 16, 14)
        yearly_layout.setSpacing(8)

        yearly_title = QLabel("Éves bevétel / éves kiadás")
        yearly_title.setObjectName("cardTitleStrong")

        yearly_placeholder = QLabel("Ide kerül majd a zöld / piros éves oszlopdiagram.")
        yearly_placeholder.setObjectName("chartPlaceholder")
        yearly_placeholder.setAlignment(Qt.AlignCenter)

        yearly_layout.addWidget(yearly_title)
        yearly_layout.addWidget(yearly_placeholder, 1)

        monthly_card = QFrame()
        monthly_card.setObjectName("statisticsChartCard")

        monthly_layout = QVBoxLayout(monthly_card)
        monthly_layout.setContentsMargins(16, 14, 16, 14)
        monthly_layout.setSpacing(8)

        monthly_title = QLabel("Havi bontás")
        monthly_title.setObjectName("cardTitleStrong")

        monthly_placeholder = QLabel(
            "Ide kerül majd a havi bontás:\n"
            "Terv bevétel / valós bevétel / kiadás / megtakarítás."
        )
        monthly_placeholder.setObjectName("chartPlaceholder")
        monthly_placeholder.setAlignment(Qt.AlignCenter)

        monthly_layout.addWidget(monthly_title)
        monthly_layout.addWidget(monthly_placeholder, 1)

        layout.addWidget(yearly_card, 1)
        layout.addWidget(monthly_card, 1)

        return page

    def refresh(self) -> None:
        """
        Statisztikai adatok újratöltése.

        Jelenleg helyfoglaló metódus.
        Később innen frissülhetnek:
            - szöveges összegzés
            - trenddiagram
            - éves bevétel / kiadás diagram
            - havi bontású diagramok
        """
        pass