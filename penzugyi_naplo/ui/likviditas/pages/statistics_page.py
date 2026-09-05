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
from datetime import UTC, date, datetime
from typing import Any

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ----- Importok vége ----

print(f"[DEBUG] statistics_page.py modul betöltve innen: {__file__}")

MONTH_LABELS = [
    "Január", "Február", "Március", "Április", "Május", "Június",
    "Július", "Augusztus", "Szeptember", "Október", "November", "December",
]




class StatisticSummaryCard(QFrame):
    def __init__(
        self,
        title: str,
        accent: str,
        value: str = "0 Ft",
        subtitle: str = "",
        symbol: str = "↗",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("statSummaryCard")
        self.accent = accent

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statCardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statCardValue")
        self.value_label.setStyleSheet(f"color: {accent};")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("statCardSubtitle")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.value_label)
        text_layout.addWidget(self.subtitle_label)

        self.symbol_label = QLabel(symbol)
        self.symbol_label.setObjectName("statCardSymbol")
        self.symbol_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.symbol_label.setStyleSheet(f"color: {accent};")

        root.addLayout(text_layout, 1)
        root.addWidget(
            self.symbol_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )


    def set_values(self, value: str, subtitle: str = "") -> None:
        """
        A statisztikai kártya értékének és alsó magyarázó szövegének frissítése.
        """
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)






















class StatisticsPage(QWidget):
    def __init__(self, ctx:Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        print(f"[DEBUG] StatisticsPage példány létrehozva. Forrásfájl: {__file__}")

        self.ctx = ctx

        # A statisztikai kártyák több fülön is megjelenhetnek.
        # Ezért listában tároljuk a kártyacsoportokat, hogy refreshkor mind frissüljön.
        self.summary_card_sets: list[tuple[
            StatisticSummaryCard,
            StatisticSummaryCard,
            StatisticSummaryCard,
            StatisticSummaryCard,
        ]] = []


        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("Statisztika")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setObjectName("pageTitle")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("statisticsTabs")

        self.general_tab = self._build_general_tab()
        self.charts_tab = self._build_charts_tab()

        self.tabs.addTab(self.general_tab, "Általános")
        self.tabs.addTab(self.charts_tab, "Diagramok")

        root.addWidget(self.tabs, 1)


    def _build_summary_cards(self) -> QWidget:
        
        """
        Felső összegző kártyasor létrehozása.

        Ugyanezt használhatja az Általános és a Diagramok fül is.
        A létrehozott kártyákat eltesszük, hogy refreshkor egyszerre frissüljenek.
        """

        container = QWidget()
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        income_card = StatisticSummaryCard("Összes bevétel", "#16a34a", symbol="↗")
        expense_card = StatisticSummaryCard("Összes kiadás", "#dc2626", symbol="↘")
        saving_card = StatisticSummaryCard("Megtakarítás", "#2563eb", symbol="◆")
        saving_rate_card = StatisticSummaryCard("Megtakarítási arány", "#7c3aed", symbol="%")

        for card in (
            income_card,
            expense_card,
            saving_card,
            saving_rate_card,
        ):
            card.setMinimumHeight(92)

        layout.addWidget(income_card, 0, 0)
        layout.addWidget(expense_card, 0, 1)
        layout.addWidget(saving_card, 0, 2)
        layout.addWidget(saving_rate_card, 0, 3)

        self.summary_card_sets.append(
            (
                income_card,
                expense_card,
                saving_card,
                saving_rate_card,
            )
        )

        return container






























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
                "Aktuális hónap",
                "Utolsó 3 hónap",
                "Utolsó 6 hónap",
                "Teljes adatbázis",
            ]
        )
        # Ez volt a hiányzó kapocs: enélkül a combo box váltása
        # soha nem hívta meg a refresh()-t.
        self.period_combo.currentIndexChanged.connect(self.refresh)

        top_row.addWidget(period_label)
        top_row.addWidget(self.period_combo)
        top_row.addStretch(1)

        layout.addLayout(top_row)

        self.summary_cards = self._build_summary_cards()
        layout.addWidget(self.summary_cards)




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

        self.trend_chart_view = QChartView()
        self.trend_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        trend_layout.addWidget(trend_title)
        trend_layout.addWidget(self.trend_chart_view, 1)

        layout.addWidget(trend_card, 1)

        return page

    def _build_charts_tab(self) -> QWidget:
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # Diagramok fül tetejére is jöhetnek az összesítő kártyák.
        self.charts_summary_cards = self._build_summary_cards()
        layout.addWidget(self.charts_summary_cards)

        monthly_card = QFrame()
        monthly_card.setObjectName("statisticsChartCard")

        monthly_layout = QVBoxLayout(monthly_card)
        monthly_layout.setContentsMargins(16, 14, 16, 14)
        monthly_layout.setSpacing(8)

        monthly_title = QLabel("Havi bevétel / kiadás / megtakarítás")
        monthly_title.setObjectName("cardTitleStrong")

        self.monthly_bar_chart_view = QChartView()
        self.monthly_bar_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.monthly_bar_chart_view.setMinimumHeight(200)

        monthly_layout.addWidget(monthly_title)
        monthly_layout.addWidget(self.monthly_bar_chart_view, 1)

        category_card = QFrame()
        category_card.setObjectName("statisticsChartCard")

        category_layout = QVBoxLayout(category_card)
        category_layout.setContentsMargins(16, 14, 16, 14)
        category_layout.setSpacing(8)

        category_title = QLabel("Kiadások kategóriák szerint")
        category_title.setObjectName("cardTitleStrong")

        self.category_pie_chart_view = QChartView()
        self.category_pie_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.category_pie_chart_view.setMinimumHeight(200)

        category_layout.addWidget(category_title)
        category_layout.addWidget(self.category_pie_chart_view, 1)

        layout.addWidget(monthly_card, 1)
        layout.addWidget(category_card, 1)

        return page
    


    def _resolve_period_range(
        self, active_year: int
    ) -> tuple[str | None, str | None, str]:
        """
        A period_combo aktuális kiválasztásából kiszámolja a szűrendő
        dátumtartományt.

        Visszatérés:
            tuple[start_date, end_date, mode]
                - start_date / end_date: 'YYYY-MM-DD' string, vagy None ha nincs korlát
                  (pl. "Teljes adatbázis" esetén mindkettő None)
                - mode: "year" | "range" | "all"
                    "year"  -> régi, egy-éves viselkedés (Aktív év)
                    "range" -> konkrét [start_date, end_date] intervallum
                               (Aktuális hónap / Utolsó 3 hónap / Utolsó 6 hónap)
                    "all"   -> teljes adatbázis, nincs dátumkorlát
        """
        selection = self.period_combo.currentText() if hasattr(self, "period_combo") else "Aktív év"

        # Use timezone-aware current date to avoid naive datetime usage
        today = datetime.now(tz=UTC).date()

        if selection == "Aktív év":
            return None, None, "year"

        if selection == "Teljes adatbázis":
            return None, None, "all"

        if selection == "Aktuális hónap":
            start = date(today.year, today.month, 1)
            end = today
            return start.isoformat(), end.isoformat(), "range"

        if selection in ("Utolsó 3 hónap", "Utolsó 6 hónap"):
            months_back = 3 if selection == "Utolsó 3 hónap" else 6

            # Hónap-visszaszámolás évhatáron át is (pl. 2026 február - 3 hónap -> 2025 november).
            total_month_index = (today.year * 12 + (today.month - 1)) - (months_back - 1)
            start_year, start_month = divmod(total_month_index, 12)
            start_month += 1

            start = date(start_year, start_month, 1)
            end = today
            return start.isoformat(), end.isoformat(), "range"

        # Ismeretlen/váratlan érték esetén essünk vissza a régi, biztonságos viselkedésre.
        return None, None, "year"

    def refresh(self) -> None:
        """
        Statisztikai adatok újratöltése az Időszak szűrő aktuális állása szerint.

        Az Időszak szűrő (self.period_combo) értéke alapján:
            - "Aktív év"          -> a korábbi, egy évre szűrő logika (year oszlop)
            - "Teljes adatbázis"  -> nincs dátumkorlát
            - egyéb (hónap/3/6 hó)-> konkrét [start_date, end_date] tartomány (tx_date oszlop)
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

        active_year = int(active_year)
        start_date, end_date, mode = self._resolve_period_range(active_year)

        try:
            summary = self._build_period_summary_text(
                active_year=active_year,
                start_date=start_date,
                end_date=end_date,
                mode=mode,
            )
        except (sqlite3.Error, ValueError, TypeError) as exc:
            # Handle expected errors from DB access, invalid period ranges or type issues
            self.summary_text.setText(
                "A statisztikai összegzés nem sikerült.\n\n"
                f"Hiba:\n{exc}"
            )
            return

        self.summary_text.setText(summary)

        # --- Összegző kártyák (bevétel/kiadás/megtakarítás/arány) ---
        try:
            income_total, expense_total = self._load_period_totals(
                active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
            )

            period_label = self._period_label(
                active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
            )

            # Az összegző kártyák több helyen is megjelennek, ezért mindegyiket frissíteni kell.
            self._update_summary_cards(
                year=active_year,
                income_total=income_total,
                expense_total=expense_total,
                period_label=period_label,
            )
        except (sqlite3.Error, ValueError, TypeError) as exc:
            for (
                income_card,
                expense_card,
                saving_card,
                saving_rate_card,
            ) in self.summary_card_sets:
                for card in (income_card, expense_card, saving_card, saving_rate_card):
                    card.set_values("Hiba", "Nem sikerült betölteni")
            print(f"[HIBA] Összegző kártyák frissítése sikertelen: {exc}")

        # --- Trenddiagram + havi oszlopdiagram ---
        try:
            month_labels, income_values, expense_values, saving_values = (
                self._load_period_monthly_totals(
                    active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
                )
            )

            self._update_trend_chart(
                income_values=income_values,
                expense_values=expense_values,
                saving_values=saving_values,
                month_labels=month_labels,
            )

            self._update_monthly_bar_chart(
                income_values=income_values,
                expense_values=expense_values,
                saving_values=saving_values,
                month_labels=month_labels,
            )
        except (sqlite3.Error, ValueError, TypeError) as exc:
            error_chart = QChart()
            error_chart.setTitle("A diagram betöltése nem sikerült.")
            self.trend_chart_view.setChart(error_chart)

            error_chart_2 = QChart()
            error_chart_2.setTitle("A diagram betöltése nem sikerült.")
            self.monthly_bar_chart_view.setChart(error_chart_2)

            print(f"[HIBA] Havi diagramok frissítése sikertelen: {exc}")

        # --- Kategória szerinti kiadás kördiagram ---
        try:
            category_values = self._load_period_expenses_by_category(
                active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
            )
            self._update_category_pie_chart(category_values)
        except (sqlite3.Error, ValueError, TypeError) as exc:
            error_chart = QChart()
            error_chart.setTitle("A diagram betöltése nem sikerült.")
            self.category_pie_chart_view.setChart(error_chart)
            print(f"[HIBA] Kategória kördiagram frissítése sikertelen: {exc}")



    # --- Segéd metódusok: WHERE-feltétel összeállítása mode szerint ---

    def _period_where_clause(
        self,
        *,
        active_year: int,
        start_date: str | None,
        end_date: str | None,
        mode: str,
    ) -> tuple[str, tuple]:
        """
        Egységes helyen állítja elő a WHERE feltételt és a hozzá tartozó
        SQL paramétereket, a period módja szerint.
        """
        if mode == "year":
            return "WHERE year = ?", (active_year,)

        if mode == "range":
            return "WHERE tx_date BETWEEN ? AND ?", (start_date, end_date)

        # mode == "all": nincs szűrés
        return "", ()

    def _period_label(
        self, *, active_year: int, start_date: str | None, end_date: str | None, mode: str
    ) -> str:
        if mode == "year":
            return str(active_year)
        if mode == "all":
            return "Teljes adatbázis"
        return f"{start_date} – {end_date}"

    # Segéd metódusok:
    def _build_period_summary_text(
        self,
        *, active_year: int, start_date: str | None, end_date: str | None, mode: str,
    ) -> str:
        """
        Pénzügyi összefoglaló szövegének összeállítása a kiválasztott
        Időszak szűrő szerint.
        """
        income_total, expense_total = self._load_period_totals(
            active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
        )

        saving = income_total - expense_total

        saving_rate = (saving / income_total) * 100 if income_total > 0 else 0.0

        period_label = self._period_label(
            active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
        )

        lines = [
            f"{period_label} összefoglalója",
            "",
            f"Összes bevétel: {self._format_money(income_total)}",
            f"Összes kiadás: {self._format_money(expense_total)}",
            f"Megtakarítás: {self._format_money(saving)}",
            f"Megtakarítási arány: {saving_rate:.1f}%",
            "",
        ]

        if income_total == 0 and expense_total == 0:
            lines.append("Ehhez az időszakhoz még nincs rögzített tranzakció.")
        elif saving > 0:
            lines.append("A bevételek jelenleg meghaladják a kiadásokat.")
        elif saving < 0:
            lines.append("A kiadások jelenleg meghaladják a bevételeket.")
        else:
            lines.append("A bevételek és kiadások jelenleg egyensúlyban vannak.")

        return "\n".join(lines)
    

    def _update_summary_cards(
        self,
        *,
        year: int,
        income_total: float,
        expense_total: float,
        period_label: str | None = None,
    ) -> None:
        """
        Felső statisztikai kártyák frissítése.

        Minden regisztrált kártyasort frissít:
            - Általános fül
            - Diagramok fül
        """
        saving = income_total - expense_total

        saving_rate = (saving / income_total) * 100 if income_total > 0 else 0.0

        label = period_label if period_label is not None else str(year)

        for (
            income_card,
            expense_card,
            saving_card,
            saving_rate_card,
        ) in self.summary_card_sets:
            income_card.set_values(
                self._format_money(income_total),
                f"{label} összes bevétele",
            )
            expense_card.set_values(
                self._format_money(expense_total),
                f"{label} összes kiadása",
            )
            saving_card.set_values(
                self._format_money(saving),
                f"{label} megtakarítása",
            )
            saving_rate_card.set_values(
                f"{saving_rate:.1f}%",
                "Megtakarítás / bevétel",
            )



    def _load_period_totals(
        self,
        *, active_year: int, start_date: str | None, end_date: str | None, mode: str,
    ) -> tuple[float, float]:
        """
        Bevétel / kiadás összesítése SQLite adatbázisból, a kiválasztott
        Időszak szűrő (self.period_combo) szerint.

        Visszatérés:
            tuple[income_total, expense_total]
        """

        database_path = self.ctx.db.db_name

        where_clause, params = self._period_where_clause(
            active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
        )

        sql = f"""
            SELECT
                COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
            FROM transactions
            {where_clause}
        """

        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
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
        rounded = round(value)
        return f"{rounded:,}".replace(",", " ") + " Ft"
    


    def _load_period_monthly_totals(
        self,
        *, active_year: int, start_date: str | None, end_date: str | None, mode: str,
    ) -> tuple[list[str], list[float], list[float], list[float]]:
        """
        Havi bevétel / kiadás / megtakarítás összesítése SQLite adatbázisból,
        a kiválasztott Időszak szűrő szerint.

        mode == "year": a korábbi viselkedés, 12 hónap (Január..December) egy évre.
        mode == "range": csak a [start_date, end_date] tartományba eső hónapok,
                         dinamikus hónapszámmal (pl. 3 vagy 6 oszlop).
        mode == "all": teljes adatbázis, hónap szerint összesítve évektől
                       függetlenül (Január..December, minden év összeadva).

        Visszatérés:
            tuple[month_labels, income_values, expense_values, saving_values]
        """

        database_path = self.ctx.db.db_name

        if mode == "year":
            income_values = [0.0] * 12
            expense_values = [0.0] * 12

            sql = """
                SELECT
                    month,
                    COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
                FROM transactions
                WHERE year = ?
                GROUP BY month
                ORDER BY month
            """

            with sqlite3.connect(database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (active_year,))
                rows = cursor.fetchall()

            for month, income_total, expense_total in rows:
                month_index = int(month) - 1

                if 0 <= month_index < 12:
                    income_values[month_index] = float(income_total or 0)
                    expense_values[month_index] = float(expense_total or 0)

            saving_values = [
                income - expense
                for income, expense in zip(income_values, expense_values, strict=True)
            ]

            return list(MONTH_LABELS), income_values, expense_values, saving_values

        if mode == "all":
            # Hónap szerint összesítve, évektől függetlenül.
            income_values = [0.0] * 12
            expense_values = [0.0] * 12

            sql = """
                SELECT
                    month,
                    COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
                FROM transactions
                GROUP BY month
                ORDER BY month
            """

            with sqlite3.connect(database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()

            for month, income_total, expense_total in rows:
                month_index = int(month) - 1

                if 0 <= month_index < 12:
                    income_values[month_index] = float(income_total or 0)
                    expense_values[month_index] = float(expense_total or 0)

            saving_values = [
                income - expense
                for income, expense in zip(income_values, expense_values, strict=True)
            ]

            return list(MONTH_LABELS), income_values, expense_values, saving_values

        # mode == "range": dinamikus hónaptartomány a [start_date, end_date] között.
        sql = """
            SELECT
                strftime('%Y-%m', tx_date) AS ym,
                COALESCE(SUM(CASE WHEN tx_type = 'income' THEN amount ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN tx_type = 'expense' THEN amount ELSE 0 END), 0)
            FROM transactions
            WHERE tx_date BETWEEN ? AND ?
            GROUP BY ym
            ORDER BY ym
        """

        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (start_date, end_date))
            rows = cursor.fetchall()

        totals_by_ym = {ym: (float(inc or 0), float(exp or 0)) for ym, inc, exp in rows}

        # Az összes hónapot generáljuk a tartományban, hogy az üres hónapok is
        # megjelenjenek 0 értékkel (ne csak azok, amikben volt tranzakció).

        # "range" módban start_date/end_date mindig kötelező (lásd _resolve_period_range).
        # Ez a védőellenőrzés a Pylance típus-narrowing kedvéért is kell.
        if start_date is None or end_date is None:
            raise ValueError("range módhoz start_date és end_date kötelező")

        start_year, start_month = int(start_date[:4]), int(start_date[5:7])
        end_year, end_month = int(end_date[:4]), int(end_date[5:7])

        month_labels: list[str] = []
        income_values = []
        expense_values = []

        cursor_index = start_year * 12 + (start_month - 1)
        end_index = end_year * 12 + (end_month - 1)

        while cursor_index <= end_index:
            y, m = divmod(cursor_index, 12)
            m += 1
            ym_key = f"{y:04d}-{m:02d}"

            income, expense = totals_by_ym.get(ym_key, (0.0, 0.0))
            month_labels.append(f"{MONTH_LABELS[m - 1]} {y}")
            income_values.append(income)
            expense_values.append(expense)

            cursor_index += 1

        saving_values = [
            income - expense
            for income, expense in zip(income_values, expense_values, strict=True)
        ]

        return month_labels, income_values, expense_values, saving_values
    


    def _update_trend_chart(
        self,
        *,
        income_values: list[float],
        expense_values: list[float],
        saving_values: list[float],
        month_labels: list[str] | None = None,
    ) -> None:
        """
        Trenddiagram frissítése.

        Megjelenítés:
            - Bevétel: zöld oszlop
            - Kiadás: piros oszlop
            - Megtakarítás: kék vonal

        month_labels: az X tengely feliratai. Ha None, a régi, fix
        12 hónapos MONTH_LABELS-t használjuk (visszafelé kompatibilitás).
        """
        labels = month_labels if month_labels is not None else MONTH_LABELS
        
        income_set = QBarSet("Bevétel")
        expense_set = QBarSet("Kiadás")

        income_set.setColor(QColor("#22c55e"))
        expense_set.setColor(QColor("#ef4444"))

        income_set.append(income_values)
        expense_set.append(expense_values)

        bar_series = QBarSeries()
        bar_series.append(income_set)
        bar_series.append(expense_set)

        saving_series = QLineSeries()
        saving_series.setName("Megtakarítás")
        saving_series.setColor(QColor("#2563eb"))

        for index, value in enumerate(saving_values):
            saving_series.append(float(index), float(value))

        chart = QChart()
        chart.setTitle("Bevétel / kiadás / megtakarítás havi bontásban")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        chart.addSeries(bar_series)
        chart.addSeries(saving_series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)

        all_values = income_values + expense_values + saving_values
        max_value = max(all_values) if all_values else 0

        if max_value <= 0:
            max_value = 1

        axis_y = QValueAxis()
        axis_y.setRange(0, max_value * 1.15)
        axis_y.setLabelFormat("%.0f Ft")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        bar_series.attachAxis(axis_x)
        bar_series.attachAxis(axis_y)

        saving_series.attachAxis(axis_x)
        saving_series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)

        self.trend_chart_view.setChart(chart)


    def _update_monthly_bar_chart(
        self,
        *,
        income_values: list[float],
        expense_values: list[float],
        saving_values: list[float],
        month_labels: list[str] | None = None,
    ) -> None:
        """
        Diagramok fül havi oszlopdiagramjának frissítése.

        Megjelenítés:
            - Bevétel: zöld oszlop
            - Kiadás: piros oszlop
            - Megtakarítás: kék oszlop

        month_labels: az X tengely feliratai. Ha None, a régi, fix
        12 hónapos MONTH_LABELS-t használjuk (visszafelé kompatibilitás).
        """
        labels = month_labels if month_labels is not None else MONTH_LABELS

        income_set = QBarSet("Bevétel")
        expense_set = QBarSet("Kiadás")
        saving_set = QBarSet("Megtakarítás")

        income_set.setColor(QColor("#22c55e"))
        expense_set.setColor(QColor("#ef4444"))
        saving_set.setColor(QColor("#2563eb"))

        income_set.append(income_values)
        expense_set.append(expense_values)
        saving_set.append(saving_values)

        series = QBarSeries()
        series.append(income_set)
        series.append(expense_set)
        series.append(saving_set)

        chart = QChart()
        chart.setTitle("")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(labels)

        all_values = income_values + expense_values + saving_values
        max_value = max(all_values) if all_values else 0
        min_value = min(all_values) if all_values else 0

        if max_value <= 0:
            max_value = 1

        axis_y = QValueAxis()
        axis_y.setRange(min(0, min_value * 1.15), max_value * 1.15)
        axis_y.setLabelFormat("%.0f Ft")

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)

        self.monthly_bar_chart_view.setChart(chart)



    def _update_category_pie_chart(
        self,
        category_values: list[tuple[str, float]],
    ) -> None:
        """
        Diagramok fül kategória szerinti kiadás kördiagramjának frissítése.
        """

        chart = QChart()
        chart.setTitle("")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        if not category_values:
            chart.setTitle("Nincs megjeleníthető kiadási adat.")
            self.category_pie_chart_view.setChart(chart)
            return

        total = sum(amount for _, amount in category_values)

        series = QPieSeries()
        series.setHoleSize(0.35)

        colors = [
            QColor("#2563eb"),
            QColor("#ef4444"),
            QColor("#22c55e"),
            QColor("#a855f7"),
            QColor("#f59e0b"),
            QColor("#64748b"),
            QColor("#14b8a6"),
            QColor("#ec4899"),
        ]

        for index, (category_name, amount) in enumerate(category_values):
            percent = (amount / total * 100) if total > 0 else 0.0

            label = (
                f"{category_name}\n"
                f"{self._format_money(amount)} · {percent:.1f}%"
            )

            slice_item = series.append(label, amount)
            slice_item.setLabelVisible(True)
            slice_item.setColor(colors[index % len(colors)])

        chart.addSeries(series)

        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)

        self.category_pie_chart_view.setChart(chart)








    def _load_period_expenses_by_category(
        self,
        *,
        active_year: int,
        start_date: str | None,
        end_date: str | None,
        mode: str,
    ) -> list[tuple[str, float]]:
        """
        Kiadások összesítése kategória szerint, a kiválasztott Időszak
        szűrő szerint.

            - transactions táblából olvas
            - categories táblával LEFT JOIN
            - csak expense típusú tranzakciókat számol
        """

        database_path = self.ctx.db.db_name

        where_clause, params = self._period_where_clause(
            active_year=active_year, start_date=start_date, end_date=end_date, mode=mode
        )

        # A meglévő WHERE feltételhez hozzáfűzzük az expense-szűrést.
        # (mode == "all" esetén where_clause üres, ott WHERE-rel kell kezdeni.)
        if where_clause:
            # tx.year / tx.tx_date oszlopokra hivatkozás t. prefixszel.
            where_clause = where_clause.replace("year = ?", "t.year = ?").replace(
                "tx_date BETWEEN", "t.tx_date BETWEEN"
            )
            expense_clause = f"{where_clause} AND t.tx_type = 'expense'"
        else:
            expense_clause = "WHERE t.tx_type = 'expense'"

        sql = f"""
            SELECT
                COALESCE(c.name, 'Nincs kategória') AS category_name,
                COALESCE(SUM(t.amount), 0) AS total_amount
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            {expense_clause}
            GROUP BY c.name
            HAVING total_amount > 0
            ORDER BY total_amount DESC
        """

        with sqlite3.connect(database_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        return [
            (str(category_name), float(total_amount or 0))
            for category_name, total_amount in rows
        ]





    















    # --- Külső frissítési hookok

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