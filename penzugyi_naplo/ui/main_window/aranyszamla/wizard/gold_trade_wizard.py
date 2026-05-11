# penzugyi_naplo/ui/main_window/aranyszamla/wizard/gold_trade_wizard.py
# ---------------------------------------------------------

"""
Aranyszámla Vétel / Eladás wizard.

Feladata:
- arany vétel vagy eladás adatainak bekérése
- alap validáció
- mentés a gold_transactions táblába
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from penzugyi_naplo.db.gold_database import add_gold_transaction


class GoldTradeWizard(QDialog):
    """Arany vétel / eladás rögzítő ablak."""

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)

        self.db_path = db_path

        self.setWindowTitle("Aranyszámla művelet rögzítése")
        self.setMinimumWidth(460)
        self.setObjectName("goldTradeWizard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Arany vétel / eladás")
        title.setObjectName("goldTradeWizardTitle")

        subtitle = QLabel("Rögzítsd az aranyszámla művelet alapadatait.")
        subtitle.setObjectName("goldTradeWizardSubtitle")
        subtitle.setWordWrap(True)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.trade_type_combo = QComboBox()
        self.trade_type_combo.addItem("Vétel", "buy")
        self.trade_type_combo.addItem("Eladás", "sell")

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(date.today())

        self.grams_spin = QDoubleSpinBox()
        self.grams_spin.setDecimals(4)
        self.grams_spin.setRange(0.0001, 1_000_000.0)
        self.grams_spin.setSingleStep(0.1)
        self.grams_spin.setSuffix(" g")

        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setDecimals(2)
        self.unit_price_spin.setRange(0.0, 1_000_000_000.0)
        self.unit_price_spin.setSingleStep(100.0)
        self.unit_price_spin.setSuffix(" Ft/g")

        self.total_spin = QSpinBox()
        self.total_spin.setRange(0, 2_000_000_000)
        self.total_spin.setSingleStep(1000)
        self.total_spin.setSuffix(" Ft")

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Opcionális megjegyzés")

        form.addRow("Típus:", self.trade_type_combo)
        form.addRow("Dátum:", self.date_edit)
        form.addRow("Gramm:", self.grams_spin)
        form.addRow("Árfolyam:", self.unit_price_spin)
        form.addRow("Összeg:", self.total_spin)
        form.addRow("Megjegyzés:", self.note_edit)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("Mentés")
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Mégse")

        self.buttons.accepted.connect(self.save_trade)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def save_trade(self) -> None:
        """Validálja és elmenti az arany műveletet."""

        trade_type = self.trade_type_combo.currentData()
        trade_date = self.date_edit.date().toString("yyyy-MM-dd")
        grams = float(self.grams_spin.value())
        unit_price_huf = float(self.unit_price_spin.value())
        total_huf = int(self.total_spin.value())
        note = self.note_edit.text().strip()

        if grams <= 0:
            QMessageBox.warning(
                self,
                "Hiányzó adat",
                "Az arany mennyiségének nagyobbnak kell lennie nullánál.",
            )
            return

        if unit_price_huf <= 0 and total_huf <= 0:
            QMessageBox.warning(
                self,
                "Hiányzó adat",
                "Adj meg árfolyamot vagy teljes összeget.",
            )
            return

        if total_huf <= 0 and unit_price_huf > 0:
            total_huf = round(grams * unit_price_huf)

        if unit_price_huf <= 0 and total_huf > 0:
            unit_price_huf = total_huf / grams

        add_gold_transaction(
            db_path=self.db_path,
            trade_date=trade_date,
            trade_type=trade_type,
            grams=grams,
            unit_price_huf=unit_price_huf,
            total_huf=total_huf,
            note=note,
        )

        self.accept()