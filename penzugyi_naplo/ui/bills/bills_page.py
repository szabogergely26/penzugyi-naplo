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
    QMessageBox,
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
        category_name: str = "",
        initially_expanded: bool = False,
        expanded_keys: set | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("billMonthRow")
        self.setProperty("paid", bool(items))

        self._kind = kind
        self._items = items
        self._month_number = month_number
        self._category_name = category_name
        self._expanded_keys = expanded_keys
        self._expanded = initially_expanded
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

        status_text, amount_text, is_multi_invoice = self._summarize(items, kind)

        status_label = QLabel(status_text)
        if is_multi_invoice:
            status_label.setObjectName("billMonthStatusMulti")
        else:
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

        # --- meta sor (kattintásra kinyíló extra adatok) ---
        # periodic: mindig van meta (Időszak, Összeg, Számla sorszám)
        # monthly: csak akkor, ha a tételeken tényleg van sorszám vagy fizetve infó
        #          (pl. KalászNet), különben nincs mit kinyitni
        self._meta_row = None

        if kind == "periodic":
            has_meta = bool(items)
        else:
            has_meta = bool(items) and (
                len(items) > 1
                or any(
                    _get_attr(it, "invoice_number", None) or _get_attr(it, "is_paid", False)
                    for it in items
                )
            )

        if has_meta:
            main_row.setCursor(Qt.CursorShape.PointingHandCursor)
            self._meta_row = self._build_meta_row(items, kind)
            self._meta_row.setVisible(self._expanded)
            self._chevron.setText("\u25b4" if self._expanded else "\u25be")
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

        if self._expanded_keys is not None:
            key = (self._category_name, self._month_number)
            if self._expanded:
                self._expanded_keys.add(key)
            else:
                self._expanded_keys.discard(key)



    def _build_meta_row(self, items: list, kind: str) -> QFrame:
        meta = QFrame()
        meta.setObjectName("billMonthMetaRow")

        lay = QVBoxLayout(meta)
        lay.setContentsMargins(14, 6, 14, 10)
        lay.setSpacing(6)

        # periodic típusnál, ha 2+ önálló (nem-korrekció) számla van a
        # hónapban, minden tétel elé "Számla N" alcím kerül, hogy egyértelmű
        # legyen a tagolás — korrekciós tételt nem számoljuk bele a sorszámba
        main_count = 0
        if kind == "periodic":
            main_items_count = len(
                [it for it in items if not _get_attr(it, "is_correction", False)]
            )
        else:
            main_items_count = 0

        for item in items:
            is_correction_item = bool(_get_attr(item, "is_correction", False))

            has_invoice_title = False
            if kind == "periodic" and main_items_count > 1 and not is_correction_item:
                main_count += 1

                title_row = QHBoxLayout()
                title_row.setSpacing(0)
                title_row.setContentsMargins(0, 0, 0, 0)

                title_indent = QWidget()
                title_indent.setFixedWidth(25)
                title_row.addWidget(title_indent)

                invoice_title = QLabel(f"Számla {main_count}")
                invoice_title.setObjectName("billMonthMetaInvoiceTitle")
                title_row.addWidget(invoice_title)
                title_row.addStretch(1)

                lay.addLayout(title_row)
                has_invoice_title = True

            line = QHBoxLayout()
            line.setSpacing(24)

            if has_invoice_title:
                indent_spacer = QWidget()
                indent_spacer.setFixedWidth(50)
                line.addWidget(indent_spacer)

           # periodic (pl. MVM Villany/Gáz): Időszak + Összeg + Sorszám
            if kind == "periodic":
                is_correction = bool(_get_attr(item, "is_correction", False))

                if is_correction:
                    correction_tag = QLabel("Korrekció/jóváírás")
                    correction_tag.setObjectName("billMonthMetaCorrectionTag")
                    line.addWidget(correction_tag)

                start = _get_attr(item, "start", "—")
                end = _get_attr(item, "end", "—")

                period_label = QLabel("Elszámolási időszak:")
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

                meter_m3 = _get_attr(item, "meter_m3", None)
                meter_mj = _get_attr(item, "meter_mj", None)
                if meter_m3 is not None or meter_mj is not None:
                    meter_label = QLabel("Fogyasztás:")
                    meter_label.setObjectName("billMonthMetaMeterLabel")
                    line.addWidget(meter_label)

                    if meter_m3 is not None and meter_mj is not None:
                        meter_text = f"{meter_m3:g} m³ ({meter_mj:g} MJ)"
                    elif meter_m3 is not None:
                        meter_text = f"{meter_m3:g} m³"
                    else:
                        meter_text = f"{meter_mj:g} MJ"

                    meter_value_widget = QLabel(meter_text)
                    meter_value_widget.setObjectName("billMonthMetaMeterValue")
                    line.addWidget(meter_value_widget)

            # monthly (pl. KalászNet): Összeg + Sorszám + Fizetve állapot
            # (Hónap a fő sorban van, de az összeg itt is kelleni fog,

            # mert egy hónapban több tétel is lehet, pl. korrekció)
            else:
                paid = bool(_get_attr(item, "is_paid", False))
                is_correction = bool(_get_attr(item, "is_correction", False))

                amount_value_raw = _get_attr(item, "amount", 0)

                amount_label = QLabel("Összeg:")
                amount_label.setObjectName("billMonthMetaAmountLabel")
                line.addWidget(amount_label)

                amount_value = QLabel(_format_huf(amount_value_raw))
                amount_value.setObjectName("billMonthMetaAmountValue")
                line.addWidget(amount_value)

                if is_correction:
                    correction_tag = QLabel("Korrekció/jóváírás")
                    correction_tag.setObjectName("billMonthMetaCorrectionTag")
                    line.addWidget(correction_tag)

                paid_label = QLabel("Állapot:")
                paid_label.setObjectName("billMonthMetaPaidLabel")
                line.addWidget(paid_label)

                paid_value = QLabel("Fizetve" if paid else "Nincs fizetve")
                paid_value.setObjectName(
                    "billMonthMetaPaidValueYes" if paid else "billMonthMetaPaidValueNo"
                )
                line.addWidget(paid_value)

            invoice_number = _get_attr(item, "invoice_number", None)

            invoice_label = QLabel("Számla sorszám:")
            invoice_label.setObjectName("billMonthMetaInvoiceLabel")
            line.addWidget(invoice_label)

            invoice_value = QLabel(str(invoice_number) if invoice_number else "—")
            invoice_value.setObjectName("billMonthMetaInvoiceValue")
            line.addWidget(invoice_value)

            # Szerkesztés / Törlés gombok (csak akkor, ha van entry_id)
            edit_btn = QPushButton("✎ Szerkesztés")
            edit_btn.setObjectName("billMonthMetaEditButton")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(
                lambda checked=False, it=item, k=kind: self._edit_bill_entry(it, k)
            )
            line.addWidget(edit_btn)

            delete_btn = QPushButton("🗑 Törlés")
            delete_btn.setObjectName("billMonthMetaDeleteButton")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(
                lambda checked=False, it=item: self._delete_bill_entry(it)
            )
            line.addWidget(delete_btn)

            line.addStretch(1)
            lay.addLayout(line)

        return meta

    def _edit_bill_entry(self, item, kind: str) -> None:
        entry_id = _get_attr(item, "entry_id", None)
        if entry_id is None:
            return

        from .invoice_edit_dialog import InvoiceEditDialog

        dlg = InvoiceEditDialog(
            entry_id=entry_id,
            current_date=_get_attr(item, "start", None) if kind == "periodic" else None,
            current_amount=_get_attr(item, "amount", 0) or 0,
            current_invoice_number=_get_attr(item, "invoice_number", None),
            current_is_correction=_get_attr(item, "is_correction", False),
            editable_date=(kind == "monthly"),
            parent=self,
            db=self._db,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_bills_page()


    def _delete_bill_entry(self, item) -> None:
        entry_id = _get_attr(item, "entry_id", None)
        if entry_id is None:
            return

        confirm = QMessageBox(self)
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setWindowTitle("Törlés megerősítése")
        confirm.setText("Biztos törölni akarod ezt a számlatételt?")
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.No)

        if confirm.exec() != QMessageBox.StandardButton.Yes:
            return

        if self._db is None:
            return

        ok = self._db.delete_transaction(entry_id)

        if not ok:
            QMessageBox.critical(
                self, "Hiba", "A törlés nem sikerült."
            )
            return

        self._reload_bills_page()

    def _reload_bills_page(self) -> None:
        widget = self.parent()
        while widget is not None and not hasattr(widget, "reload"):
            widget = widget.parent()

        if widget is not None:
            widget.reload()


    @staticmethod
    def _summarize(items: list, kind: str) -> tuple[str, str, bool]:
        """Visszaadja a fő sorban megjelenő státusz-szöveget, az összeget,
        és egy jelzőt (is_multi_invoice), hogy a szöveget ki kell-e emelni.

        A fősor összege csak a "rendes" (nem korrekció/jóváírás) tételekből áll —
        egy esetleges korrekciós tétel (pl. KalászNet túlfizetés visszaírása)
        csak a kibontott nézetben jelenik meg, a fősor összegét nem módosítja.
        Ha van korrekciós tétel is a hónapban, a státusz-szöveg jelzi ezt.

        periodic (pl. MVM) esetén más a helyzet: ott előfordulhat, hogy egy
        hónapban KÉT ÖNÁLLÓ, egymástól független számla esik (eltérő díjjal,
        eltérő fizetési határidővel) — ez nem korrekció, hanem két egyenrangú
        tétel. Ilyenkor a "N külön számla" szöveg jelenik meg, kiemelve
        (is_multi_invoice=True), hogy a felhasználó biztosan rákattintson és
        lássa mindkettőt, mert az összesített összeg félrevezető lehet.
        """

        if not items:
            return "Nincs még kiállítva", "—", False

        main_items = [it for it in items if not _get_attr(it, "is_correction", False)]
        correction_items = [it for it in items if _get_attr(it, "is_correction", False)]

        # A fősor összege csak a rendes tételekből áll. Ha valamiért csak
        # korrekciós tétel volna a hónapban (nem várt eset), essünk vissza
        # az összes tételre, hogy legalább lássunk valamit.
        total_source = main_items or items
        total = sum(float(_get_attr(it, "amount", 0) or 0) for it in total_source)
        amount_text = _format_huf(total)

        has_correction = bool(correction_items)

        if kind == "monthly":
            status = "Fizetve"
            if has_correction:
                status += f" (+{len(correction_items)} tétel)"
            return status, amount_text, False

        # periodic (MVM Villany/Gáz): 2+ önálló számla egy hónapban
        if len(main_items) > 1:
            status = f"{len(main_items)} külön számla"
            if has_correction:
                status += f" (+{len(correction_items)} tétel)"
            return status, amount_text, True

        dates = [
            _get_payment_date(it)
            for it in items
            if _get_payment_date(it) != "—"
        ]
        if dates:
            status = f"Fizetve {dates[0]}"
            if has_correction:
                status += f" (+{len(correction_items)} tétel)"
            return status, amount_text, False

        status = "Fizetve"
        if has_correction:
            status += f" (+{len(correction_items)} tétel)"
        return status, amount_text, False


class WideBillCard(QFrame):
    """Egy teljes számla széles, vízszintes kártyája."""

    clicked = Signal(int)

    def __init__(
            self, 
            model: BillCardModel, 
            parent: QWidget | None = None, 
            db=None, expanded_keys=None
        ) -> None:

        self._expanded_keys = expanded_keys if expanded_keys is not None else set()
        
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

            category_name = str(_get_attr(model, "name", ""))
            is_expanded = (category_name, month_number) in self._expanded_keys

            months_layout.addWidget(
                BillMonthRow(
                    month_number, items, self.kind,
                    db=self._db,
                    category_name=category_name,
                    initially_expanded=is_expanded,
                    expanded_keys=self._expanded_keys,
                )
            )

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
        self._expanded_keys: set[tuple[str, int]] = set()
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



    def set_expanded(self, category_name: str, month_number: int, expanded: bool) -> None:
        key = (category_name, month_number)
        if expanded:
            self._expanded_keys.add(key)
        else:
            self._expanded_keys.discard(key)

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
            card = WideBillCard(model, db=self.db, expanded_keys=self._expanded_keys)
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
                MonthlyAmount(
                    1, 7170, invoice_number="VG2026/270191", is_paid=True
                ),
                MonthlyAmount(
                    2, 7170, invoice_number="VG2026/270842", is_paid=True
                ),
                MonthlyAmount(
                    3, 7170, invoice_number="VG2026/271503", is_paid=True
                ),
                MonthlyAmount(
                    4,
                    7200 if year >= 2026 else 6900,
                    invoice_number="VG2026/272198",
                    is_paid=True,
                ),
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