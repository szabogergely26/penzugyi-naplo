# pénzügyi_napló/ui/main_window.py
# -----------------------------------

"""
Az alkalmazás fő vezérlő ablaka
(penzugyi_naplo/ui/main_window.py).

Architektúra szerep:
    - Globális UI felépítése
    - Oldalak regisztrálása és navigációja
    - Aktív év és oldal kezelése (AppState)
    - UI → oldal → DB koordináció

UI szerkezet:
    - Bal panel: YearTabsBar (ui/widgets/year_tabs_bar.py)
    - Felső navigáció: RibbonBar / NavBar
    - Oldalak: QStackedWidget

Oldalak:
    - Kezdőoldal: ui/pages/home_page.py
        → Havi összesítő táblázat itt található
    - Tranzakciók: ui/pages/transactions_page.py
        → Részletes tranzakciós tábla
    - Statisztika: ui/charts.py (ChartManager)
    - Számlák: ui/pages/bills_page.py
    - Beállítások: ui/pages/settings_page.py

Adatkapcsolat:
    - TransactionDatabase példány kezelése
    - DB reset esetén oldalak újrakötése
    - év-szűrés propagálása az oldalak felé

Fontos:
    - A MainWindow nem számol és nem SQL-ez.
    - Az oldalak saját logikájukat kezelik.
    - Ez a réteg csak koordinál.
"""


# --- Importok ---

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.bills.bills_page import BillsPage
from ui.pages.home_page import HomePage
from ui.pages.settings_page import SettingsPage
from ui.pages.statistics_page import StatisticsPage
from ui.pages.transactions_page import TransactionsPage
from ui.widgets.ribbon_bar import RibbonBar  # igazítsd az útvonalat
from ui.widgets.year_tabs_bar import YearTabsBar
from ui.wizard_transaction import TransactionWizard

# ------- Importok vége -------


# Ha nálad máshol van, igazítsd:
# from pénzügyi_napló.db.transaction_database import TransactionDatabase

if TYPE_CHECKING:
    from db.transaction_database import TransactionDatabase


@dataclass
class AppState:
    """Központi, egyszerű állapot a MainWindow-hoz (később bővíthető)."""

    active_year: int = 2026
    active_page_key: str = "home"
    # ide jöhetnek később: szűrők, nézetmód, keresés, stb.


class _SimpleNavBar(QFrame):
    pageRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QPushButton] = {}

        self.setObjectName("navBar")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        self._add_btn(lay, "home", "Kezdő")
        self._add_btn(lay, "transactions", "Tranzakciók")
        self._add_btn(lay, "statistics", "Statisztika")
        self._add_btn(lay, "bills", "Számlák")
        lay.addStretch(1)  # KICSI rugalmas hézag a Számlák után

        self._add_btn(lay, "settings", "Beállítások")
        lay.addStretch(10)  # NAGY rugalmas tér a Beállítások után

    def _add_btn(self, lay: QHBoxLayout, key: str, text: str) -> None:
        btn = QPushButton(text, self)
        btn.setCheckable(True)

        btn.setObjectName("navButton")

        if key == "settings":
            btn.setObjectName("navSettings")
            print("DEBUG settings objectName:", btn.objectName())

        btn.clicked.connect(lambda _=False, k=key: self.pageRequested.emit(k))
        lay.addWidget(btn)
        self._buttons[key] = btn

    def set_active(self, key: str) -> None:
        for k, b in self._buttons.items():
            b.setChecked(k == key)


class MainWindow(QMainWindow):
    """
    MainWindow váz:
    - csak konstruktor
    - legfontosabb attribútumok (db, state, pages registry, stacked, central root)
    """

    def __init__(
        self, db: "TransactionDatabase", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)

        # --- Core állapot ---
        self.db: "TransactionDatabase" = db
        self.state: AppState = AppState()
        self.pages: dict[str, QWidget] = {}

        # --- UI gyökér ---
        self._central = QWidget(self)
        self.setCentralWidget(self._central)

        # --- FŐ (bal + jobb) layout ---
        self._main_layout = QHBoxLayout(self._central)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # --- BAL PANEL ---
        self._left_panel = QWidget(self._central)
        self._left_panel.setFixedWidth(140)

        self._left_layout = QVBoxLayout(self._left_panel)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(10)
        self._left_layout.setAlignment(Qt.AlignTop)

        self._left_header_spacer = QWidget(self._left_panel)
        self._left_header_spacer.setFixedHeight(0)
        self._left_layout.addWidget(self._left_header_spacer)
        self._left_layout.addSpacing(12)

        # --- JOBB PANEL ---
        self._right_panel = QWidget(self._central)
        self._root_layout = QVBoxLayout(self._right_panel)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # --- Panelok a fő layouthoz ---
        self._main_layout.addWidget(self._left_panel, 0)
        self._main_layout.addWidget(self._right_panel, 1)

        # --- Actions + menü ---
        self._create_actions()
        self._build_menubar()

        # --- LEFT: Year tabs (EGYSZER) ---
        self.year_tabs = YearTabsBar(
            years=[2023, 2024, 2025, 2026], parent=self._left_panel
        )
        self._left_layout.addWidget(self.year_tabs)

        # --- RIGHT: ribbon + navbar + pages ---
        self._build_ribbon()
        self._root_layout.addWidget(self.ribbon)

        self._build_navbar()
        self._root_layout.addWidget(self.navbar)

        self._build_pages()
        self._root_layout.addWidget(self.page_stack, 1)

        # --- Signalok + kezdő állapot ---
        self._connect_core_signals()
        self._load_toolbar_mode()

        self.setWindowTitle("Pénzügyi Napló")
        self.setMinimumSize(1440, 900)

        # Initial state
        self.year_tabs.set_active_year(self.state.active_year, emit=False)
        self.set_active_year(self.state.active_year)
        self.set_page(self.state.active_page_key)

        self._sync_left_year_offset()

        QTimer.singleShot(0, self._sync_left_year_offset)

        self._filter_all_years = True
        self._filter_year = None

    def on_year_selected(self, year: int) -> None:
        self.set_active_year(int(year))  # állapot + oldalak év
        self._filter_all_years = False
        self._filter_year = int(year)
        self._apply_year_filter()

    def on_all_years(self) -> None:
        self._filter_all_years = True
        self._filter_year = None
        self._apply_year_filter()

    def _apply_year_filter(self) -> None:
        tx = self.pages.get("transactions")
        if tx and hasattr(tx, "set_filter"):
            tx.set_filter(year=self._filter_year, all_years=self._filter_all_years)
            if hasattr(tx, "reload"):
                tx.reload()

        st = self.pages.get("statistics")
        if st and hasattr(st, "set_filter"):
            st.set_filter(year=self._filter_year, all_years=self._filter_all_years)
            if hasattr(st, "reload"):
                st.reload()

        bills = self.pages.get("bills")
        if bills and hasattr(bills, "set_filter"):
            bills.set_filter(year=self._filter_year, all_years=self._filter_all_years)
            if hasattr(bills, "reload"):
                bills.reload()

    def _sync_left_year_offset(self) -> None:
        """Az év-sávot lejjebb tolja a jobb oldali fejléc (ribbon + navbar) alá."""
        h = 0

        if getattr(self, "ribbon", None) is not None and self.ribbon.isVisible():
            h += self.ribbon.height()  # valós magasság

        if getattr(self, "navbar", None) is not None and self.navbar.isVisible():
            h += self.navbar.height()  # valós magasság

        self._left_header_spacer.setFixedHeight(
            h + 16
        )  # +16: finom ráhagyás (igény szerint 12/20)

    # Oldalak regisztrálása
    # ---------------------------

    # (gerinc metódusok, hogy a konstruktor tiszta maradjon)

    def _register_core_pages(self) -> None:
        """
        Placeholder oldalak létrehozása.
        Később itt példányosítjuk a valódi page osztályokat.
        """
        self.add_page("home", HomePage(self))
        self.add_page("transactions", TransactionsPage(self, db=self.db))
        self.add_page("statistics", StatisticsPage(self))
        self.add_page("settings", SettingsPage(self))
        self.bills_page = BillsPage(self)
        self.bills_page.billRequested.connect(self.on_bill_requested)
        self.add_page("bills", self.bills_page)

    def _connect_core_signals(self) -> None:
        """
        Itt kötjük majd össze a topbar/sidebar/year tabs jelzéseket.
        Most szándékosan üres.
        """
        self.year_tabs.yearChanged.connect(self.on_year_selected)
        self.navbar.pageRequested.connect(self.set_page)

        return

    def add_page(self, key: str, page: QWidget) -> None:
        """Oldal regisztrálása a stackbe."""
        if key in self.pages:
            raise ValueError(f"Page already registered: {key}")

        self.pages[key] = page
        self.page_stack.addWidget(page)

    def set_page(self, key: str) -> None:
        """Aktív oldal váltása."""
        page = self.pages.get(key)
        if page is None:
            QMessageBox.warning(self, "Navigáció", f"Ismeretlen oldal: {key}")
            return

        self.state.active_page_key = key
        self.page_stack.setCurrentWidget(page)

        # Mindig frissítsünk, amikor oda váltunk (különösen indulás után)
        if key in ("transactions", "statistics"):
            if hasattr(page, "reload"):
                page.reload()

        # UI szinkron
        if hasattr(self, "navbar"):
            self.navbar.set_active(key)

        print(
            "SET_PAGE:",
            key,
            "index=",
            self.page_stack.currentIndex(),
            "widget=",
            type(self.page_stack.currentWidget()).__name__,
        )

    def set_active_year(self, year: int) -> None:
        self.state.active_year = int(year)

        # 1) minden page, ami tud year-t
        for page in self.pages.values():
            if hasattr(page, "set_year"):
                page.set_year(int(year))

        # 2) Tranzakciók oldal: erős év-szűrés
        tx = self.pages.get("transactions")
        if tx and hasattr(tx, "set_filter"):
            tx.set_filter(year=int(year), all_years=False)
            if hasattr(tx, "reload"):
                tx.reload()

    def _create_actions(self) -> None:
        self.act_exit = QAction("Kilépés", self)
        self.act_exit.triggered.connect(self.close)

        self.act_import = QAction("Import", self)
        self.act_import.triggered.connect(self.on_import)  # majd megírod

        self.act_export = QAction("Export", self)
        self.act_export.triggered.connect(self.on_export)  # majd megírod

        self.act_backup_db = QAction("Mentés (backup)…", self)
        self.act_backup_db.triggered.connect(self.on_backup_database)

        self.act_restore_db = QAction("Betöltés (restore)…", self)
        self.act_restore_db.triggered.connect(self.on_restore_database)

        self.act_new_tx = QAction("Új tranzakció", self)
        self.act_new_tx.triggered.connect(self.on_new_transaction)  # majd megírod

        self.act_toolbar_menubar = QAction("Menüsor mód", self, checkable=True)
        self.act_toolbar_ribbon = QAction("Szalag mód", self, checkable=True)

        self.act_toolbar_menubar.triggered.connect(
            lambda: self.set_toolbar_mode("menubar")
        )
        self.act_toolbar_ribbon.triggered.connect(
            lambda: self.set_toolbar_mode("ribbon")
        )

        self.toolbar_mode_group = QActionGroup(self)
        self.toolbar_mode_group.setExclusive(True)

        self.act_toolbar_menubar.setActionGroup(self.toolbar_mode_group)
        self.act_toolbar_ribbon.setActionGroup(self.toolbar_mode_group)

        self.act_reset_db = QAction("Adatbázis törlése…", self)
        self.act_reset_db.triggered.connect(self.on_reset_database)

    def _build_menubar(self) -> None:
        mb = self.menuBar()
        mb.clear()

        m_file = mb.addMenu("Fájl")
        m_file.addAction(self.act_new_tx)
        m_file.addSeparator()
        m_file.addAction(self.act_exit)

        m_data = mb.addMenu("Adatok")
        m_data.addAction(self.act_backup_db)
        m_data.addAction(self.act_restore_db)
        m_data.addSeparator()
        m_data.addAction(self.act_import)
        m_data.addAction(self.act_export)
        m_data.addSeparator()
        m_data.addAction(self.act_reset_db)

        m_view = mb.addMenu("Nézet")
        m_view.addAction(self.act_toolbar_menubar)
        m_view.addAction(self.act_toolbar_ribbon)

        m_help = mb.addMenu("Súgó")

        # később: névjegy, verzió, stb.

    def _build_ribbon(self) -> None:
        self.ribbon = RibbonBar(self)

        tab_home = self.ribbon.add_tab("Fő")
        self.ribbon.add_action_button(tab_home, self.act_new_tx)

        tab_data = self.ribbon.add_tab("Adatok")

        self.ribbon.add_action_button(tab_data, self.act_backup_db)
        self.ribbon.add_action_button(tab_data, self.act_restore_db)

        self.ribbon.add_separator(tab_data, spacing=12)

        self.ribbon.add_action_button(tab_data, self.act_import)
        self.ribbon.add_action_button(tab_data, self.act_export)

        # vizuális elválasztás
        self.ribbon.add_separator(tab_data, spacing=18)

        btn_delete = self.ribbon.add_action_button(tab_data, self.act_reset_db)
        btn_delete.setObjectName("dangerLiteButton")

        tab_app = self.ribbon.add_tab("Nézet")
        # self.ribbon.add_action_button(tab_app, self.act_exit)  # -ez nem kell: a kilépés a fájl menüben van

        self.ribbon.add_action_button(tab_app, self.act_toolbar_menubar)
        self.ribbon.add_action_button(tab_app, self.act_toolbar_ribbon)

        menu = self._build_file_menu_for_ribbon()
        self.ribbon.file_btn.setMenu(menu)

        self.ribbon.add_separator(tab_data, spacing=18)

    def set_toolbar_mode(self, mode: str) -> None:
        s = QSettings("SzaboG", "PenzugyiNaplo")
        s.setValue("ui/toolbar_mode", mode)

        is_ribbon = mode == "ribbon"
        # menüsor mindig létezhet, de el is rejthető:
        self.menuBar().setVisible(not is_ribbon)

        if hasattr(self, "ribbon") and self.ribbon:
            self.ribbon.setVisible(is_ribbon)

        self.act_toolbar_menubar.setChecked(not is_ribbon)
        self.act_toolbar_ribbon.setChecked(is_ribbon)

        QTimer.singleShot(0, self._sync_left_year_offset)

    def _load_toolbar_mode(self) -> None:
        s = QSettings("SzaboG", "PenzugyiNaplo")
        mode = str(s.value("ui/toolbar_mode", "menubar"))
        if mode not in ("menubar", "ribbon"):
            mode = "menubar"
        self.set_toolbar_mode(mode)

    def _build_file_menu_for_ribbon(self) -> QMenu:
        m = QMenu(self)
        m.addAction(self.act_new_tx)
        m.addSeparator()
        m.addAction(self.act_import)
        m.addAction(self.act_export)
        m.addSeparator()
        # ide: Beállítások action (ha van), vagy a settings oldalra navigálás
        m.addAction(self.act_exit)
        return m

    def on_import(self) -> None:
        QMessageBox.information(self, "Import", "Import funkció még nincs megírva.")

    def on_export(self) -> None:
        QMessageBox.information(self, "Export", "Export funkció még nincs megírva.")

    def _rebind_db_to_pages(self) -> None:
        # ahol van bind_db, ott új DB-t adunk át
        for key, page in self.pages.items():
            if hasattr(page, "bind_db"):
                page.bind_db(self.db)

        # és frissítsünk mindent, ami tud reload-ot
        for key, page in self.pages.items():
            if hasattr(page, "reload"):
                page.reload()

    def on_backup_database(self) -> None:
        db_path = Path(self.db.db_name)

        if not db_path.exists():
            QMessageBox.warning(self, "Mentés", f"A DB fájl nem található:\n{db_path}")
            return

        # alap fájlnév javaslat
        suggested = f"{db_path.stem}_backup.sqlite3"
        target, _ = QFileDialog.getSaveFileName(
            self,
            "Adatbázis mentése (backup)",
            str(db_path.with_name(suggested)),
            "SQLite DB (*.sqlite3 *.db);;Minden fájl (*)",
        )
        if not target:
            return

        try:
            # biztos ami biztos: flush/close ha van
            self.db.close() if hasattr(self.db, "close") else None
            shutil.copy2(str(db_path), target)
            QMessageBox.information(self, "Mentés kész", f"Backup elkészült:\n{target}")
        except Exception as e:
            QMessageBox.critical(self, "Mentés hiba", f"Nem sikerült menteni:\n{e}")
        finally:
            # visszanyitjuk a DB-t, hogy az app menjen tovább
            from db.transaction_database import TransactionDatabase

            self.db = TransactionDatabase(str(db_path))
            self._rebind_db_to_pages()

    def on_restore_database(self) -> None:
        db_path = Path(self.db.db_name)

        source, _ = QFileDialog.getOpenFileName(
            self,
            "Adatbázis betöltése (restore)",
            str(db_path.parent),
            "SQLite DB (*.sqlite3 *.db);;Minden fájl (*)",
        )
        if not source:
            return

        ret = QMessageBox.warning(
            self,
            "Betöltés (restore)",
            "Biztosan betöltöd ezt a backupot?\n\n"
            "A jelenlegi adatbázis felül lesz írva.\n"
            "A művelet nem visszavonható.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if ret != QMessageBox.Yes:
            return

        source_path = Path(source)
        if not source_path.exists():
            QMessageBox.warning(
                self, "Betöltés", f"A kiválasztott fájl nem létezik:\n{source}"
            )
            return

        try:
            # 1) DB bezár
            self.db.close() if hasattr(self.db, "close") else None

            # 2) biztonsági mentés a jelenlegiről (ugyanabba a mappába)
            if db_path.exists():
                safety = db_path.with_suffix(db_path.suffix + ".pre_restore.bak")
                shutil.copy2(str(db_path), str(safety))

            # 3) restore (felülírjuk az app DB-jét)
            shutil.copy2(str(source_path), str(db_path))

            # 4) DB újranyit + oldalak újrakötése + reload
            from db.transaction_database import TransactionDatabase

            self.db = TransactionDatabase(str(db_path))
            self._rebind_db_to_pages()
            self.reload_all_pages()

            QMessageBox.information(
                self, "Betöltés kész", "A backup betöltve, az oldalak frissítve."
            )
        except Exception as e:
            QMessageBox.critical(self, "Betöltés hiba", f"Nem sikerült betölteni:\n{e}")
            # megpróbáljuk visszanyitni a meglévőt, hogy ne haljon meg az app
            try:
                from db.transaction_database import TransactionDatabase

                self.db = TransactionDatabase(str(db_path))
                self._rebind_db_to_pages()
            except Exception:
                pass

    def on_new_transaction(self) -> None:
        wiz = TransactionWizard(self.db, self, parent=self)

        if wiz.exec() == QDialog.DialogCode.Accepted:
            # ha van majd transactions page reload metódus, itt lehet hívni
            # de minimum: navigáljunk a tranzakciók oldalra
            self.set_page("transactions")
            page = self.pages.get("transactions")
            if page and hasattr(page, "reload"):
                page.reload()

    def _build_navbar(self) -> None:
        self.navbar = _SimpleNavBar(parent=self._right_panel)

    def _build_pages(self) -> None:
        """Oldal-stack felépítése és az alap oldalak regisztrálása."""
        # 1) Stack létrehozása (parent: jobb panel)
        self.page_stack = QStackedWidget(self._right_panel)

        # 2) Placeholder / core oldalak regisztrálása
        self._register_core_pages()

        # 3) Kezdő oldal
        if "home" in self.pages:
            self.set_page("home")
        else:
            # ha valamiért nincs home, akkor legalább az első widgetre álljunk
            if self.page_stack.count() > 0:
                self.page_stack.setCurrentIndex(0)

    def on_reset_database(self) -> None:
        ret = QMessageBox.warning(
            self,
            "Adatbázis törlése",
            "Biztosan törlöd az adatbázist?\n\nA művelet nem visszavonható.",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if ret != QMessageBox.Yes:
            return

        db_path = Path(self.db.db_name)
        self.db.close() if hasattr(self.db, "close") else None

        if db_path.exists():
            db_path.unlink()

        from db.transaction_database import TransactionDatabase

        self.db = TransactionDatabase(str(db_path))
        self.reload_all_pages()

        # oldalak újrakötése
        page = self.pages.get("transactions")
        if page and hasattr(page, "bind_db"):
            page.bind_db(self.db)

    def on_bill_requested(self, bill_id: int) -> None:
        # TODO: később rendes részletek

        QMessageBox.information(self, "Számla részletek", f"Bill ID: {bill_id}")

    def reload_all_pages(self) -> None:
        # ahol van bind_db: újra ráadjuk a DB-t (ha restore/reset miatt új példány lett)
        for page in self.pages.values():
            if hasattr(page, "bind_db"):
                page.bind_db(self.db)

        # ahol van reload: meghívjuk
        for page in self.pages.values():
            if hasattr(page, "reload"):
                page.reload()

        # extra: ha van “aktuális oldal” specifikus frissítés (nem kötelező)
        w = self.stack.currentWidget() if hasattr(self, "stack") else None
        if w is not None and hasattr(w, "reload"):
            w.reload()
