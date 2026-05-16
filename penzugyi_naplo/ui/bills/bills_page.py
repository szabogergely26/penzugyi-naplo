# - ui/bills/bills_page.py
# --------------------------

"""
Számlák oldal.

Új elrendezési irány:
- a számlák egymás alatt, széles kártyákban jelennek meg
- egy számlán belül a hónapok egymás alatt vannak
- ha egy hónapban több befizetés van, azok egymás mellett jelennek meg
- havi számláknál nincs időszak mező
- időszakos számláknál van időszak + összeg
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.ui.bills.bill_models import (
    BillCardModel,
    MonthlyAmount,
    PeriodicAmount,
)


MONTH_NAMES = {
    1: "Január",
    2: "Február",
    3: "Március",
    4: "Április",
    5: "Május",
    6: "Június",
    7: "Július",
    8: "Augusztus",
    9: "Szeptember",
    10: "Október",
    11: "November",
    12: "December",
}


class MonthlyPaymentChip(QFrame):
    """Egyszerű havi számla befizetés-blokkja, például KalászNet."""

    def __init__(self, item: MonthlyAmount, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("billPaymentChip")
        
        # Ne nyúljon túl szélesre a fizetési blokk,
        # mert egy hónapon belül egymás mellett több ilyen is lehet.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(170)
        self.setMaximumWidth(230)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title = QLabel("Befizetés")
        title.setObjectName("billPaymentTitle")
        layout.addWidget(title)

        amount_label = QLabel("Összeg")
        amount_label.setObjectName("billPaymentMetaLabel")
        layout.addWidget(amount_label)

        amount_value = QLabel(_format_huf(_get_attr(item, "amount", 0)))
        amount_value.setObjectName("billPaymentAmount")
        layout.addWidget(amount_value)


class PeriodicPaymentChip(QFrame):
    """Időszakos számla befizetés-blokkja, például MVMNext."""

    def __init__(self, item: PeriodicAmount, index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("billPaymentChip")
        
        # Ne nyúljon túl szélesre a fizetési blokk,
        # mert egy hónapon belül egymás mellett több ilyen is lehet.
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(170)
        self.setMaximumWidth(230)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title = QLabel(f"{index}. fizetés")
        title.setObjectName("billPaymentTitle")
        layout.addWidget(title)


        # A hónapsor a fizetés/rögzítés hónapja alapján csoportosít.
        # Ezért a kártyán külön kiírjuk a fizetés/rögzítés dátumát is,
        # hogy ne keveredjen az elszámolási időszakkal.
        payment_date = _get_payment_date(item)

        payment_date_label = QLabel("Rögzítve / fizetve")
        payment_date_label.setObjectName("billPaymentMetaLabel")
        layout.addWidget(payment_date_label)

        payment_date_value = QLabel(payment_date)
        payment_date_value.setObjectName("billPaymentValue")
        layout.addWidget(payment_date_value)












        period_label = QLabel("Időszak")
        period_label.setObjectName("billPaymentMetaLabel")
        layout.addWidget(period_label)

        start = _get_attr(item, "start", "—")
        end = _get_attr(item, "end", "—")

        period_value = QLabel(f"{start} – {end}")
        period_value.setObjectName("billPaymentValue")
        layout.addWidget(period_value)

        amount_label = QLabel("Összeg")
        amount_label.setObjectName("billPaymentMetaLabel")
        layout.addWidget(amount_label)

        amount_value = QLabel(_format_huf(_get_attr(item, "amount", 0)))
        amount_value.setObjectName("billPaymentAmount")
        layout.addWidget(amount_value)

        invoice_number = _get_attr(item, "invoice_number", "")
        if invoice_number:
            invoice_label = QLabel(f"Számla sorszáma: {invoice_number}")
            invoice_label.setObjectName("billPaymentValue")
            layout.addWidget(invoice_label)


class BillMonthRow(QFrame):
    """Egy hónap sora a számlakártyán belül."""

    def __init__(
        self,
        month_number: int,
        items: list[MonthlyAmount] | list[PeriodicAmount],
        kind: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("billMonthRow")

        # Hónap sor:
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(12)

        month_label = QLabel(MONTH_NAMES.get(month_number, str(month_number)))
        month_label.setObjectName("billMonthName")
        month_label.setFixedWidth(130)
        month_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(month_label)

        payments_row = QHBoxLayout()
        payments_row.setContentsMargins(0, 0, 0, 0)
        payments_row.setSpacing(12)

        if not items:
            empty = QLabel("—")
            empty.setObjectName("billEmptyMonth")
            payments_row.addWidget(empty)
        else:
            for index, item in enumerate(items, start=1):
                if kind == "periodic":
                    payments_row.addWidget(PeriodicPaymentChip(item, index))
                else:
                    payments_row.addWidget(MonthlyPaymentChip(item))

        payments_row.addStretch(1)
        row.addLayout(payments_row, stretch=1)


class WideBillCard(QFrame):
    """Egy teljes számla széles, vízszintes kártyája."""

    clicked = Signal(int)

    def __init__(self, model: BillCardModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("billCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.model = model
        self.bill_id = int(_get_attr(model, "id", 0))
        self.kind = str(_get_attr(model, "kind", "monthly"))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("billCardHeader")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        icon = QLabel(_icon_for_model(model))
        icon.setObjectName("billCardIcon")
        icon.setFixedSize(28, 28)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon)

        title = QLabel(str(_get_attr(model, "name", "Számla")))
        title.setObjectName("billCardTitle")
        header_layout.addWidget(title)

        header_layout.addStretch(1)

        details_btn = QPushButton("Részletek")
        details_btn.setObjectName("billDetailsButton")
        details_btn.clicked.connect(self._open_details)
        header_layout.addWidget(details_btn)

        root.addWidget(header)

        months_container = QWidget()
        months_layout = QVBoxLayout(months_container)
        months_layout.setContentsMargins(0, 0, 0, 0)
        months_layout.setSpacing(0)

        # A tételeket hónap szerint csoportosítjuk.
        grouped = self._group_items_by_month(model)

        # Első körben csak azokat a hónapokat jelenítjük meg,
        # ahol ténylegesen van rögzített adat.
        # Így nem lesz tele a kártya üres, nagy sorokkal.
        for month_number in sorted(grouped):
            items = grouped.get(month_number, [])

            if not items:
                continue

            months_layout.addWidget(BillMonthRow(month_number, items, self.kind))

        root.addWidget(months_container)


    def _open_details(self) -> None:
        """
        Megnyitja a számla részletező ablakát a kártya saját modelljével.

        A dialog a BillCardModel alapján építi fel a táblázatot,
        ezért itt nem elég csak bill_id-t átadni.
        """
        from penzugyi_naplo.ui.bills.bill_details_dialog import BillDetailsDialog

        dlg = BillDetailsDialog(
            self.model,
            parent=self,
            db=getattr(self.window(), "db", None),
        )

        bills_page = self.parent()
        while bills_page is not None and not hasattr(bills_page, "reload"):
            bills_page = bills_page.parent()

        if bills_page is not None:
            dlg.billDeleted.connect(bills_page.reload)

        dlg.exec()




    def mouseDoubleClickEvent(self, event) -> None:
        """
        Duplakattintásra ugyanazt a részletező ablakot nyitjuk,
        mint a fejlécben lévő Részletek gombbal.

        Fontos:
        törlés után a BillsPage.reload() újraépítheti a kártyákat,
        ezért itt nem hívunk super().mouseDoubleClickEvent(event)-et
        a dialog bezárása után.
        """
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        event.accept()
        self._open_details()


    def _group_items_by_month(self, model: BillCardModel) -> dict[int, list]:
        if self.kind == "periodic":
            periodic_items = list(_get_attr(model, "periodic", []) or [])

            grouped: dict[int, list] = {}
            for item in periodic_items:
                month = _get_periodic_month(item)
                grouped.setdefault(month, []).append(item)

            return grouped

        monthly_items = list(_get_attr(model, "monthly", []) or [])

        grouped = {}
        for item in monthly_items:
            month = int(_get_attr(item, "month", 0) or 0)
            if month > 0:
                grouped.setdefault(month, []).append(item)

        return grouped


class BillsPage(QWidget):
    billRequested = Signal(int)

    def __init__(self, parent: QWidget | None = None, db=None) -> None:
        super().__init__(parent)
        self.setObjectName("billsPage")
        self.db = db

        self._year: int | None = None
        self._all_years: bool = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("billsContainer")

        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(14, 14, 14, 14)
        self.content_layout.setSpacing(12)

        self.header = QWidget(self.container)
        self.header.setObjectName("billsPageHeader")

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        self.page_title = QLabel("Számlák")
        self.page_title.setObjectName("billsPageTitle")
        header_layout.addWidget(self.page_title)

        header_layout.addStretch(1)

        self.year_label = QLabel("Aktív év: —")
        self.year_label.setObjectName("billsPageYearLabel")
        header_layout.addWidget(self.year_label)

        self.subtitle = QLabel("Éves számlák havi bontásban")
        self.subtitle.setObjectName("billsPageSubtitle")

        self.empty_state = QWidget(self.container)
        self.empty_state.setObjectName("billsEmptyState")

        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(10)

        title = QLabel("Számlák")
        title.setObjectName("billsEmptyTitle")

        subtitle = QLabel("Ehhez az évhez még nincs rögzített számla.")
        subtitle.setObjectName("billsEmptySubtitle")

        hint_row = QWidget()
        hint_layout = QHBoxLayout(hint_row)
        hint_layout.setContentsMargins(0, 0, 0, 0)
        hint_layout.setSpacing(6)

        bulb = QLabel("💡")
        bulb.setObjectName("billsEmptyBulb")
        bulb.setAlignment(Qt.AlignmentFlag.AlignTop)

        hint = QLabel("Tipp: Az első számla felvitele után itt jelennek meg a tételek.")
        hint.setObjectName("billsEmptyHint")
        hint.setWordWrap(True)

        hint_layout.addWidget(bulb, 0, Qt.AlignmentFlag.AlignTop)
        hint_layout.addWidget(hint, 1)

        empty_layout.addWidget(title)
        empty_layout.addWidget(subtitle)
        empty_layout.addWidget(hint_row)
        empty_layout.addStretch()

        self.cards_widget = QWidget(self.container)
        self.cards_widget.setObjectName("billsCardsWidget")

        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self.content_layout.addWidget(self.header)
        self.content_layout.addWidget(self.subtitle)
        self.content_layout.addWidget(self.empty_state)
        self.content_layout.addWidget(self.cards_widget)
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.container)
        root.addWidget(self.scroll_area)

        self.log = getattr(parent, "log", None)

        self.reload()

    def set_filter(self, *, year: int | None, all_years: bool) -> None:
        self._year = year
        self._all_years = all_years
        self.reload()

    def reload(self) -> None:
        year = self._year or date.today().year

        if self._all_years:
            self.year_label.setText("Aktív év: minden év")
        else:
            self.year_label.setText(f"Aktív év: {year}")

        models = self._load_models_from_db(year)

        if self.log is not None:
            self.log.d(f"BillsPage.reload source=db year={year} models={len(models)}")
        else:
            print(f"[BillsPage.reload] source=db year={year} models={len(models)}")

        self._render(models)

    def _render(self, models: list[BillCardModel]) -> None:
        self._clear_cards()

        has_models = len(models) > 0
        self.empty_state.setVisible(not has_models)
        self.cards_widget.setVisible(has_models)

        if not has_models:
            return

        for model in models:
            card = WideBillCard(model)
            card.clicked.connect(self.billRequested.emit)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch(1)

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def _load_demo_data_for_year(self, year: int) -> list[BillCardModel]:
        telekom = BillCardModel(
            id=1,
            name="Telekom",
            kind="monthly",
            monthly=[
                MonthlyAmount(1, 8990),
                MonthlyAmount(2, 8990),
                MonthlyAmount(3, 8990),
                MonthlyAmount(4, 9490 if year >= 2026 else 8990),
            ],
        )

        kalasznet = BillCardModel(
            id=2,
            name="KalászNet",
            kind="monthly",
            monthly=[
                MonthlyAmount(1, 6900),
                MonthlyAmount(2, 6900),
                MonthlyAmount(3, 6900),
                MonthlyAmount(4, 7200 if year >= 2026 else 6900),
            ],
        )

        mvm_villany = BillCardModel(
            id=3,
            name="MVMNext – Villany",
            kind="periodic",
            periodic=[
                PeriodicAmount(
                    month=4,
                    start=f"{year}-02-16",
                    end=f"{year}-03-15",
                    amount=4722,
                    invoice_number="AA12345678",
                    is_paid=True,
                ),
                PeriodicAmount(
                    month=4,
                    start=f"{year}-03-16",
                    end=f"{year}-04-15",
                    amount=4722,
                    invoice_number="AA12345679",
                    is_paid=True,
                ),
            ],
        )

        mvm_gaz = BillCardModel(
            id=4,
            name="MVMNext – Gáz",
            kind="periodic",
            periodic=[
                PeriodicAmount(
                    month=1,
                    start=f"{year}-01-15",
                    end=f"{year}-03-15",
                    amount=24110,
                ),
                PeriodicAmount(
                    month=5,
                    start=f"{year}-05-15",
                    end=f"{year}-07-15",
                    amount=26300,
                ),
            ],
        )

        return [mvm_villany, mvm_gaz, kalasznet, telekom]

    def _load_models_from_db(self, year: int) -> list[BillCardModel]:
        if self.db is None:
            return self._load_demo_data_for_year(year)

        return self.db.get_bill_card_models(year)







# Segédfüggvények:

def _format_huf(value: int | float | str | None) -> str:
    try:
        amount = int(float(value or 0))
    except (TypeError, ValueError):
        amount = 0

    return f"{amount:,} Ft".replace(",", " ")


def _get_attr(obj, name: str, default=None):
    return getattr(obj, name, default)


def _get_payment_date(item: PeriodicAmount) -> str:
    """Visszaadja a fizetés/rögzítés dátumát megjelenítéshez.

    Több lehetséges mezőnevet is megnézünk, mert a DB/model rétegben
    később lehet, hogy más néven érkezik ugyanaz az adat.
    """

    for attr_name in ("payment_date", "paid_at", "date", "created_at", "recorded_at"):
        value = _get_attr(item, attr_name, None)

        if value:
            return str(value)

    return "—"


def _get_periodic_month(item: PeriodicAmount) -> int:
    month = _get_attr(item, "month", None)

    if month:
        try:
            return int(month)
        except (TypeError, ValueError):
            pass

    start = str(_get_attr(item, "start", "") or "")

    try:
        return int(start[5:7])
    except (TypeError, ValueError):
        return 0


def _icon_for_model(model: BillCardModel) -> str:
    name = str(_get_attr(model, "name", "")).lower()
    kind = str(_get_attr(model, "kind", "monthly"))

    if "villany" in name:
        return "⚡"

    if "gáz" in name or "gaz" in name:
        return "🔥"

    if "internet" in name or "kalász" in name or "kalasz" in name:
        return "🌐"

    if "telekom" in name or "domino" in name:
        return "📱"

    if kind == "periodic":
        return "📄"

    return "💳"
