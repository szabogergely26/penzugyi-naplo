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


class MonthDetailsDialog(QDialog):
    def __init__(self, row, parent=None):
        """
        row: a meglévő HomeSummaryRow objektumod.
        A mezőneveket lent igazítsd a saját dataclass-hoz, ha kell.
        """
        super().__init__(parent)
        self.row = row

        self.setWindowTitle(f"Havi részletek – {row.month_label}")
        self.setModal(True)
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

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

        root.addWidget(header)

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
        planned_card.add_row("Tervezett megtakarítás", row.planned_savings, row.planned_savings >= 0)

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

        info_card.add_row("Hó nettó eredménye", row.actual_income - row.actual_expense, (row.actual_income - row.actual_expense) >= 0)
        info_card.add_row("Tervezett nettó", row.planned_income - row.planned_expense, (row.planned_income - row.planned_expense) >= 0)
        info_card.add_row("Teljes eltérés", (row.actual_income - row.actual_expense) - (row.planned_income - row.planned_expense),
                          ((row.actual_income - row.actual_expense) - (row.planned_income - row.planned_expense)) >= 0)

        grid.addWidget(planned_card, 0, 0)
        grid.addWidget(actual_card, 0, 1)
        grid.addWidget(balance_card, 1, 0)
        grid.addWidget(info_card, 1, 1)

        root.addWidget(content, 1)


        # - Bezárás gomb:
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)

        close_btn = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_btn is not None:
            close_btn.setText("Bezárás")

        buttons.rejected.connect(self.reject)
        
        root.addWidget(buttons)