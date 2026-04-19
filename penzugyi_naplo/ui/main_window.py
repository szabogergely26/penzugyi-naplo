# pénzügyi_napló/ui/main_window.py
# -----------------------------------

"""
Az alkalmazás fő vezérlő ablaka
(penzugyi_naplo/ui/main_window.py).

Architektúra szerep:
    - Globális UI felépítése
    - Oldalak regisztrálása és navigációja  -->self.page_stack, set_page
    - Aktív év és oldal kezelése (AppState)
    - UI → oldal → DB koordináció

UI szerkezet:
    - Bal panel: YearTabsBar (ui/widgets/year_tabs_bar.py)
    - Felső navigáció: RibbonBar / NavBar
    - Oldalak: QStackedWidget

Gombok létrehozása:
    - ui / shared / nav_bar.py : Felső sáv gombok
    - ui / shared / widgets / year_tabs_bar.py : Évszűrő gombok


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
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.config import APP_NAME, ORG_NAME
from penzugyi_naplo.core.app_context import AppContext, AppState
from penzugyi_naplo.core.logging_utils import DebugFlags, Log
from penzugyi_naplo.db.transaction_database import TransactionDatabase
from penzugyi_naplo.ui.bills.bills_page import BillsPage
from penzugyi_naplo.ui.dialogs.about_dialog import AboutDialog
from penzugyi_naplo.ui.dialogs.version_info import VersionInfoDialog
from penzugyi_naplo.ui.likviditas.dialogs.wizard_transaction import TransactionWizard
from penzugyi_naplo.ui.likviditas.pages.accounts_page import AccountsPage
from penzugyi_naplo.ui.likviditas.pages.home_page import HomePage
from penzugyi_naplo.ui.likviditas.pages.settings_page import SettingsPage
from penzugyi_naplo.ui.likviditas.pages.statistics_page import StatisticsPage
from penzugyi_naplo.ui.likviditas.pages.transactions_page import TransactionsPage
from penzugyi_naplo.ui.shared.nav_bar import NavBar
from penzugyi_naplo.ui.shared.pages.coming_soon_page import ComingSoonPage
from penzugyi_naplo.ui.shared.widgets.ribbon_bar import RibbonBar
from penzugyi_naplo.ui.shared.widgets.year_tabs_bar import YearTabsBar
from penzugyi_naplo.ui.dialogs.log_viewer_dialog import LogViewerDialog

# ------- Importok vége -------


# Ha nálad máshol van, igazítsd:
# from pénzügyi_napló.db.transaction_database import TransactionDatabase




class MainWindow(QMainWindow):
    """
    MainWindow váz:
    - csak konstruktor
    - legfontosabb attribútumok (db, state, pages registry, stacked, central root)
    """

    def __init__(
        self,
        db: TransactionDatabase,
        dev_mode: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        


        # --- Core állapot ---
        self.db: TransactionDatabase = db
        self.dev_mode = dev_mode
        self.state = AppState(active_year=2026)
        self.ctx = AppContext(
            db=self.db,
            state=self.state,
            dev_mode=self.dev_mode,
        )

        # --- Debug/log (csak dev módban aktív) ---
        self.log = Log(
            DebugFlags(
                enabled=self.dev_mode,
                trace_page_stack=False,  # ezt csak akkor kapcsold be, ha kell
            )
        )

        
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
        self._left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._left_header_spacer = QWidget(self._left_panel)
        self._left_header_spacer.setFixedHeight(0)
        self._left_layout.addWidget(self._left_header_spacer)
        self._left_layout.addSpacing(12)

        # --- JOBB PANEL ---
        self._right_panel = QWidget(self._central)
        self._root_layout = QVBoxLayout(self._right_panel)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self.dev_banner = QLabel(self._right_panel)
        self.dev_banner.setObjectName("devBanner")
        self.dev_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self.dev_mode:  # nálad MainWindow(db=db, dev_mode=dev) már át van adva
            self.dev_banner.setText(f"FEJLESZTŐI MÓD AKTÍV — {self.db.db_name}")
            self.dev_banner.setVisible(True)
        else:
            self.dev_banner.setVisible(False)

        self._root_layout.addWidget(self.dev_banner)

        # --- Panelok a fő layouthoz ---
        self._main_layout.addWidget(self._left_panel, 0)
        self._main_layout.addWidget(self._right_panel, 1)

        # --- Actions + menü ---
        self._create_actions()

        self.act_about = QAction("Névjegy", self)
        self.act_about.triggered.connect(self._show_about)

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

        self.setWindowTitle("Pénzügyi Napló : Fejlesztői verzió")

        # --  Induló ablakméret:   (szélesség, magasság)
        self.resize(1650, 1000)

        # - Minimum ablakméret:  (szélesség, magasság)
        self.setMinimumSize(1440, 900)


        self.load_style_mode()

        # Initial state
        self.year_tabs.set_active_year(self.state.active_year, emit=False)
        self.set_active_year(self.state.active_year)
        self.set_page(self.state.active_page_key)

        self._sync_left_year_offset()

        QTimer.singleShot(0, self._sync_left_year_offset)

        self._filter_all_years = True
        self._filter_year = None

        if self.dev_mode:
            self.log.flags.trace_page_stack = True


        

        

    def apply_style_mode(self, mode: str) -> None:
        mode = (mode or "").strip().lower()
        if mode not in ("classic", "modern"):
            mode = "classic"

        # 1) fájl kiválasztás
        base = Path(__file__).resolve().parent  # .../ui
        qss_path = (
            base
            / "styles"
            / ("classic_style.qss" if mode == "classic" else "modern_style.qss")
        )

        # 2) betöltés
        try:
            qss = qss_path.read_text(encoding="utf-8")
        except Exception as e:
            self.log.d("QSS load failed:", str(qss_path), e)
            qss = ""

        # 3) alkalmazás
        self.setStyleSheet(qss)
        self.log.d("Style mode set:", mode, "QSS:", str(qss_path))

    def load_style_mode(self) -> None:
        s = QSettings(ORG_NAME, APP_NAME)
        mode = str(s.value("ui/style_mode", "classic"))
        self.apply_style_mode(mode)

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

    def _build_navbar(self) -> None:
        self.navbar = NavBar(parent=self._right_panel)

    # Oldalak regisztrálása
    # ---------------------------

    # (gerinc metódusok, hogy a konstruktor tiszta maradjon)

    def _register_core_pages(self) -> None:
        """
        Placeholder oldalak létrehozása.
        DEV módban: valódi (félkész) oldalak is elérhetők.
        Normál módban: ezek "Hamarosan" placeholder-rel jelennek meg.
        """
        self.add_page("home", HomePage(self))
        self.add_page("transactions", TransactionsPage(self, db=self.db))

        # --- Statisztika ---
        if self.dev_mode:
            self.add_page("statistics", StatisticsPage(self))
        else:
            self.add_page(
                "statistics",
                ComingSoonPage(
                    title="Statisztika",
                    msg="Diagrammok és kimutatások (fejlesztés alatt).",
                ),
            )

        self.add_page("settings", SettingsPage(self))

        # --- Számlák ---
       
        self.bills_page = BillsPage(self, db=self.db)
        self.bills_page.billRequested.connect(self.on_bill_requested)
        self.add_page("bills", self.bills_page)
        
           


        # --- Pénztárcák / egyenlegek (Accounts/Wallets) ---
        # Ez NEM a bills (kötelezők) oldal, hanem egyenleg/érték nyilvántartás.
        self.add_page("accounts", AccountsPage(self, db=self.db))

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

        # idempotencia: ha már ezen az oldalon vagyunk, ne csináljunk semmit
        if getattr(self, "_active_page_key", None) == key:
            return
        self._active_page_key = key

        # opcionális stack trace (később settingsből kapcsolható)
        # if self.log.flags.trace_page_stack:
        #    self.log.trace("SET_PAGE STACK", limit=8)

        page = self.pages.get(key)
        if page is None:
            QMessageBox.warning(self, "Navigáció", f"Ismeretlen oldal: {key}")
            self.log.d("SET_PAGE: unknown page:", key)
            return

        self.state.active_page_key = key
        self.page_stack.setCurrentWidget(page)

        # UI szinkron
        if hasattr(self, "navbar"):
            self.navbar.set_active(key)

        # debug print csak dev módban
        self.log.d(
            "SET_PAGE:",
            key,
            "index=",
            self.page_stack.currentIndex(),
            "widget=",
            type(self.page_stack.currentWidget()).__name__,
        )

        # oldal-aktiválás hook
        if hasattr(page, "on_activated"):
            page.on_activated()

        # fallback: ha van reload, hívd
        elif hasattr(page, "reload"):
            page.reload()

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

        self.act_about = QAction("Névjegy", self)
        self.act_about.triggered.connect(self._show_about)

        self.act_version_info = QAction("Verzió infók", self)
        self.act_version_info.triggered.connect(self._show_version_info)

        self.act_log_viewer = QAction("Alkalmazásnapló", self)
        self.act_log_viewer.triggered.connect(self.show_log_viewer)





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
        m_help.addAction(self.act_about)
        m_help.addAction(self.act_version_info)
        m_help.addSeparator()
        m_help.addAction(self.act_log_viewer)

       

    def _build_ribbon(self) -> None:

        # FONTOS:
        # A ribbon "Fájl" gombja nem ribbon-tab, hanem egy külön beépített gomb
        # (self.ribbon.file_btn). Ezért ide nem add_tab()/add_action_button() kell,
        # hanem egy külön QMenu-t építünk, és azt adjuk hozzá a file_btn-höz.

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
        btn_delete.setObjectName("dangerButton")
        btn_delete.style().unpolish(btn_delete)
        btn_delete.style().polish(btn_delete)
        btn_delete.update()



        tab_app = self.ribbon.add_tab("Nézet")

        tab_help = self.ribbon.add_tab("Súgó")
        self.ribbon.add_action_button(tab_help, self.act_about)
        self.ribbon.add_action_button(tab_help, self.act_version_info)

        self.ribbon.add_action_button(tab_help, self.act_log_viewer)

        self.ribbon.add_action_button(tab_app, self.act_toolbar_menubar)
        self.ribbon.add_action_button(tab_app, self.act_toolbar_ribbon)


        

        # Fájl-hoz létrehozza a lenyíló menüt:

        file_menu = self._build_file_menu_for_ribbon()
        self.ribbon.file_btn.setMenu(file_menu)

        

    def set_toolbar_mode(self, mode: str) -> None:
        s = QSettings(ORG_NAME, APP_NAME)
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
        s = QSettings(ORG_NAME, APP_NAME)
        mode = str(s.value("ui/toolbar_mode", "menubar"))
        if mode not in ("menubar", "ribbon"):
            mode = "menubar"
        self.set_toolbar_mode(mode)

    def _build_file_menu_for_ribbon(self) -> QMenu:
        menu = QMenu("Fájl", self)

        # Fájl menü elemek
        menu.addAction(self.act_new_tx)
        menu.addSeparator()
        menu.addAction(self.act_exit)
        
        return menu

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
            from penzugyi_naplo.db.transaction_database import TransactionDatabase

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
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )

        if ret != QMessageBox.StandardButton.Yes:
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
            from penzugyi_naplo.db.transaction_database import TransactionDatabase

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
                from penzugyi_naplo.db.transaction_database import TransactionDatabase

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

    def _build_pages(self) -> None:
        """Oldal-stack felépítése és az alap oldalak regisztrálása."""
        # 1) Stack létrehozása (parent: jobb panel)
        self.page_stack = QStackedWidget(self._right_panel)

        # 2) Placeholder / core oldalak regisztrálása
        self._register_core_pages()

    def on_reset_database(self) -> None:
        ret = QMessageBox.warning(
            self,
            "Adatbázis törlése",
            "Biztosan törlöd az adatbázist?\n\nA művelet nem visszavonható.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return

        db_path = Path(self.db.db_name)
        self.db.close() if hasattr(self.db, "close") else None

        if db_path.exists():
            db_path.unlink()

        from penzugyi_naplo.db.transaction_database import TransactionDatabase

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
        w = self.page_stack.currentWidget() if hasattr(self, "page_stack") else None

        if w is not None and hasattr(w, "reload"):
            w.reload()

    def _show_about(self):
        dlg = AboutDialog(self)
        dlg.exec()


    def _show_version_info(self):
        dlg = VersionInfoDialog(self)
        dlg.exec()

    def show_log_viewer(self) -> None:
        dialog = LogViewerDialog(self)
        dialog.exec()