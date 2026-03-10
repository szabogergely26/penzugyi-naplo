# - ui/bills/bills_page.py
# --------------------------

"""
Leírás a ui.bills.bills_page-hez:

# - Számlák oldal (BillsPage)
#
# - Fő felelősség:
#   - számla-kártyák megjelenítése (BillCard) görgethető, rugalmas elrendezésben
#   - év / all_years szűrés kezelése MainWindow felől
#
# - UI felépítés:
#   - QScrollArea + FlowLayout
#   - kártya alapú megjelenítés



    Számlák oldal a fő alkalmazásban.

    - Állapot:
        - _year / _all_years a MainWindow-tól érkezik

    - Folyamat:
        - set_filter() -> reload() -> _render()

    - Adatforrás:
        - jelenleg demó adatok
        - később DB: bills + bill_entries év szerint

    - Megjelenítés:
        - Interakció:
            - BillCard.clicked -> billRequested(bill_id)



    Adatforrás: jelenleg demó; később DB: bills + bill_entries év szerint.


"""


# ------ Importok -------

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from penzugyi_naplo.ui.bills.bill_card import BillCard
from penzugyi_naplo.ui.bills.bill_models import (
    BillCardModel,
    MonthlyAmount,
    PeriodicAmount,
)
from penzugyi_naplo.ui.shared.widgets.flow_layout import FlowLayout


class BillsPage(QWidget):
    billRequested = Signal(int)  # bill_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("billsPage")

        self._year: int | None = None
        self._all_years: bool = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("billsContainer")

        self.flow = FlowLayout(self.container, margin=14, spacing=12)
        self.container.setLayout(self.flow)

        self.scroll.setWidget(self.container)
        root.addWidget(self.scroll)

        self.reload()

    # --- MainWindow hívja ---
    def set_filter(self, *, year: int | None, all_years: bool) -> None:
        self._year = year
        self._all_years = all_years

    def reload(self) -> None:
        year = self._year or date.today().year
        
        use_demo_data = False
        if use_demo_data:
            models = self._load_demo_data_for_year(year)

        else:            
            models = self._load_models_from_db(year)

        self._render(models)

    # --- UI ---
    def _render(self, models: list[BillCardModel]) -> None:
        self._clear_cards()
        for m in models:
            card = BillCard(m)
            card.clicked.connect(self.billRequested.emit)
            self.flow.addWidget(card)

    def _clear_cards(self) -> None:
        while self.flow.count():
            it = self.flow.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    # --- DEMÓ: később DB-ből ---
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
            name="KalászNet (hónapos)",
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
            name="MVM – Villany (időszakos)",
            kind="periodic",
            periodic=[
                PeriodicAmount(f"{year}-01-01", f"{year}-02-01", 17170),
                PeriodicAmount(
                    f"{year}-02-01", f"{year}-03-01", 0
                ),  # 0 eset maradhat (— helyett itt Ft lesz; lásd lent)
                PeriodicAmount(f"{year}-03-01", f"{year}-04-01", 19880),
            ],
        )

        mvm_gaz = BillCardModel(
            id=4,
            name="MVM – Gáz (időszakos)",
            kind="periodic",
            periodic=[
                PeriodicAmount(f"{year}-01-15", f"{year}-03-15", 24110),
                PeriodicAmount(f"{year}-03-15", f"{year}-05-15", 0),
                PeriodicAmount(f"{year}-05-15", f"{year}-07-15", 26300),
            ],
        )

        return [telekom, kalasznet, mvm_villany, mvm_gaz]


    def _load_models_from_db(self, year: int) -> list[BillCardModel]:
        # TODO: később adatbázisból betöltés
        return []