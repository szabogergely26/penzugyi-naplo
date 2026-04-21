# # - ui/likviditas/pages/home_page.py
# -------------------------------------


"""
Kezdőoldal / Dashboard oldal
(ui/pages/home_page.py).

Felelősség:
    - havi bontású pénzügyi összesítések megjelenítése
    - bevételek, kiadások, számlák és megtakarítás számítása

Év-kezelés:
    - aktív év a MainWindow-tól érkezik
    - set_year() -> reload()

Adatforrás:
    - TransactionDatabase (havi/éves összesítések)

UI:
    - havi táblázatos nézet (Jan–Dec fix sorrend)
    - belső tabok: "Kezdőoldal" / "Számlák"

Topology (UI):
    MainWindow
      └─ HomePage  ← this
           ├─ HomeSummaryPanel (ui/home_summary_panel.py)
           └─ QTableWidget (havi dashboard)

"""


# --- Importok ---

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.core.app_context import AppContext
from penzugyi_naplo.ui.likviditas.dialogs.home_table_dialog import HomeTableDialog
from penzugyi_naplo.ui.likviditas.dialogs.month_details_dialog import MonthDetailsDialog
from penzugyi_naplo.ui.likviditas.widgets.home_summary_panel import HomeSummaryPanel



# - Importok vége - #



@dataclass
class HomeSummaryRow:
    month_label: str
    planned_income: float
    actual_income: float
    income_diff: float
    planned_expense: float
    planned_fixed_expense: float
    actual_expense: float
    expense_diff: float
    planned_savings: float
    actual_savings: float







# - Konstansok, segédfüggvények - #


MONTHS_HU = [
    "Január",
    "Február",
    "Március",
    "Április",
    "Május",
    "Június",
    "Július",
    "Augusztus",
    "Szeptember",
    "Október",
    "November",
    "December",
]


def fmt_huf(x: float) -> str:
    s = f"{int(round(x)):,}".replace(",", " ")
    return s


def parse_huf(text: str) -> float:
    """
    Engedjük: '12 000', '12000', '12 000 Ft'
    """
    t = (text or "").strip()
    if not t:
        return 0.0
    t = t.replace("Ft", "").replace("ft", "").replace(" ", "")
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0













# - HomePage osztály -


class HomePage(QWidget):
    """
    Kezdőoldal (dashboard):
    - Havi bontás: Bevételek / Kiadások
    - Aktív év szerint frissül (MainWindow set_year hívja)
    """

    def __init__(self, ctx: AppContext, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ctx = ctx
        self.dev_mode = self.ctx.dev_mode
        self._year = int(self.ctx.state.active_year)

        self.log = getattr(parent, "log", None)

        # LOG:
        if self.log:
            self.log.d("AKTIV HOME_PAGE: ui/likviditas/pages/home_page.py")


        self._updating = False

        # --- UI felépítése ---
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Kezdőoldal")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        subtitle = QLabel("Havi összesítők az aktív év tranzakcióiból.")
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        content = QFrame()
        content.setObjectName("homeContent")
        content.setFrameShape(QFrame.NoFrame)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)


        


        # --- Belső tabok a Kezdőoldalon ---
        self.tabs = QTabWidget(content)
        self.tabs.setObjectName("homeTabs")


       





        # 1) Kezdőoldal TAB
        tab_dashboard = QWidget()
        dash_layout = QVBoxLayout(tab_dashboard)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_layout.setSpacing(12)

        self.summary = HomeSummaryPanel(self)
        dash_layout.addWidget(self.summary)
        dash_layout.addSpacing(8)

        btn = QPushButton("Táblázatos nézet")   
        btn.clicked.connect(self.open_table_dialog)
        dash_layout.addWidget(btn)

        self.dashboard_body = QFrame()
        self.dashboard_body.setObjectName("homeDashboardBody")

        self.dashboard_body_layout = QVBoxLayout(self.dashboard_body)
        self.dashboard_body_layout.setContentsMargins(0, 0, 0, 0)
        self.dashboard_body_layout.setSpacing(0)

        self.cards_container = self._build_cards_view()
        self.dashboard_body_layout.addWidget(self.cards_container)

        dash_layout.addWidget(self.dashboard_body, 1)
        
        # kis térköz
        dash_layout.addSpacing(8)





       



    
        # 2) Számlák TAB
        tab_bills = QWidget()
        bills_layout = QVBoxLayout(tab_bills)
        bills_layout.setContentsMargins(0, 0, 0, 0)
        bills_layout.setSpacing(12)

        # Felül: számlainfók "kártya"
        info_card = QFrame()
        info_card.setObjectName("bankInfoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(12, 12, 12, 12)
        info_layout.setSpacing(6)

        info_title = QLabel("Raiffeisen Bank számlainfók")
        info_title.setObjectName("sectionTitle")

        self.lbl_total_balance = QLabel("Teljes egyenleg: –")
        self.lbl_metal_balance = QLabel("Nemesfém egyenleg: –")
        self.lbl_cash_balance = QLabel("Készpénz: –")

        info_layout.addWidget(info_title)
        info_layout.addWidget(self.lbl_total_balance)
        info_layout.addWidget(self.lbl_metal_balance)
        info_layout.addWidget(self.lbl_cash_balance)

        bills_layout.addWidget(info_card)

        # Alul: ide jön majd a számlák listája/táblája (később)
        placeholder = QLabel("Számlák listája (hamarosan)")
        placeholder.setObjectName("mutedText")
        bills_layout.addWidget(placeholder, 1)

        # Tabok felvétele
        self.tabs.addTab(tab_dashboard, "Kezdőoldal")
        self.tabs.addTab(tab_bills, "Számlák")

        # TabWidget a content-be
        content_layout.addWidget(self.tabs)

        # --- összerakás ---
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(content, 1)

        

        self.reload()

      
        self._updating = False

        


  
    def _build_summary_rows(self) -> list[HomeSummaryRow]:
        rows: list[HomeSummaryRow] = []

        actual = self.ctx.db.get_monthly_income_expense_bills(self._year)
        plans = self.ctx.db.get_year_plans(self._year)

        for month in range(1, 13):
            p_income, p_expense, p_fixed = plans.get(month, (0.0, 0.0, 0.0))
            income, expense_core, bills = actual.get(month, (0.0, 0.0, 0.0))

            actual_expense = float(expense_core) + float(bills)

            income_diff = float(income) - float(p_income)
            planned_total_expense = float(p_expense) + float(p_fixed)
            expense_diff = float(actual_expense) - float(planned_total_expense)

            planned_savings = float(p_income) - float(planned_total_expense)
            actual_savings = float(income) - float(actual_expense)

            rows.append(
                HomeSummaryRow(
                    month_label=MONTHS_HU[month - 1],
                    planned_income=float(p_income),
                    actual_income=float(income),
                    income_diff=float(income_diff),
                    planned_expense=float(p_expense),
                    planned_fixed_expense=float(p_fixed),
                    actual_expense=float(actual_expense),
                    expense_diff=float(expense_diff),
                    planned_savings=float(planned_savings),
                    actual_savings=float(actual_savings),
                )
            )

        return rows


        

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)

            child_widget = item.widget()
            child_layout = item.layout()

            if child_widget is not None:
                child_widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)


    


    def _build_cards_view(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("homeCardsWrapper")
        wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        return wrapper

    def _make_info_pair(
        self,
        left_label: str,
        left_value: float,
        right_label: str,
        right_value: float,
    ) -> QFrame:
        row = QFrame()
        row.setObjectName("monthInfoRow")

        grid = QGridLayout(row)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(4)

        lbl1 = QLabel(left_label)
        lbl1.setObjectName("monthInfoLabel")
        


        val1 = QLabel(f"{fmt_huf(left_value)} Ft")
        val1.setObjectName("monthInfoValue")
        val1.setProperty("positive", left_value >= 0)
       
        

        lbl2 = QLabel(right_label)
        lbl2.setObjectName("monthInfoLabel")
        

        val2 = QLabel(f"{fmt_huf(right_value)} Ft")
        val2.setObjectName("monthInfoValue")
        val2.setProperty("positive", right_value >= 0)
    

        val1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val2.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        grid.addWidget(lbl1, 0, 0)
        grid.addWidget(val1, 0, 1)
        grid.addWidget(lbl2, 0, 2)
        grid.addWidget(val2, 0, 3)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 1)

        return row


    def _make_single_value_row(self, label: str, value: float) -> QFrame:
        row = QFrame()
        row.setObjectName("monthInfoRow")

        layout = QGridLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("monthInfoLabel")
        

        val = QLabel(f"{fmt_huf(value)} Ft")
        val.setObjectName("monthInfoValue")
        val.setProperty("positive", value >= 0)
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(lbl, 0, 0)
        layout.addWidget(val, 0, 1)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 1)

        return row


    def _make_month_card(self, row: HomeSummaryRow) -> QFrame:
        card = QFrame()
        card.setObjectName("monthSummaryCard")
        card.setProperty("hoverable", True)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(200)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(row.month_label)
        title.setObjectName("monthCardTitle")
        layout.addWidget(title)

       

       
        card = QFrame()
        card.setObjectName("monthSummaryCard")
        card.setProperty("hoverable", True)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(200)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(row.month_label)
        title.setObjectName("monthCardTitle")
        layout.addWidget(title)

        divider = QFrame()
        divider.setObjectName("monthCardDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)


        has_data = any([
            row.actual_income != 0,
            row.actual_expense != 0,
            row.actual_savings != 0,
        ])

        if not has_data:
            empty_label = QLabel("Ehhez a hónaphoz még nincs rögzített adat.")
            empty_label.setObjectName("monthCardEmptyText")
            empty_label.setWordWrap(True)
            layout.addWidget(empty_label)
            layout.addStretch()
            card.mousePressEvent = lambda event: self._open_month_details(event, row)
            return card



        max_value = max(
            abs(row.actual_income),
            abs(row.actual_expense),
            abs(row.actual_savings),
            1.0,  # nullával osztás ellen
        )

        income_ratio = abs(row.actual_income) / max_value
        expense_ratio = abs(row.actual_expense) / max_value
        savings_ratio = abs(row.actual_savings) / max_value

        layout.addWidget(
            self._make_card_value_row(
                "Valós bevétel",
                row.actual_income,
                "income",
                income_ratio,
            )
        )

        layout.addWidget(
            self._make_card_value_row(
                "Valós kiadás",
                row.actual_expense,
                "expense",
                expense_ratio,
            )
        )

        layout.addWidget(
            self._make_card_value_row(
                "Megtakarítás",
                row.actual_savings,
                "savings",
                savings_ratio,
            )
        )

        layout.addStretch()

        card.mousePressEvent = lambda event: self._open_month_details(event, row)

        return card

        


    def _make_card_value_row(
            self, 
            label_text: str, 
            value: float, 
            row_type: str,
            fill_ratio: float,
    ) -> QWidget:
        
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # --- felső sor: label + érték ---
        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setObjectName("monthCardRowLabel")

        value_label = QLabel(f"{value:,.0f} Ft".replace(",", " "))
        value_label.setObjectName("monthCardRowValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setProperty("rowType", row_type)

        top_layout.addWidget(label)
        top_layout.addStretch(1)
        top_layout.addWidget(value_label)

        # --- alsó sor: MINI BAR ---
        bar_bg = QFrame()
        bar_bg.setObjectName("miniBarBg")

        bar_layout = QHBoxLayout(bar_bg)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        bar_fill = QFrame()
        bar_fill.setObjectName("miniBarFill")
        bar_fill.setProperty("rowType", row_type)

        # 👉 arányos szélesség:
        
        BAR_MAX_FILL = 80   # Meddig futhat ki a sáv
        BAR_TOTAL = 100     # teljes belső arányrendszer
                            # stretch: tényleges kitöltés
                            # rest: maradék hely

        stretch = max(1, int(fill_ratio * BAR_MAX_FILL)) if value > 0 else 0
        rest = max(0, BAR_TOTAL - stretch)

        bar_layout.addWidget(bar_fill, stretch)
        bar_layout.addStretch(rest)

        # --- összeépítés ---
        layout.addWidget(top_row)
        layout.addWidget(bar_bg)

        return row







    











  

    def set_year(self, year: int) -> None:
        self._year = int(year)
        self.reload()

    
    
    
    
    
    def reload(self) -> None:
        self._updating = True
        try:
            rows = self._build_summary_rows()
            self._render_dev_rows(rows)

            year = getattr(self, "_year", None)
            cash, bank, sec, metal, total = self.ctx.db.get_dashboard_balances(year=year)

            self.summary.set_balances(
                cash_balance=cash,
                bank_balance=bank,
                securities_balance=sec,
                metal_balance=metal,
            )
        finally:
            self._updating = False


   

    # DEV mód:
    def _render_dev_rows(self, rows: list[HomeSummaryRow]) -> None:
        
        # LOG:
        if self.log:
            self.log.d("HOME DEV render rows:", len(rows))



        if self.cards_container is None:
            return

        layout = self.cards_container.layout()
        if layout is None:
            return

        self._clear_layout(layout)

        outer_card = QFrame()
        outer_card.setObjectName("homeTableCard")
        outer_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        outer_layout = QVBoxLayout(outer_card)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(12)

        title = QLabel("Havi összesítő")
        title.setObjectName("sectionTitle")
        outer_layout.addWidget(title)

        rows_host = QWidget()
        rows_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        rows_layout = QVBoxLayout(rows_host)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(12)
        rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for i in range(0, len(rows), 2):
            row_wrap = QWidget()
            row_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            row_layout = QHBoxLayout(row_wrap)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            left_card = self._make_month_card(rows[i])
            row_layout.addWidget(left_card, 1)

            if i + 1 < len(rows):
                right_card = self._make_month_card(rows[i + 1])
                row_layout.addWidget(right_card, 1)
            else:
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                row_layout.addWidget(spacer, 1)

            row_wrap.setMinimumHeight(210)   # vagy 220
            rows_layout.addWidget(row_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True) 
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(rows_host)

        outer_layout.addWidget(scroll, 1)


        layout.addWidget(outer_card, 1)

        if self.log:
            self.log.d("HOME DEV: cards added")





    def _open_month_details(self, event, row: HomeSummaryRow) -> None:
        if event.button() == Qt.LeftButton:
            dlg = MonthDetailsDialog(row, self)
            dlg.exec()



    def open_table_dialog(self):
        dlg = HomeTableDialog(self.ctx, self)
        dlg.exec()