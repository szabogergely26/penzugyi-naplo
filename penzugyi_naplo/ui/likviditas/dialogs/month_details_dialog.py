# - Fejlesztői -
#----------------------#


from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def format_huf(value: float) -> str:
    return f"{value:,.0f} Ft".replace(",", " ")


class ValueRow(QWidget):
    def __init__(self, label_text: str, value: float, positive: bool | None = None, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        label = QLabel(label_text)
        label.setObjectName("monthDetailsLabel")

        val = QLabel(format_huf(value))
        val.setObjectName("monthDetailsValue")

        if positive is not None:
            val.setProperty("positive", positive)
            val.setProperty("negative", not positive)

        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        val.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        layout.addWidget(label, 1)
        layout.addWidget(val, 0)


class SectionCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("monthDetailsSectionCard")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("monthDetailsSectionTitle")
        self._layout.addWidget(title_label)

    def add_row(self, label_text: str, value: float, positive: bool | None = None) -> None:
        self._layout.addWidget(ValueRow(label_text, value, positive))

    def add_stretch(self) -> None:
        self._layout.addStretch(1)


class TransactionListRow(QWidget):
    """
    Egyetlen sor a Gyorskeresés listájában: Dátum / Név / Összeg,
    egysoros elrendezésben. Nem QTableWidget/QTreeWidget-re épül,
    így a stílus szabadon, letisztultan formázható.

    Az oszlopszerkezet később bővíthető (pl. Kategória hozzáadása),
    mert minden mező külön QLabel-ként, saját object name-mel jön létre.
    """

    def __init__(self, tx_date: str, name: str, amount: float, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(12)

        date_label = QLabel(tx_date)
        date_label.setObjectName("quickSearchRowDate")
        date_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        name_label = QLabel(name or "—")
        name_label.setObjectName("quickSearchRowName")
        name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        amount_label = QLabel(format_huf(amount))
        amount_label.setObjectName("quickSearchRowAmount")
        amount_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        layout.addWidget(date_label, 0)
        layout.addWidget(name_label, 1)
        layout.addWidget(amount_label, 0)


class QuickSearchTab(QWidget):
    """
    "Gyorskeresés" fül: szegmentált gombsor (Bevétel / Kiadás / Számlabefizetés),
    a kiválasztott típus havi összege a fejlécben, alatta pedig egy letisztult,
    egysoros lista (Dátum / Név / Összeg) az adott típushoz tartozó tranzakciókról.

    A hónap maga nem szűrhető itt: a dialógus mindig egy adott (year, month)
    párra vonatkozik, ez a kontextusból adott.
    """

    KIND_LABELS = {
        "income": "Bevétel",
        "expense": "Kiadás",
        "bill": "Számlabefizetés",
    }

    def __init__(self, ctx, year: int, month: int, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.year = year
        self.month = month
        self.current_kind = "income"

        self._kind_buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # ---- szegmentált szűrősáv ----
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        for kind, label in self.KIND_LABELS.items():
            btn = QPushButton(label)
            btn.setObjectName("quickSearchFilterButton")
            btn.setCheckable(True)
            btn.setProperty("kind", kind)
            btn.clicked.connect(lambda _checked, k=kind: self._select_kind(k))
            self._kind_buttons[kind] = btn
            filter_bar.addWidget(btn)

        filter_bar.addStretch(1)
        root.addLayout(filter_bar)

        # ---- fejléc: kiválasztott típus + havi összeg ----
        header_card = QFrame()
        header_card.setObjectName("quickSearchHeaderCard")

        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(4)

        self.header_type_label = QLabel()
        self.header_type_label.setObjectName("quickSearchHeaderType")

        self.header_total_label = QLabel()
        self.header_total_label.setObjectName("quickSearchHeaderTotal")

        header_layout.addWidget(self.header_type_label)
        header_layout.addWidget(self.header_total_label)

        root.addWidget(header_card)

        # ---- elválasztó vonal ----
        divider = QFrame()
        divider.setObjectName("quickSearchDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(divider)

        # ---- lista terület ----
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(2)
        self.list_layout.addStretch(1)

        root.addWidget(self.list_container, 1)

        # Alapértelmezett kijelölés: Bevétel
        self._select_kind("income")

    def _select_kind(self, kind: str) -> None:
        self.current_kind = kind

        for btn_kind, btn in self._kind_buttons.items():
            btn.setChecked(btn_kind == kind)

        self._refresh_list()

    def _refresh_list(self) -> None:
        # Régi sorok eltávolítása (a végén lévő stretch kivételével)
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        rows = self.ctx.db.get_month_transactions_by_type(
            year=self.year, month=self.month, kind=self.current_kind
        )

        total = sum(float(r["amount"] or 0) for r in rows)

        self.header_type_label.setText(self.KIND_LABELS[self.current_kind])
        self.header_total_label.setText(format_huf(total))

        if not rows:
            empty_label = QLabel("Nincs tranzakció ebben a hónapban")
            empty_label.setObjectName("quickSearchEmptyLabel")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty_label)
            return

        for row in rows:
            row_widget = TransactionListRow(
                tx_date=str(row["tx_date"]),
                name=str(row["name"] or ""),
                amount=float(row["amount"] or 0),
            )
            self.list_layout.insertWidget(self.list_layout.count() - 1, row_widget)


class MonthDetailsDialog(QDialog):
    def __init__(self, row, ctx, parent=None):
        """
        row: a meglévő HomeSummaryRow objektumod.
        ctx: AppContext, a DB-elérés miatt kell a Gyorskereséshez.
        A mezőneveket lent igazítsd a saját dataclass-hoz, ha kell.
        """
        super().__init__(parent)
        self.row = row
        self.ctx = ctx

        self.setWindowTitle(f"Havi részletek – {row.month_label}")
        self.setModal(True)
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # ---- fülek: Áttekintés / Gyorskeresés ----
        self.tabs = QTabWidget()
        self.tabs.setObjectName("monthDetailsTabs")

        self.overview_tab = self._build_overview_tab(row)
        self.quick_search_tab = QuickSearchTab(ctx=self.ctx, year=row.year, month=row.month)

        self.tabs.addTab(self.overview_tab, "Áttekintés")
        self.tabs.addTab(self.quick_search_tab, "Gyorskeresés")

        root.addWidget(self.tabs, 1)

        # - Bezárás gomb:
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)

        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("Bezárás")

        buttons.rejected.connect(self.reject)

        root.addWidget(buttons)

    def _build_overview_tab(self, row) -> QWidget:
        """
        A korábbi, egyetlen nézetből álló tartalom (fejléc + 2x2 kártya),
        most az "Áttekintés" fülként, változatlan logikával.
        """
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # ---- fejléc ----
        header = QFrame()
        header.setObjectName("monthDetailsHeader")

        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 14, 14, 14)
        header_layout.setSpacing(6)

        title = QLabel(f"{row.month_label} – Havi összesítő")
        title.setObjectName("monthDetailsTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Tervezett és valós havi pénzmozgások")
        subtitle.setObjectName("monthDetailsSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # ---- 2 oszlopos tartalom ----
        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        planned_card = SectionCard("Tervezett értékek")
        actual_card = SectionCard("Valós értékek")
        balance_card = SectionCard("Eredmény")
        info_card = SectionCard("Összegzés")

        # Ezeket a mezőneveket igazítsd, ha nálad más a HomeSummaryRow
        planned_card.add_row("Tervezett bevétel", row.planned_income, True)
        planned_card.add_row("Tervezett kiadás", row.planned_expense, False)
        planned_card.add_row(
            "Tervezett megtakarítás", row.planned_savings, row.planned_savings >= 0
        )

        actual_card.add_row("Valós bevétel", row.actual_income, True)
        actual_card.add_row("Valós kiadás", row.actual_expense, False)
        actual_card.add_row("Valós megtakarítás", row.actual_savings, row.actual_savings >= 0)

        income_diff = row.actual_income - row.planned_income
        expense_diff = row.actual_expense - row.planned_expense
        saving_diff = row.actual_savings - row.planned_savings

        balance_card.add_row("Bevétel eltérés", income_diff, income_diff >= 0)
        # kiadásnál a kisebb a jobb, ezért fordított logika
        balance_card.add_row("Kiadás eltérés", expense_diff, expense_diff <= 0)
        balance_card.add_row("Megtakarítás eltérés", saving_diff, saving_diff >= 0)

        actual_net = row.actual_income - row.actual_expense
        planned_net = row.planned_income - row.planned_expense
        net_diff = actual_net - planned_net

        info_card.add_row("Hó nettó eredménye", actual_net, actual_net >= 0)
        info_card.add_row("Tervezett nettó", planned_net, planned_net >= 0)
        info_card.add_row("Teljes eltérés", net_diff, net_diff >= 0)

        grid.addWidget(planned_card, 0, 0)
        grid.addWidget(actual_card, 0, 1)
        grid.addWidget(balance_card, 1, 0)
        grid.addWidget(info_card, 1, 1)

        layout.addWidget(content, 1)

        return page