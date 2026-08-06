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
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QPushButton,
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


class BillMonthRow(QFrame):
    """
    Egy hónap tömör sora a számlakártyán belül.

    Alap állapotban: hónap | "Fizetve [dátum]" pipával | összeg — egy sorban.
    Kattintásra kinyílik alatta egy apró meta-sor (időszak, számla sorszám),
    csak 'periodic' típusnál, ahol van ilyen adat.

    Az 'esedékes' / 'lejárt' állapotok (sárga/piros) egyelőre nincsenek
    bekötve, mert a fizetési határidő adat még nincs a modellben — ez egy
    későbbi lépés. Most csak a ténylegesen fizetve tételeket jelenítjük meg.
    """

    def __init__(
        self,
        month_number: int,
        items: list[MonthlyAmount] | list[PeriodicAmount],
        kind: str,
        parent: QWidget | None = None,
        db=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("billMonthRow")
        self.setProperty("paid", bool(items))

        self._kind = kind
        self._items = items
        self._expanded = False
        self._db = db

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- fő sor (mindig látszik) ---
        main_row = QFrame()
        main_row.setObjectName("billMonthMainRow")

        row = QHBoxLayout(main_row)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        month_label = QLabel(MONTH_NAMES.get(month_number, str(month_number)))
        month_label.setObjectName("billMonthName")
        month_label.setFixedWidth(80)
        row.addWidget(month_label)

        status_text, amount_text = self._summarize(items, kind)

        status_label = QLabel(status_text)
        status_label.setObjectName(
            "billMonthStatus" if items else "billMonthStatusEmpty"
        )
        row.addWidget(status_label, stretch=1)

        amount_label = QLabel(amount_text)
        amount_label.setObjectName("billMonthAmount")
        amount_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(amount_label)

        self._chevron = QLabel("\u25be")  # lefelé mutató nyíl
        self._chevron.setObjectName("billMonthChevron")
        self._chevron.setFixedWidth(16)
        self._chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self._chevron)

        root.addWidget(main_row)

        # --- meta sor (csak periodic + van adat + kattintásra) ---
        self._meta_row = None
        has_meta = kind == "periodic" and bool(items)

        if has_meta:
            main_row.setCursor(Qt.CursorShape.PointingHandCursor)
            self._meta_row = self._build_meta_row(items)
            self._meta_row.setVisible(False)
            root.addWidget(self._meta_row)
            main_row.mousePressEvent = lambda e: self._toggle_expanded()
        else:
            self._chevron.setVisible(False)

    def _toggle_expanded(self) -> None:
        if self._meta_row is None:
            return

        self._expanded = not self._expanded
        self._meta_row.setVisible(self._expanded)
        self._chevron.setText("\u25b4" if self._expanded else "\u25be")

    def _build_meta_row(self, items: list) -> QFrame:
        meta = QFrame()
        meta.setObjectName("billMonthMetaRow")

        lay = QVBoxLayout(meta)
        lay.setContentsMargins(14, 6, 14, 10)
        lay.setSpacing(6)

        for item in items:
            line = QHBoxLayout()
            line.setSpacing(24)

            start = _get_attr(item, "start", "—")
            end = _get_attr(item, "end", "—")

            period_label = QLabel("Időszak:")
            period_label.setObjectName("billMonthMetaPeriodLabel")
            line.addWidget(period_label)

            period_value = QLabel(f"{start} – {end}")
            period_value.setObjectName("billMonthMetaPeriodValue")
            line.addWidget(period_value)

            amount_value_raw = _get_attr(item, "amount", 0)

            amount_label = QLabel("Összeg:")
            amount_label.setObjectName("billMonthMetaAmountLabel")
            line.addWidget(amount_label)

            amount_value = QLabel(_format_huf(amount_value_raw))
            amount_value.setObjectName("billMonthMetaAmountValue")
            line.addWidget(amount_value)

            invoice_number = _get_attr(item, "invoice_number", None)

            invoice_label = QLabel("Számla sorszám:")
            invoice_label.setObjectName("billMonthMetaInvoiceLabel")
            line.addWidget(invoice_label)

            invoice_value = QLabel(str(invoice_number))
            invoice_value.setObjectName("billMonthMetaInvoiceValue")
            line.addWidget(invoice_value)

            entry_id = _get_attr(item, "entry_id", None)

            edit_btn = QPushButton("✎ Szerkesztés")
            edit_btn.setObjectName("billMonthMetaEditButton")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(
                lambda checked=False, eid=entry_id, val=invoice_number, val_label=invoice_value: (
                    self._edit_invoice_number(eid, val, val_label)
                )
            )
            line.addWidget(edit_btn)

            line.addStretch(1)
            lay.addLayout(line)

        return meta

    def _edit_invoice_number(self, entry_id, current_value, value_label: QLabel) -> None:
        if entry_id is None:
            return

        from .invoice_edit_dialog import InvoiceEditDialog

        dlg = InvoiceEditDialog(
            entry_id=entry_id,
            current_invoice_number=current_value,
            parent=self,
            db=self._db,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_value = dlg.new_invoice_number
            value_label.setText(str(new_value) if new_value else "—")


    @staticmethod
    def _summarize(items: list, kind: str) -> tuple[str, str]:
        """Visszaadja a fő sorban megjelenő státusz-szöveget és az összeget."""

        if not items:
            return "Nincs még kiállítva", "—"

        total = sum(float(_get_attr(it, "amount", 0) or 0) for it in items)
        amount_text = _format_huf(total)

        if kind == "monthly":
            return "Fizetve", amount_text

        dates = [
            _get_payment_date(it)
            for it in items
            if _get_payment_date(it) != "—"
        ]
        if dates:
            return f"Fizetve {dates[0]}", amount_text

        return "Fizetve", amount_text


class WideBillCard(QFrame):
    """Egy teljes számla széles, vízszintes kártyája."""

    clicked = Signal(int)

    def __init__(self, model: BillCardModel, parent: QWidget | None = None, db=None) -> None:
        super().__init__(parent)
        self.setObjectName("billCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.model = model
        self.bill_id = int(_get_attr(model, "id", 0))
        self.kind = str(_get_attr(model, "kind", "monthly"))
        self._db = db

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

            months_layout.addWidget(BillMonthRow(month_number, items, self.kind, db=self._db))

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
            card = WideBillCard(model, db=self.db)
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