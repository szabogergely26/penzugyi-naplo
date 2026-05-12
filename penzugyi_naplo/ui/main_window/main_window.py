# pénzügyi_napló/ui/main_window/main_window.py
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


from pathlib import Path
from typing import Optional

from PySide6.QtCore import QEvent, QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QPushButton,
    QButtonGroup,


    QDialog,
    
    QHBoxLayout,
    QLabel,
    QMainWindow,
    
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.config import (
    APP_NAME, 
    ORG_NAME,
    SETTINGS_KEY_STYLE_MODE,
    STYLE_CLASSIC,
    STYLE_MODERN,
    STYLE_MODERN_HOME,
    DEFAULT_STYLE_MODE,
    AVAILABLE_STYLE_MODES,
)

from penzugyi_naplo.core.app_context import AppContext, AppState
from penzugyi_naplo.core.logging_utils import DebugFlags, Log
from penzugyi_naplo.db.transaction_database import TransactionDatabase

from penzugyi_naplo.ui.dialogs.about_dialog import AboutDialog
from penzugyi_naplo.ui.dialogs.version_info import VersionInfoDialog
from penzugyi_naplo.ui.likviditas.wizard.wizard_transaction import TransactionWizard


from penzugyi_naplo.ui.shared.nav_bar import NavBar


from penzugyi_naplo.ui.shared.widgets.year_tabs_bar import YearTabsBar
from penzugyi_naplo.ui.dialogs.log_viewer_dialog import LogViewerDialog
from penzugyi_naplo.ui.dialogs.version_history_dialog import VersionHistoryDialog



from penzugyi_naplo.ui.main_window.likviditas.register_pages import (
    register_likviditas_pages,
)

from penzugyi_naplo.ui.main_window.likviditas.menus import (
    build_likviditas_menubar,
    build_likviditas_ribbon,
)

from penzugyi_naplo.ui.main_window.likviditas.actions import (
    create_likviditas_actions,
)

from penzugyi_naplo.ui.main_window.likviditas.toolbar_mode import (
    load_likviditas_toolbar_mode,
    set_likviditas_toolbar_mode,
)


from penzugyi_naplo.ui.main_window.likviditas.import_handlers import handle_ods_import


from penzugyi_naplo.ui.main_window.likviditas.backup_restore_handlers import (
    handle_backup_database,
    handle_restore_database,
)



# - Aranyszámla importok:

from penzugyi_naplo.ui.main_window.aranyszamla.register_pages import (
    register_aranyszamla_pages,
)

from penzugyi_naplo.ui.main_window.aranyszamla.wizard.gold_trade_wizard import (
    GoldTradeWizard,
)

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

        # --- TELJES ABLAK FŐ LAYOUT ---
        # Felül: dev banner + ribbon
        # Alul: modulválasztó + évszűrő + aktuális oldal tartalma
        self._central_layout = QVBoxLayout(self._central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)

        # --- ALSÓ FŐTERÜLET: bal + jobb panelek ---
        self._main_layout = QHBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)





        # --- MODULVÁLASZTÓ PANEL ---
        self._module_panel = QWidget(self._central)
        self._module_panel.setObjectName("modulePanel")
        self._module_panel.setFixedWidth(150)

        self._module_layout = QVBoxLayout(self._module_panel)
        self._module_layout.setContentsMargins(8, 8, 8, 8)
        self._module_layout.setSpacing(12)

    
        # Alapértelmezett induló modul: Likviditás.
        self.current_module = "likviditas"

        # Bal oldali modulválasztó sáv állapota.
        # True = teljes szélességű, False = összecsukott.
        self.module_sidebar_expanded = True

        # Ha True, akkor az oldalsáv csak hover miatt van ideiglenesen kinyitva.
        self.module_sidebar_hover_expanded = False


        # Hamburger gomb a bal oldali modulválasztó sávhoz.
        # Később ez fogja nyitni/csukni az oldalsávot.
        self.sidebar_toggle_button = QPushButton("☰")
        self.sidebar_toggle_button.setObjectName("sidebarToggleButton")
        self.sidebar_toggle_button.setFixedSize(36, 36)
        self.sidebar_toggle_button.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle_button.setToolTip("Oldalsáv összecsukása / kibontása")

        # A hamburger mindig a modulpanel tetején legyen.
        self._module_layout.addWidget(self.sidebar_toggle_button, 0, Qt.AlignHCenter)
        
        # Kis térköz a hamburger alatt.
        self._module_layout.addSpacing(40)

        # Ez húzza a modulválasztó gombokat középre/lejjebb.
        self._module_layout.addStretch(1)

        self.btn_module_likviditas = QPushButton("Likviditás")
        self.btn_module_likviditas.setCheckable(True)
        self.btn_module_likviditas.setChecked(True)
        self.btn_module_likviditas.setObjectName("moduleButtonActive")
        self.btn_module_likviditas.setMinimumHeight(54)

        self.btn_module_aranyszamla = QPushButton("Aranyszámla")
        self.btn_module_aranyszamla.setCheckable(True)
        self.btn_module_aranyszamla.setObjectName("moduleButton")
        self.btn_module_aranyszamla.setMinimumHeight(54)

        

        self.module_button_group = QButtonGroup(self)
        self.module_button_group.setExclusive(True)
        self.module_button_group.addButton(self.btn_module_likviditas)
        self.module_button_group.addButton(self.btn_module_aranyszamla)

        
        self._module_layout.addWidget(self.btn_module_likviditas)
        self._module_layout.addWidget(self.btn_module_aranyszamla)
        

        # A gombok alatt is legyen hely, így középen maradnak.
        self._module_layout.addStretch(1)



        # --- BAL PANEL ---
        self._left_panel = QWidget(self._central)
        self._left_panel.setObjectName("leftPanel")
        self._left_panel.setFixedWidth(125)

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

        self._central_layout.addWidget(self.dev_banner)

        # --- Panelok a fő layouthoz ---
        self._main_layout.addWidget(self._module_panel, 0)
        self._main_layout.addWidget(self._left_panel, 0)
        self._main_layout.addWidget(self._right_panel, 1)

        # --- Actions + menü ---
        self._create_actions()

       
        self._build_menubar()



        # --- LEFT: Year tabs (EGYSZER) ---
        
        years = self.db.get_transaction_years()

        if not years:
            years = [self.state.active_year]

        self.year_tabs = YearTabsBar(
            years=years,
            parent=self._left_panel,
        )
        self._left_layout.addWidget(self.year_tabs)



        # --- FULL WIDTH: ribbon ---
        self._build_ribbon()
        self.ribbon.setObjectName("ribbonBar")
        self._central_layout.addWidget(self.ribbon)

        # --- ALSÓ FŐTERÜLET: modulválasztó + évszűrő + jobb panel ---
        self._central_layout.addLayout(self._main_layout, 1)

        # --- RIGHT: navbar + pages ---
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


        
        # Hamburger menü események:

        # Egér ráhúzás / elhagyás figyelése az összecsukott oldalsávnál.
        self._module_panel.installEventFilter(self)

        # kattintáskori művelet
        self.sidebar_toggle_button.clicked.connect(self.toggle_module_sidebar)




    def toggle_module_sidebar(self) -> None:
        """
        Bal oldali modulválasztó sáv összecsukása / kibontása.

        Kattintásos állapot:
            - nyitva: 150 px széles, látszanak a modulválasztó gombok
            - csukva: 52 px széles, csak a hamburger ikon látszik

        Hover:
            - ha csukott állapotban rámegy az egér, ideiglenesen kinyílik
            - ha az egér elhagyja, visszacsukódik
        """
        
        self.module_sidebar_hover_expanded = False
        self.module_sidebar_expanded = not self.module_sidebar_expanded

        if self.module_sidebar_expanded:
            self._set_module_sidebar_expanded(persistent=True)
        else:
            self._set_module_sidebar_collapsed()

    
    # segéd metódusok a sidebar-hoz:

    def _set_module_sidebar_expanded(self, persistent: bool = False) -> None:
        """
        Modulválasztó oldalsáv kinyitása.

        persistent=True:
            rendes, kattintással nyitott állapot

        persistent=False:
            ideiglenes, hover miatti kinyitás
        """
    
        self._module_panel.setFixedWidth(150)

        self.btn_module_likviditas.setVisible(True)
        self.btn_module_aranyszamla.setVisible(True)

        if persistent:
            self.module_sidebar_expanded = True
            self.module_sidebar_hover_expanded = False
            self.sidebar_toggle_button.setToolTip("Oldalsáv összecsukása")
            self.log.d("MODULE SIDEBAR: expanded")
        else:
            self.module_sidebar_hover_expanded = True
            self.sidebar_toggle_button.setToolTip("Oldalsáv rögzített kibontása")
            self.log.d("MODULE SIDEBAR: hover expanded")


    def _set_module_sidebar_collapsed(self) -> None:
        """
        Modulválasztó oldalsáv összecsukása.
        """
        
        self._module_panel.setFixedWidth(52)

        self.btn_module_likviditas.setVisible(False)
        self.btn_module_aranyszamla.setVisible(False)

        self.module_sidebar_expanded = False
        self.module_sidebar_hover_expanded = False

        self.sidebar_toggle_button.setToolTip("Oldalsáv kibontása")
        self.log.d("MODULE SIDEBAR: collapsed")



    def eventFilter(self, watched: object, event: QEvent) -> bool:
        """
        Összecsukott modulválasztó sáv hover-kezelése.

        Ha a sáv csukott állapotban van:
            - egér belépésre ideiglenesen kinyitjuk
            - egér kilépésre visszacsukjuk
        """
    
        if watched is self._module_panel:
            if event.type() == QEvent.Type.Enter:
                if not self.module_sidebar_expanded:
                    self._set_module_sidebar_expanded(persistent=False)
                return False

            if event.type() == QEvent.Type.Leave:
                if self.module_sidebar_hover_expanded:
                    self._set_module_sidebar_collapsed()
                return False

        return super().eventFilter(watched, event)









    def apply_style_mode(self, mode: str) -> None:
        mode = (mode or "").strip().lower()

        style_to_file = {
            STYLE_CLASSIC: "classic_style.qss",
            STYLE_MODERN: "modern_style.qss",
            STYLE_MODERN_HOME: "modern_style_home.qss",
        }

        if mode not in AVAILABLE_STYLE_MODES:
            mode = DEFAULT_STYLE_MODE

        base = Path(__file__).resolve().parent.parent  # .../ui
        qss_path = base / "styles" / style_to_file[mode]

        try:
            qss = qss_path.read_text(encoding="utf-8")
        except Exception as e:
            self.log.d("QSS load failed:", str(qss_path), e)
            qss = ""

        self.setStyleSheet(qss)
        self.log.d("Style mode set:", mode, "QSS:", str(qss_path))




    def load_style_mode(self) -> None:
        s = QSettings(ORG_NAME, APP_NAME)
        mode = str(s.value(SETTINGS_KEY_STYLE_MODE, DEFAULT_STYLE_MODE))
        self.apply_style_mode(mode)

    def on_year_selected(self, year: int) -> None:
        """
        Konkrét év kiválasztása a bal oldali évlistából.

        Ilyenkor a tranzakciós kereső hatóköre visszaáll
        "Aktuális év" módra.
        """
        self.set_active_year(int(year))
        self._filter_all_years = False
        self._filter_year = int(year)

        tx = self.pages.get("transactions")
        if tx and hasattr(tx, "set_search_scope"):
            tx.set_search_scope("active_year")
        else:
            self._apply_year_filter()

    def on_all_years(self) -> None:
        """
        A bal oldali "Minden év" tab kiválasztása.

        Ilyenkor a tranzakciós oldalon lévő keresési hatókör is
        átáll "Minden év" módra, hogy a bal oldali vizuális állapot
        és a táblázat tartalma ugyanazt mutassa.
        """
        self._filter_all_years = True
        self._filter_year = None

        tx = self.pages.get("transactions")
        if tx and hasattr(tx, "set_search_scope"):
            tx.set_search_scope("all_years")
        else:
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
        """
        Az év-sávot a jobb oldali modulon belüli navbar alá igazítja.

        A ribbon már teljes szélességű felső sáv, ezért annak magasságát
        itt nem kell beleszámolni.
        """
        h = 0

        if getattr(self, "navbar", None) is not None and self.navbar.isVisible():
            h += self.navbar.height()

        self._left_header_spacer.setFixedHeight(h + 16)



    def _build_navbar(self) -> None:
        self.navbar = NavBar(parent=self._right_panel)

   
    def _register_core_pages(self) -> None:
        """
        Likviditás modul oldalainak regisztrálása.

        A konkrét oldalak létrehozása külön modulban van, hogy a MainWindow
        megmaradjon főablak-váznak.
        """
        register_likviditas_pages(self)
        register_aranyszamla_pages(self)

    def _connect_core_signals(self) -> None:
        """
        Itt kötjük majd össze a topbar/sidebar/year tabs jelzéseket.
        Most szándékosan üres.
        """
        self.year_tabs.yearChanged.connect(self.on_year_selected)
        self.year_tabs.allYearsSelected.connect(self.on_all_years)
        self.navbar.pageRequested.connect(self.set_page)
        self.btn_module_likviditas.clicked.connect(self.switch_to_likviditas_module)
        self.btn_module_aranyszamla.clicked.connect(self.switch_to_aranyszamla_module)

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

        # fallback: ha van refresh, hívd
        elif hasattr(page, "refresh"):
            page.refresh()



    def switch_to_likviditas_module(self) -> None:
        """
        Likviditás modul aktiválása.
        """

        self.current_module = "likviditas"

        # Évszűrő panel láthatósága:
        self._left_panel.setVisible(True)


        # NavBar láthatósága    (Kezdő, Tranzakciók, stb......)
        self.navbar.setVisible(True)

         # Likviditás kezdőoldal visszaállítása:
        self.set_page("home")




    def switch_to_aranyszamla_module(self) -> None:
        """
        Aranyszámla modul aktiválása.

        """

        self.current_module = "aranyszamla"


        # Évszűrő panel láthatósága:
        self._left_panel.setVisible(False)

        

        # NavBar láthatósága    (Kezdő, Tranzakciók, stb.......)
        self.navbar.setVisible(False)
        self.set_page("aranyszamla_home")



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
        """Likviditás nézethez tartozó actionök létrehozása."""
        create_likviditas_actions(self)




    def _build_menubar(self) -> None:
        """Klasszikus menüsor felépítése."""
        build_likviditas_menubar(self)
       

    def _build_ribbon(self) -> None:
        """Ribbon felépítése."""
        build_likviditas_ribbon(self)

        

    def set_toolbar_mode(self, mode: str) -> None:
        """Toolbar mód beállítása."""
        set_likviditas_toolbar_mode(self, mode)

    def _load_toolbar_mode(self) -> None:
        """Toolbar mód betöltése QSettings-ből."""
        load_likviditas_toolbar_mode(self)

    
    def on_import(self) -> None:
        """ODS tranzakció import indítása."""
        handle_ods_import(self)
        


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
         """Adatbázis biztonsági mentése."""
         handle_backup_database(self)


    def on_restore_database(self) -> None:
        """Adatbázis betöltése"""
        handle_restore_database(self)
        


    def on_new_transaction(self) -> None:
        """Az aktív modulhoz tartozó új művelet varázslóját nyitja meg."""

        if self.current_module == "aranyszamla":
            self.on_new_gold_trade()
            return

        wiz = TransactionWizard(self.db, self, parent=self)

        if wiz.exec() == QDialog.DialogCode.Accepted:
            # Likviditás modul: mentés után a tranzakciós oldalra váltunk.
            self.set_page("transactions")

            page = self.pages.get("transactions")
            if page and hasattr(page, "reload"):
                page.reload()



    def on_new_gold_trade(self) -> None:
        """Aranyszámla modul: vétel/eladás varázsló megnyitása."""

        wiz = GoldTradeWizard(self.db.db_name, parent=self)

        if wiz.exec() == QDialog.DialogCode.Accepted:
            # Mentés után az Aranyszámla modulra váltunk.
            self.set_page("aranyszamla_home")

            # Az Aranyszámla modul egyetlen MainWindow-szintű oldal.
            page = self.pages.get("aranyszamla_home")

            if page and hasattr(page, "show_trading"):
                page.show_trading()

            if page and hasattr(page, "refresh"):
                page.refresh()


                

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


    def _show_version_history(self) -> None:
        dialog = VersionHistoryDialog(self)
        dialog.exec()