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

import sqlite3
from typing import Any, Optional

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
    def __init__(self, ctx:Any = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.ctx = ctx
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

        Jelenlegi funkció:
            - aktív év lekérése az AppContextből
            - éves bevétel / kiadás / megtakarítás összesítése
            - szöveges összefoglaló megjelenítése
        """
        if self.ctx is None:
            self.summary_text.setText(
                "A statisztika oldal még nem kapott alkalmazás-környezetet."
            )
            return

        active_year = getattr(self.ctx.state, "active_year", None)

        if active_year is None:
            self.summary_text.setText(
                "Nincs aktív év kiválasztva a statisztika számításához."
            )
            return

        try:
            summary = self._build_year_summary_text(int(active_year))
        except Exception as exc:
            self.summary_text.setText(
                "A statisztikai összegzés nem sikerült.\n\n"
                f"Hiba:\n{exc}"
            )
            return

        self.summary_text.setText(summary)


    # Segéd metódusok:
    def _build_year_summary_text(self, year: int) -> str:
        """
        Éves pénzügyi összefoglaló szövegének összeállítása.

        Az adatokat a transactions táblából olvassa:
            - income  → bevétel
            - expense → kiadás
        """
        income_total, expense_total = self._load_year_totals(year)

        saving = income_total - expense_total

        if income_total > 0:
            saving_rate = (saving / income_total) * 100
        else:
            saving_rate = 0.0

        lines = [
            f"{year} összefoglalója",
            "",
            f"Összes bevétel: {self._format_money(income_total)}",
            f"Összes kiadás: {self._format_money(expense_total)}",
            f"Megtakarítás: {self._format_money(saving)}",
            f"Megtakarítási arány: {saving_rate:.1f}%",
            "",
        ]

        if income_total == 0 and expense_total == 0:
            lines.append("Ehhez az évhez még nincs rögzített tranzakció.")
        elif saving > 0:
            lines.append("A bevételek jelenleg meghaladják a kiadásokat.")
        elif saving < 0:
            lines.append("A kiadások jelenleg meghaladják a bevételeket.")
        else:
            lines.append("A bevételek és kiadások jelenleg egyensúlyban vannak.")

        return "\n".join(lines)
    



    def _load_year_totals(self, year: int) -> tuple[float, float]:
        """
        Aktív év bevétel / kiadás összesítése SQLite adatbázisból.

        Visszatérés:
            tuple[income_total, expense_total]
        """
        db_path = self.ctx.db.db_name

      
        sql = """
            SELECT
                COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
            FROM transactions
            WHERE year = ?
        """

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (year,))
            row = cursor.fetchone()

        
        if row is None:
            return 0.0, 0.0

        income_total = float(row[0] or 0)
        expense_total = float(row[1] or 0)

        return income_total, expense_total
    



    def _format_money(self, value: float) -> str:
        """
        Forint összeg formázása magyaros, ezres tagolású alakra.
        """
        rounded = int(round(value))
        return f"{rounded:,}".replace(",", " ") + " Ft"
    


    def reload(self) -> None:
        """
        Kompatibilitási alias a MainWindow által használt reload() mintához.
        """
        self.refresh()



    def set_year(self, year: int) -> None:
        """
        Évváltáskor hívható hook.

        A tényleges aktív év továbbra is a ctx.state.active_year értékéből jön,
        de ez a metódus biztosítja, hogy évváltáskor frissülhessen az oldal.
        """
        self.refresh()