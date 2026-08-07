# penzugyi_naplo/ui/likviditas/wizard/wizard_pages_bill.py
# --------------------------------------------------------------
# Likviditás / Tranzakciórögzítő varázsló — számlabefizetés (bill) oldalak
# --------------------------------------------------------------

"""
A tranzakció-varázsló számlabefizetés (bill) ágához tartozó oldalak:

- PageBillProvider: szolgáltató választás (KalászNet / Telekom / MVMNext)
- PageBillMvmType: MVMNext esetén Villany / Gáz választás
- PageAmount: az összeg (és Villanynál minden bill-adat) rögzítése

A közös (nem-bill) oldalak a wizard_pages_common.py-ban vannak.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QWizardPage,
)

from penzugyi_naplo.core.utils import is_valid_date, parse_amount

from .wizard_helpers import bill_requires_period, create_transaction_wizard_page_layout


class PageBillProvider(QWizardPage):
    """
    Számlabefizetés oldal (Számlabefizetés ág): szolgáltató választás.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Számlabefizetés")
        self.setSubTitle("Válaszd ki a célszámlát / szolgáltatót.")

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "🧾",
            "Számlabefizetés",
            "Válaszd ki, melyik számlát vagy szolgáltatót fizeted be.",
        )

        label = QLabel("Célszámla / szolgáltató")
        label.setObjectName("transactionWizardSectionTitle")
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.addItems(
            [
                "Válassz szolgáltatót...",
                "KalászNet (Internet)",
                "Telekom",
                "MVMNext",
            ]
        )

        layout.addWidget(self.combo)

        hint = QLabel(
            "Az MVMNext választás után külön megadható, hogy villany vagy gáz számláról van szó."
        )
        hint.setObjectName("transactionWizardHint")
        hint.setWordWrap(True)

        layout.addSpacing(8)
        layout.addWidget(hint)
        layout.addStretch(1)

        self.registerField(
            "bill_provider*",
            self.combo,
            "currentText",
            self.combo.currentTextChanged,
        )

        self.combo.currentIndexChanged.connect(lambda _i: self.completeChanged.emit())

    def isComplete(self) -> bool:
        return self.combo.currentIndex() > 0

    def nextId(self) -> int:
        return 6 if self.combo.currentText() == "MVMNext" else 3


class PageBillMvmType(QWizardPage):
    """
    MVMNext oldal (csak MVMNext-nél): Villany / Gáz.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("MVMNext")
        self.setSubTitle("Válaszd ki: villany vagy gáz.")

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "⚡",
            "MVMNext",
            "Válaszd ki, hogy villany vagy gáz számlát rögzítesz.",
        )

        label = QLabel("Milyen MVMNext számlát fizetsz?")
        label.setObjectName("transactionWizardSectionTitle")
        layout.addWidget(label)

        self.rb_villany = QRadioButton("Villany")
        self.rb_gaz = QRadioButton("Gáz")

        self.rb_villany.setObjectName("transactionWizardRadio")
        self.rb_gaz.setObjectName("transactionWizardRadio")

        self.rb_villany.setChecked(True)

        self.group = QButtonGroup(self)
        self.group.addButton(self.rb_villany, 0)
        self.group.addButton(self.rb_gaz, 1)

        layout.addWidget(self.rb_villany)
        layout.addWidget(self.rb_gaz)
        layout.addStretch(1)

    def is_gas(self) -> bool:
        return self.rb_gaz.isChecked()

    def nextId(self) -> int:
        return 7 if self.is_gas() else 3


class PageAmount(QWizardPage):
    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Összeg Rögzítése")
        self.setSubTitle("Adja meg a tranzakció értékét (csak pozitív számot).")
        self.setFinalPage(True)

        layout, self.side_title_label, self.side_subtitle_label = create_transaction_wizard_page_layout(
            self,
            "💵",
            "Összeg rögzítése",
            "Add meg a tranzakció értékét.",
        )

        # ---- Bill mód mezők (alapesetben rejtve) ----

        self.lbl_date = QLabel("Elszámolt hónap dátuma (YYYY-MM-DD):")
        self.input_date = QLineEdit()
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))

        self.lbl_period_start = QLabel("Időszak kezdete (YYYY-MM-DD):")
        self.input_period_start = QLineEdit()
        self.input_period_start.setPlaceholderText("Pl.: 2025-03-15")

        self.lbl_period_end = QLabel("Időszak vége (YYYY-MM-DD):")
        self.input_period_end = QLineEdit()
        self.input_period_end.setPlaceholderText("Pl.: 2025-04-15")

        self.lbl_invoice_number = QLabel("Számla sorszáma:")
        self.input_invoice_number = QLineEdit()
        self.input_invoice_number.setPlaceholderText("Pl.: 1234567890")

        self.chk_is_correction = QCheckBox("Ez korrekció / jóváírás (nem önálló számla)")
        self.chk_is_correction.setObjectName("transactionWizardCorrectionCheckbox")

        layout.addWidget(self.lbl_invoice_number)
        layout.addWidget(self.input_invoice_number)
        layout.addWidget(self.chk_is_correction)

        layout.addWidget(self.lbl_date)
        layout.addWidget(self.input_date)
        layout.addWidget(self.lbl_period_start)
        layout.addWidget(self.input_period_start)
        layout.addWidget(self.lbl_period_end)
        layout.addWidget(self.input_period_end)

        # ---- közös mező ----

        self.input_amount = QLineEdit()
        self.input_amount.setPlaceholderText("Csak pozitív szám (pl. 20000)")

        layout.addWidget(QLabel("Összeg (HUF):"))
        layout.addWidget(self.input_amount)
        layout.addStretch()

    def initializePage(self) -> None:
        super().initializePage()

        wiz = self.wizard()
        mode = None
        provider = ""

        if (
            wiz is not None
            and wiz.page(0) is not None
            and hasattr(wiz.page(0), "get_type")
        ):
            mode = wiz.page(0).get_type()

        if wiz is not None:
            provider = (wiz.field("bill_provider") or "").strip()

        is_bill = mode == "bill"
        needs_period = is_bill and bill_requires_period(provider)

        if is_bill:
            self.setTitle("Számlabefizetés összege")
            self.setSubTitle("Add meg a fizetés dátumát és a befizetett összeget.")
            self.side_title_label.setText("Számla összege")
            self.side_subtitle_label.setText("A számlabefizetéshez tartozó összeg és dátum.")

        elif mode == "income":
            self.setTitle("Bevétel összege")
            self.setSubTitle("Add meg a bevétel összegét.")
            self.side_title_label.setText("Bevétel összege")
            self.side_subtitle_label.setText("A saját egyenleghez érkező pénz rögzítése.")

        else:
            self.setTitle("Kiadás összege")
            self.setSubTitle("Add meg a kiadás összegét.")
            self.side_title_label.setText("Kiadás összege")
            self.side_subtitle_label.setText("A kiadáshoz tartozó végösszeg rögzítése.")

        self.lbl_date.setVisible(is_bill)
        self.input_date.setVisible(is_bill)

        self.lbl_period_start.setVisible(needs_period)
        self.input_period_start.setVisible(needs_period)
        self.lbl_period_end.setVisible(needs_period)
        self.input_period_end.setVisible(needs_period)

        self.lbl_invoice_number.setVisible(is_bill)
        self.input_invoice_number.setVisible(is_bill)
        self.chk_is_correction.setVisible(is_bill)

        if is_bill:
            self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
            self.input_amount.clear()
            self.input_invoice_number.clear()
            self.chk_is_correction.setChecked(False)

            if needs_period:
                self.input_period_start.clear()
                self.input_period_end.clear()
            else:
                self.input_period_start.clear()
                self.input_period_end.clear()

    def reset_bill_fields(self) -> None:
        self.input_invoice_number.clear()
        self.chk_is_correction.setChecked(False)
        self.input_date.setText(datetime.now().strftime("%Y-%m-%d"))
        self.input_period_start.clear()
        self.input_period_end.clear()
        self.input_amount.clear()

    def validatePage(self) -> bool:
        wiz = self.wizard()
        mode = None
        provider = ""

        if (
            wiz is not None
            and wiz.page(0) is not None
            and hasattr(wiz.page(0), "get_type")
        ):
            mode = wiz.page(0).get_type()

        if wiz is not None:
            provider = (wiz.field("bill_provider") or "").strip()

        if mode == "bill":
            payment_date = is_valid_date(self.input_date.text().strip())
            if not payment_date:
                QMessageBox.warning(
                    self,
                    "Hiba",
                    "Érvénytelen fizetési dátum! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
                )
                return False

            if bill_requires_period(provider):
                period_start = is_valid_date(self.input_period_start.text().strip())
                if not period_start:
                    QMessageBox.warning(
                        self,
                        "Hiba",
                        "Érvénytelen időszak kezdete! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
                    )
                    return False

                period_end = is_valid_date(self.input_period_end.text().strip())
                if not period_end:
                    QMessageBox.warning(
                        self,
                        "Hiba",
                        "Érvénytelen időszak vége! Használj YYYY-M-D vagy YYYY-MM-DD formátumot.",
                    )
                    return False

                if period_start > period_end:
                    QMessageBox.warning(
                        self,
                        "Hiba",
                        "Az időszak kezdete nem lehet későbbi, mint az időszak vége.",
                    )
                    return False

        amount_str = self.input_amount.text().strip()
        try:
            loc = QLocale.system()
            gs = loc.groupSeparator()
            dp = loc.decimalPoint()

            amount = parse_amount(amount_str, group_sep=gs, decimal_point=dp)
            if amount <= 0:
                QMessageBox.warning(self, "Hiba", "Kérjük, adjon meg pozitív összeget.")
                return False

            return True
        except ValueError:
            QMessageBox.warning(
                self, "Hiba", "Érvénytelen összeg formátum. Csak számokat használjon."
            )
            return False

    def get_amount(self) -> float:
        amount_str = self.input_amount.text().strip()
        loc = QLocale.system()
        gs = loc.groupSeparator()
        dp = loc.decimalPoint()
        return abs(parse_amount(amount_str, group_sep=gs, decimal_point=dp))

    def get_bill_date_raw(self) -> str:
        return self.input_date.text().strip()

    def get_period_start_raw(self) -> str:
        return self.input_period_start.text().strip()

    def get_period_end_raw(self) -> str:
        return self.input_period_end.text().strip()

    def nextId(self) -> int:
        return -1

    def get_invoice_number_raw(self) -> str:
        return self.input_invoice_number.text().strip()

    def get_is_correction(self) -> bool:
        return self.chk_is_correction.isChecked()