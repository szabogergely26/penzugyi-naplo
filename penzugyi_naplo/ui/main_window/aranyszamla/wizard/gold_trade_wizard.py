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

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QButtonGroup,
   
    QDateEdit,
    
    QDoubleSpinBox,
   
    QLabel,
 
    
    QHBoxLayout,
    QVBoxLayout,
    QWizard,
    QWizardPage,
   
    QFrame,
    QWidget,
    QRadioButton,
    QTextEdit,
)

from penzugyi_naplo.db.gold_database import add_gold_transaction


# közös két-oszlopos oldalhelper:

def create_gold_wizard_page_layout(
    page: QWizardPage,
    icon_text: str,
    title: str,
    subtitle: str,
) -> tuple[QVBoxLayout, QLabel, QLabel]:
    
    """
    Egységes kétoszlopos Aranyszámla-varázsló oldal.

    Bal oldal:
    - későbbi kép / illusztráció helye

    Jobb oldal:
    - az adott oldal tényleges tartalma
    """

    root_layout = QHBoxLayout(page)
    root_layout.setContentsMargins(18, 18, 18, 18)
    root_layout.setSpacing(20)

    image_panel = QFrame()
    image_panel.setObjectName("goldWizardImagePanel")
    image_panel.setMinimumWidth(230)
    image_panel.setMaximumWidth(280)

    image_layout = QVBoxLayout(image_panel)
    image_layout.setContentsMargins(20, 20, 20, 20)
    image_layout.setSpacing(12)

    icon_label = QLabel(icon_text)
    icon_label.setObjectName("goldWizardImagePlaceholder")
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    title_label = QLabel(title)
    title_label.setObjectName("goldWizardImageTitle")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setWordWrap(True)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("goldWizardImageSubtitle")
    subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle_label.setWordWrap(True)

    image_layout.addStretch(1)
    image_layout.addWidget(icon_label)
    image_layout.addWidget(title_label)
    image_layout.addWidget(subtitle_label)
    image_layout.addStretch(1)

    content_panel = QWidget()
    content_panel.setObjectName("goldWizardContentPanel")

    content_layout = QVBoxLayout(content_panel)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.setSpacing(12)

    root_layout.addWidget(image_panel)
    root_layout.addWidget(content_panel, 1)

    return content_layout, title_label, subtitle_label






class GoldTradeWizard(QWizard):
    """Arany vétel / eladás rögzítő varázsló."""

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)

        self.db_path = db_path

        self.setWindowTitle("Aranyszámla művelet rögzítése")
        self.setMinimumWidth(860)
        self.setMinimumHeight(580)
        self.setObjectName("goldTradeWizard")

        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

        self.addPage(GoldTradeTypePage(self))
        self.addPage(GoldTradeDataPage(self))
        self.addPage(GoldTradeNotePage(self))

        self.setButtonText(QWizard.WizardButton.BackButton, "Vissza")
        self.setButtonText(QWizard.WizardButton.NextButton, "Tovább")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Mentés")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Mégse")



    def accept(self) -> None:
        """
        Aranyszámla művelet mentése a varázsló befejezésekor.
        """

        is_buy = bool(self.field("trade_type_buy"))
        is_product_purchase = bool(self.field("trade_type_product_purchase"))

        trade_type = "buy" if is_buy else "sell"

        trade_date = self.field("trade_date").toString("yyyy-MM-dd")
        grams = float(self.field("grams") or 0)
        unit_price_huf = float(self.field("unit_price_huf") or 0)
        total_huf = int(float(self.field("total_huf") or 0))
        note = str(self.field("note") or "").strip()

        if is_product_purchase:
            if note:
                note = f"Termékvásárlás: {note}"
            else:
                note = "Termékvásárlás"




        print("GOLD WIZARD SAVE DEBUG")
        print("trade_type:", trade_type)
        print("trade_date:", trade_date)
        print("grams:", grams)
        print("unit_price_huf:", unit_price_huf)
        print("total_huf:", total_huf)
        print("note:", note)





        add_gold_transaction(
            self.db_path,
            trade_date=trade_date,
            trade_type=trade_type,
            grams=grams,
            unit_price_huf=unit_price_huf,
            total_huf=total_huf,
            note=note,
        )

        super().accept()









class GoldTradeTypePage(QWizardPage):
    """Aranyszámla művelet típusának kiválasztása."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Tranzakció típusa")
        self.setSubTitle(
            "Válaszd ki, milyen aranyszámla műveletet szeretnél rögzíteni."
        )

        layout, self.side_title_label, self.side_subtitle_label = create_gold_wizard_page_layout(
            self,
            "🪙",
            "Tranzakció típusa",
            "Első lépésként válaszd ki a művelet fajtáját.",
        )

        label = QLabel("Milyen műveletet szeretnél rögzíteni?")
        label.setObjectName("goldWizardFieldLabel")

        self.buy_radio = QRadioButton(
            "Vétel\n"
            "    Arany vásárlás, ami aranyszámlára kerül."
        )

        self.sell_radio = QRadioButton(
            "Eladás\n"
            "    Arany eladása aranyszámláról."
        )

        self.product_purchase_radio = QRadioButton(
            "Termék vásárlás\n"
            "    Aranyszámla megadott mennyiségéből termék vásárlása "
            "(pl.: aranylapka, aranyrúd).\n"
            "    Ez később hazaszállíttatható."
        )

        self.buy_radio.setChecked(True)

        self.trade_type_group = QButtonGroup(self)
        self.trade_type_group.addButton(self.buy_radio)
        self.trade_type_group.addButton(self.sell_radio)
        self.trade_type_group.addButton(self.product_purchase_radio)

        radio_layout = QVBoxLayout()
        radio_layout.setSpacing(14)
        radio_layout.addWidget(self.buy_radio)
        radio_layout.addWidget(self.sell_radio)
        radio_layout.addWidget(self.product_purchase_radio)

        hint = QLabel(
            "A termék vásárlás jelenleg az aranyszámla egyenlegét csökkentő "
            "műveletként kerül mentésre, külön megjegyzéssel jelölve."
        )
        hint.setObjectName("goldWizardHint")
        hint.setWordWrap(True)

        layout.addWidget(label)
        layout.addLayout(radio_layout)
        layout.addSpacing(12)
        layout.addWidget(hint)
        layout.addStretch(1)

        self.registerField("trade_type_buy", self.buy_radio)
        self.registerField("trade_type_sell", self.sell_radio)
        self.registerField("trade_type_product_purchase", self.product_purchase_radio)






























class GoldTradeDataPage(QWizardPage):
    """Arany vétel / eladás alapadatainak oldala."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Művelet adatai")
        self.setSubTitle("Add meg, hogy vételről vagy eladásról van szó, majd töltsd ki az összeget.")

        layout, self.side_title_label, self.side_subtitle_label = create_gold_wizard_page_layout(
            self,
            "🪙",
            "Arany művelet",
            "Vétel vagy eladás rögzítése az Aranyszámlához.",
        )

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy.MM.dd")
        self.date_edit.setDate(QDate.currentDate())

        self.grams_spin = QDoubleSpinBox()
        self.grams_spin.setDecimals(6)
        self.grams_spin.setMinimum(0.000001)
        self.grams_spin.setMaximum(999999.999999)
        self.grams_spin.setSingleStep(0.01)

        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setDecimals(0)
        self.unit_price_spin.setMinimum(0)
        self.unit_price_spin.setMaximum(999999999)
        self.unit_price_spin.setSuffix(" Ft/g")

        self.total_huf_spin = QDoubleSpinBox()
        self.total_huf_spin.setDecimals(0)
        self.total_huf_spin.setMinimum(0)
        self.total_huf_spin.setMaximum(999999999)
        self.total_huf_spin.setSuffix(" Ft")

        

        layout.addWidget(QLabel("Dátum"))
        layout.addWidget(self.date_edit)

        layout.addWidget(QLabel("Mennyiség"))
        layout.addWidget(self.grams_spin)

        layout.addWidget(QLabel("Egységár"))
        layout.addWidget(self.unit_price_spin)

        layout.addWidget(QLabel("Összeg"))
        layout.addWidget(self.total_huf_spin)

        layout.addStretch(1)

        
        self.registerField("trade_date", self.date_edit, "date")
        self.registerField("grams", self.grams_spin, "value")
        self.registerField("unit_price_huf", self.unit_price_spin, "value")
        self.registerField("total_huf", self.total_huf_spin, "value")



    def initializePage(self) -> None:
        """
        Az oldal címe a kiválasztott tranzakciótípus alapján frissül.
        """

        is_buy = bool(self.field("trade_type_buy"))
        is_product_purchase = bool(self.field("trade_type_product_purchase"))

        if is_buy:
            self.setTitle("Vétel adatai")
            self.setSubTitle("Add meg az aranyvétel dátumát, mennyiségét és összegét.")

            self.side_title_label.setText("Arany vétel")
            self.side_subtitle_label.setText(
                "Vásárlás rögzítése az Aranyszámlához."
            )

        elif is_product_purchase:
            self.setTitle("Termék vásárlás adatai")
            self.setSubTitle(
                "Add meg, mennyi aranyat szeretnél fizikai termékre váltani."
            )

            self.side_title_label.setText("Termék vásárlás")
            self.side_subtitle_label.setText(
                "Aranylapka, aranyrúd vagy más fizikai termék rögzítése."
            )

        else:
            self.setTitle("Eladás adatai")
            self.setSubTitle("Add meg az aranyeladás dátumát, mennyiségét és összegét.")

            self.side_title_label.setText("Arany eladás")
            self.side_subtitle_label.setText(
                "Eladás rögzítése az Aranyszámlához."
            )

        
        









class GoldTradeNotePage(QWizardPage):
    """Arany művelet megjegyzés és ellenőrzés oldala."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle("Megjegyzés")
        self.setSubTitle("Adj meg opcionális megjegyzést a művelethez.")

        layout, self.side_title_label, self.side_subtitle_label = create_gold_wizard_page_layout(
            self,
            "✅",
            "Ellenőrzés",
            "A művelet mentés előtt még átnézhető.",
        )

        note_label = QLabel("Megjegyzés")
        note_label.setObjectName("goldWizardFieldLabel")

        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Például: GoldTresor vétel, kártyás fizetés, díj levonva...")
        self.note_edit.setMinimumHeight(120)

        hint = QLabel(
            "A mentés után a művelet megjelenik az Aranyszámla kereskedési listájában."
        )
        hint.setObjectName("goldWizardHint")
        hint.setWordWrap(True)

        layout.addWidget(note_label)
        layout.addWidget(self.note_edit)
        layout.addWidget(hint)
        layout.addStretch(1)

        self.registerField("note", self.note_edit, "plainText")