"""
Kezdőoldal felső összesítő panelje (HomePage → HomeSummaryPanel).

Aktív évhez tartozó gyors egyenleg/összeg kártyákat mutat (dashboard). A Tranzakciók táblázat nézet külön:
ui/pages/transactions_page.py (TransactionsPage, QTableWidget).
"""


# -- Importok ---

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# --- importok vége ----


def _money_fmt(value: Optional[float]) -> str:
    if value is None:
        return "—"
    # egyszerű HU formátum: ezres tagolás szóközzel
    s = f"{value:,.0f}".replace(",", " ")
    return f"{s} Ft"


class _Card(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("cardTitle")
        lay.addWidget(self.title_lbl)

        self.body = QWidget(self)
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(8)
        lay.addWidget(self.body)


class HomeSummaryPanel(QWidget):
    """
    Kezdőoldal felső dashboard blokk:
      - Fix (aktuális) bevételek: szerkeszthető, QSettings-ben tárolva
      - Egyenlegek: címke+érték (db-ből vagy settingsből frissíthető)
    """

    changed = Signal()  # ha a fix bevétel módosul, a home page rá tud frissíteni

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.settings = QSettings("NaplóPenzugy", "FinanceDiary")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        # -------- Bal: Fix bevételek --------
        self.card_fixed = _Card("Állandó (aktuális bevételek)", self)
        root.addWidget(self.card_fixed, 1)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(6)

        self.sp_family = self._make_money_spinbox("income_fixed/family_support")
        self.sp_rehab = self._make_money_spinbox("income_fixed/rehab")
        self.sp_salary = self._make_money_spinbox("income_fixed/salary")
        self.sp_szep = self._make_money_spinbox("income_fixed/szep_card")

        form.addRow("Családi támogatás:", self.sp_family)
        form.addRow("Rehabilitációs ellátás:", self.sp_rehab)
        form.addRow("Munkabér:", self.sp_salary)
        form.addRow("OTP Szép kártya:", self.sp_szep)

        self.btn_save = QPushButton("Mentés")
        self.btn_save.clicked.connect(self.save_fixed_incomes)

        w_form = QWidget()
        lay_form = QVBoxLayout(w_form)
        lay_form.setContentsMargins(0, 0, 0, 0)
        lay_form.setSpacing(8)
        lay_form.addLayout(form)

        # ---- Mentés sor + Összesen label ----
        self.lbl_income_sum = QLabel("Összesen: 0 Ft")
        self.lbl_income_sum.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        self.lbl_income_modified = QLabel("Utoljára módosítva: —")
        self.lbl_income_modified.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )

        row_save = QHBoxLayout()
        row_save.setContentsMargins(0, 0, 0, 0)
        row_save.setSpacing(10)
        row_save.addWidget(self.lbl_income_sum, 1)  # balra, kitölti a helyet
        row_save.addWidget(self.lbl_income_modified, 0)  # közép/jobb
        row_save.addWidget(self.btn_save, 0)  # jobbra

        lay_form.addLayout(row_save)

        self.card_fixed.body_lay.addWidget(w_form)

        # -------- Jobb: Egyenlegek --------
        self.card_bal = _Card("Számított értékek", self)
        root.addWidget(self.card_bal, 1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(8)
        grid.setContentsMargins(0, 0, 0, 0)

        # sorok
        self.lbl_bank = self._make_value_row(
            grid, 0, "Aktuális egyenleg (folyószámla):"
        )
        self.lbl_total = self._make_value_row(grid, 1, "Teljes egyenleg:", big=True)
        self.lbl_sec = self._make_value_row(grid, 2, "Értékpapírszámla:")
        self.lbl_metal = self._make_value_row(grid, 3, "Nemesfém egyenleg:")

        w_grid = QWidget()
        w_grid.setLayout(grid)
        self.card_bal.body_lay.addWidget(w_grid)

        self.load_fixed_incomes()

        self._update_income_sum_label()
        self._update_income_modified_label()

    def _format_huf_int(self, value: float) -> str:
        n = int(round(value))
        return f"{n:,}".replace(",", " ") + " Ft"

    def _update_income_sum_label(self) -> None:
        total = float(
            self.sp_family.value() + self.sp_rehab.value() + self.sp_salary.value()
        )
        self.lbl_income_sum.setText(f"Összesen: {self._format_huf_int(total)}")

    def _make_money_spinbox(self, key: str) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setDecimals(0)
        sp.setRange(0, 50_000_000)
        sp.setSingleStep(1000)
        sp.setGroupSeparatorShown(True)
        sp.setSuffix(" Ft")
        sp.setObjectName("moneySpin")
        sp.valueChanged.connect(lambda _v: self._on_any_change())
        sp.setProperty("settings_key", key)
        return sp

    def _make_value_row(
        self, grid: QGridLayout, row: int, label: str, big: bool = False
    ) -> QLabel:
        label_widget = QLabel(label)
        label_widget.setObjectName("sumLabelBig" if big else "sumLabel")
        v = QLabel("—")
        v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        v.setObjectName("sumValueBig" if big else "sumValue")

        grid.addWidget(label_widget, row, 0)
        grid.addWidget(v, row, 1)
        return v

    def _on_any_change(self) -> None:
        # opcionális auto-save később; most csak jelzünk
        self.changed.emit()

    # -------- Fix bevételek mentés/töltés --------
    def load_fixed_incomes(self) -> None:
        for sp in (self.sp_family, self.sp_rehab, self.sp_salary, self.sp_szep):
            key = sp.property("settings_key")
            sp.blockSignals(True)
            sp.setValue(float(self.settings.value(key, 0) or 0))
            sp.blockSignals(False)

    def save_fixed_incomes(self) -> None:
        for sp in (self.sp_family, self.sp_rehab, self.sp_salary, self.sp_szep):
            key = sp.property("settings_key")
            self.settings.setValue(key, int(sp.value()))

        now = datetime.now().strftime("%Y-%m-%d %H:%M")  # pl. 2026-02-15 09:12
        self.settings.setValue("income_fixed/last_modified", now)

        self.settings.sync()
        self.changed.emit()

        # Mentés után frissüljön
        self._update_income_sum_label()
        self._update_income_modified_label()

    def _update_income_modified_label(self) -> None:
        s = self.settings.value("income_fixed/last_modified", "")
        s = str(s).strip()
        self.lbl_income_modified.setText(f"Utoljára módosítva: {s if s else '—'}")

    def fixed_incomes_sum(self) -> float:
        return float(
            self.sp_family.value()
            + self.sp_rehab.value()
            + self.sp_salary.value()
            + self.sp_szep.value()
        )

    # -------- Egyenlegek frissítése kívülről --------
    def set_balances(
        self,
        bank_balance: Optional[float],
        securities_balance: Optional[float],
        metal_balance: Optional[float],
        cash_balance: Optional[float] = 0.0,
    ) -> None:
        self.lbl_bank.setText(_money_fmt(bank_balance))
        self.lbl_sec.setText(_money_fmt(securities_balance))
        self.lbl_metal.setText(_money_fmt(metal_balance))

        total = None
        if (
            bank_balance is not None
            and securities_balance is not None
            and metal_balance is not None
            and cash_balance is not None
        ):
            total = bank_balance + securities_balance + metal_balance + cash_balance
        self.lbl_total.setText(_money_fmt(total))
