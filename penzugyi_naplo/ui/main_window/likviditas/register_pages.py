# penzugyi_naplo/ui/main_window/likviditas/register_pages.py
"""
Likviditás oldalak regisztrálása a MainWindow számára.

Felelősség:
    - A Likviditás modulhoz tartozó oldalak létrehozása.
    - Az oldalak regisztrálása a MainWindow központi page_stack rendszerébe.
    - A BillsPage speciális signal bekötése.

Fontos:
    - A QStackedWidget kezelés továbbra is a MainWindow felelőssége.
    - Ez a modul csak azt mondja meg, milyen Likviditás oldalak léteznek.
"""

from __future__ import annotations

from penzugyi_naplo.ui.likviditas.pages.accounts_page import AccountsPage
from penzugyi_naplo.ui.bills.bills_page import BillsPage
from penzugyi_naplo.ui.shared.pages.coming_soon_page import ComingSoonPage
from penzugyi_naplo.ui.likviditas.pages.home_page import HomePage
from penzugyi_naplo.ui.likviditas.pages.statistics_page import StatisticsPage
from penzugyi_naplo.ui.likviditas.pages.transactions_page import TransactionsPage
from penzugyi_naplo.ui.likviditas.pages.settings_page import SettingsPage


def register_likviditas_pages(window) -> None:
    """
    Likviditás modul oldalainak létrehozása és regisztrálása.

    A window paraméter a MainWindow példány.
    Azért nem importáljuk típusosan a MainWindow-t, hogy ne hozzunk létre
    körkörös importot a főablak és a modulregisztráció között.
    """
    window.add_page("home", HomePage(window))
    window.add_page("transactions", TransactionsPage(window, db=window.db))

    # --- Statisztika ---
    if window.dev_mode:
        window.add_page("statistics", StatisticsPage(window.ctx, parent=window))
    else:
        window.add_page(
            "statistics",
            ComingSoonPage(
                title="Statisztika",
                msg="Diagrammok és kimutatások (fejlesztés alatt).",
            ),
        )

    window.add_page("settings", SettingsPage(window))

    # --- Számlák ---
    window.bills_page = BillsPage(window, db=window.db)
    window.bills_page.billRequested.connect(window.on_bill_requested)
    window.add_page("bills", window.bills_page)

    # --- Pénztárcák / egyenlegek (Accounts/Wallets) ---
    # Ez NEM a bills (kötelezők) oldal, hanem egyenleg/érték nyilvántartás.
    window.add_page("accounts", AccountsPage(window, db=window.db))