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

import gc
import inspect
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from penzugyi_naplo.config.config import (
    APP_NAME,
    AVAILABLE_STYLE_MODES,
    DEFAULT_STYLE_MODE,
    ORG_NAME,
    SETTINGS_KEY_STYLE_MODE,
    STYLE_CLASSIC,
    STYLE_MODERN,
    STYLE_MODERN_HOME,
    clear_backup_restore_status,
    get_last_backup_ts,
    get_last_restore_ts,
    set_last_backup_ts,
    set_last_restore_ts,
)
from penzugyi_naplo.core.app_context import AppContext, AppState
from penzugyi_naplo.core.logging_utils import DebugFlags, Log
from penzugyi_naplo.db.transaction_database import TransactionDatabase
from penzugyi_naplo.ui.dialogs.about_dialog import AboutDialog
from penzugyi_naplo.ui.dialogs.log_viewer_dialog import LogViewerDialog
from penzugyi_naplo.ui.dialogs.version_history_dialog import VersionHistoryDialog
from penzugyi_naplo.ui.dialogs.version_info import VersionInfoDialog
from penzugyi_naplo.ui.likviditas.wizard.wizard_transaction import TransactionWizard

# - Aranyszámla importok:
from penzugyi_naplo.ui.main_window.aranyszamla.register_pages import (
    register_aranyszamla_pages,
)
from penzugyi_naplo.ui.main_window.aranyszamla.wizard.gold_trade_wizard import (
    GoldTradeWizard,
)
from penzugyi_naplo.ui.main_window.likviditas.actions import (
    create_likviditas_actions,
)
from penzugyi_naplo.ui.main_window.likviditas.backup_restore_handlers import (
    handle_backup_database,
    handle_restore_database,
)
from penzugyi_naplo.ui.main_window.likviditas.import_handlers import handle_ods_import
from penzugyi_naplo.ui.main_window.likviditas.menus import (
    build_likviditas_menubar,
    build_likviditas_ribbon,
)
from penzugyi_naplo.ui.main_window.likviditas.register_pages import (
    register_likviditas_pages,
)
from penzugyi_naplo.ui.main_window.likviditas.toolbar_mode import (
    create_likviditas_standard_toolbar,
    load_likviditas_toolbar_mode,
    set_likviditas_toolbar_mode,
)
from penzugyi_naplo.ui.settings.settings import SettingsDialog
from penzugyi_naplo.ui.shared.nav_bar import NavBar
from penzugyi_naplo.ui.shared.widgets.year_tabs_bar import YearTabsBar

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
        parent: QWidget | None = None,
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
        self.sidebar_toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle_button.setToolTip("Oldalsáv összecsukása / kibontása")

        # A hamburger mindig a modulpanel tetején legyen.
        self._module_layout.addWidget(self.sidebar_toggle_button, 0, Qt.AlignmentFlag.AlignHCenter)

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

        # --- Standard / menüsoros eszköztár ---
        self.likviditas_standard_toolbar = create_likviditas_standard_toolbar(self)
        self.addToolBar(
            Qt.ToolBarArea.TopToolBarArea,
            self.likviditas_standard_toolbar,
        )

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

        # --- Globális statusbar: "Utolsó mentés" / "Utoljára betöltve" ---
        self._build_statusbar()

        # DB módosítás-eseményeire feliratkozás (lásd TransactionDatabase.on_save).
        # FONTOS: ez az "utolsó módosítás" jelzés, NEM a kézi mentés/backup!
        # Minden sima commit() (pl. egy tétel rögzítése) is meghívja ezt.
        # Jelenleg nincs hozzá statusbar-kimenet, csak a tooltipben van
        # utalás rá; ha a jövőben kellene valahol megjeleníteni, ide
        # köthető be egy külön callback.
        self.db.on_save(self._on_db_saved)

        # Statusbar "Utolsó mentés" / "Utoljára betöltve" jelzések:
        # ezek KIZÁRÓLAG a kézi biztonsági mentésre (backup) illetve
        # kézi visszatöltésre (restore) frissülnek, nem minden commit-ra
        # és nem az app indulására (lásd TransactionDatabase.on_backup /
        # on_restore, valamint backup_restore_handlers.py).
        self.db.on_backup(self._on_db_backup)
        self.db.on_restore(self._on_db_restore)

        # Perzisztens állapot betöltése: az "Utolsó mentés" / "Utoljára
        # betöltve" időbélyegek app-újraindítás után is megmaradnak,
        # mert a config.py (QSettings) tárolja őket, DB-fájlonként
        # elkülönítve. Csak akkor töltjük be, ha az induláskor létrejött
        # friss TransactionDatabase-nek még nincs saját (memóriabeli)
        # értéke - ez véd az ellen, hogy egy örökölt érték (pl. korábbi
        # _reopen_db-ből) felülíródjon egy régebbi, lemezes bejegyzéssel.
        if self.db.last_backup_ts is None:
            self.db.last_backup_ts = get_last_backup_ts(self.db.db_name)
        if self.db.last_restore_ts is None:
            self.db.last_restore_ts = get_last_restore_ts(self.db.db_name)

        # Kezdeti statusbar-feliratok: app induláskor még nem történt ebben
        # a folyamatban se kézi mentés, se kézi visszatöltés, ezért "—".
        # Ha a DB-példány már hordoz korábbi last_backup_ts/last_restore_ts
        # értéket (pl. a fenti perzisztens betöltésből), azt mutatjuk.
        self._refresh_backup_restore_labels()

        # --- Signalok + kezdő állapot ---
        self._connect_core_signals()
        self._load_toolbar_mode()

        self.setWindowTitle("Pénzügyi Napló : Előzetes verzió")

        # --  Induló ablakméret:   (szélesség, magasság)
        self.resize(1650, 1000)

        # - Minimum ablakméret:  (szélesség, magasság)
        self.setMinimumSize(1440, 900)

        # Indításkor teljes méretű / maximalizált ablak.
        # self.showMaximized()

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

        # Aranyszámla modul saját kiegészítő stílusa.
        # Ez nem teljes téma, csak ráül az aktuális app témára.
        gold_qss_path = base / "styles" / "gold_style.qss"

        try:
            gold_qss = gold_qss_path.read_text(encoding="utf-8")
        except Exception as e:
            self.log.d("Gold QSS load failed:", str(gold_qss_path), e)
            gold_qss = ""

        self.setStyleSheet(qss + "\n\n" + gold_qss)
        self.log.d(
            "Style mode set:",
            mode,
            "QSS:",
            str(qss_path),
            "Gold QSS:",
            str(gold_qss_path),
        )

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

    def _build_statusbar(self) -> None:
        """
        Globális, oldalfüggetlen statusbar felépítése.

        Jelenleg két állandó címke:
            - "Utolsó mentés: ..."
            - "Utoljára betöltve: ..."

        Terv szerint később oldalanként bővíthető lesz (pl. jobb oldali
        extra státusz-widget), ezért a bal oldali két címke egy külön
        QWidget-be van szervezve, amit a QMainWindow beépített
        statusBar()-jába teszünk - így később könnyen tehetünk mellé
        oldal-specifikus tartalmat is, anélkül hogy ezt a részt bántani
        kellene.
        """

        status_bar = self.statusBar()
        status_bar.setObjectName("appStatusBar")

        self._status_container = QWidget(status_bar)
        status_layout = QHBoxLayout(self._status_container)
        status_layout.setContentsMargins(8, 0, 8, 0)
        status_layout.setSpacing(24)

        self.status_last_saved_label = QLabel("Utolsó mentés: —")
        self.status_last_saved_label.setObjectName("statusLastSavedLabel")
        self.status_last_saved_label.setToolTip(
            "A legutóbbi kézi biztonsági mentés (backup fájl készítés) "
            "időpontja. Nem az egyes tételek rögzítésének/módosításának "
            "időpontja."
        )

        self.status_last_loaded_label = QLabel("Utoljára betöltve: —")
        self.status_last_loaded_label.setObjectName("statusLastLoadedLabel")
        self.status_last_loaded_label.setToolTip(
            "A legutóbbi kézi visszatöltés (restore egy backup fájlból) "
            "időpontja. Nem az alkalmazás indításának időpontja."
        )

        status_layout.addStretch(1)
        status_layout.addWidget(self.status_last_saved_label)
        status_layout.addWidget(self.status_last_loaded_label)

        status_bar.addWidget(self._status_container, 1)

    @staticmethod
    def _format_status_ts(raw_ts: str) -> str:
        """
        DB-beli időbélyeg ("%Y-%m-%d %H:%M:%S") megjelenítő formátumra hozása.

        Ha a formátum bármi miatt nem illeszkedik, az eredeti string-et
        adjuk vissza, hogy a statusbar sose omoljon össze emiatt.
        """
        try:
            dt = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y.%m.%d %H:%M:%S")
        except (ValueError, TypeError):
            return raw_ts

    def _on_db_saved(self, raw_ts: str) -> None:
        """
        A TransactionDatabase minden sikeres commit() után ezt hívja meg
        (lásd db.on_save feliratkozás a konstruktorban).

        FONTOS: ez az "utolsó módosítás" jelzés, NEM a kézi mentés/backup!
        Ez minden sima tétel-rögzítésre/módosításra is lefut, ezért a
        statusbart szándékosan NEM ez frissíti - lásd _on_db_backup.
        Jelenleg nincs UI-kimenete; helyben tartva arra az esetre, ha
        később mégis kellene valahol (pl. debug célra) megjeleníteni.
        """

    def _on_db_backup(self, raw_ts: str) -> None:
        """
        A TransactionDatabase.mark_backup_done() hívja meg sikeres KÉZI
        biztonsági mentés (backup fájl készítés) után
        (lásd db.on_backup feliratkozás a konstruktorban).
        """
        self.status_last_saved_label.setText(f"Utolsó mentés: {self._format_status_ts(raw_ts)}")

        # Perzisztens tárolás: app-újraindítás után is megmaradjon az
        # időbélyeg. A self.db.db_name-et használjuk kulcsként, hogy
        # dev/stabil/egyéni DB-fájlok külön kapjanak "Utolsó mentés" infót.
        set_last_backup_ts(self.db.db_name, raw_ts)

    def _on_db_restore(self, raw_ts: str) -> None:
        """
        A TransactionDatabase.mark_restore_done() hívja meg sikeres KÉZI
        visszatöltés (restore egy backup fájlból) után
        (lásd db.on_restore feliratkozás a konstruktorban).
        """
        self.status_last_loaded_label.setText(
            f"Utoljára betöltve: {self._format_status_ts(raw_ts)}"
        )

        # Perzisztens tárolás: app-újraindítás után is megmaradjon az
        # időbélyeg (lásd _on_db_backup indoklása fentebb).
        set_last_restore_ts(self.db.db_name, raw_ts)

    def _refresh_backup_restore_labels(self) -> None:
        """
        A statusbar "Utolsó mentés" / "Utoljára betöltve" feliratainak
        szinkronba hozása a jelenlegi self.db állapotával.

        Hívási pontok: konstruktor (induláskor még "—", hacsak a DB-példány
        nem hordoz örökölt last_backup_ts/last_restore_ts-t), illetve
        bármikor, amikor a self.db referencia lecserélődik és a meglévő
        állapotot meg kell jeleníteni anélkül, hogy új mentés/betöltés
        történt volna.
        """
        backup_ts = getattr(self.db, "last_backup_ts", None)
        if backup_ts:
            self.status_last_saved_label.setText(
                f"Utolsó mentés: {self._format_status_ts(backup_ts)}"
            )
        else:
            self.status_last_saved_label.setText("Utolsó mentés: —")

        restore_ts = getattr(self.db, "last_restore_ts", None)
        if restore_ts:
            self.status_last_loaded_label.setText(
                f"Utoljára betöltve: {self._format_status_ts(restore_ts)}"
            )
        else:
            self.status_last_loaded_label.setText("Utoljára betöltve: —")

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
        A főablak központi UI-jeleinek bekötése.

        Ide tartozik:
            - évszűrő jelzései,
            - felső navigáció oldalváltása,
            - bal oldali modulválasztó gombok.
        """
        self.year_tabs.yearChanged.connect(self.on_year_selected)
        self.year_tabs.allYearsSelected.connect(self.on_all_years)
        self.navbar.pageRequested.connect(self.set_page)
        self.btn_module_likviditas.clicked.connect(self.switch_to_likviditas_module)
        self.btn_module_aranyszamla.clicked.connect(self.switch_to_aranyszamla_module)

    def add_page(self, key: str, page: QWidget) -> None:
        """Oldal regisztrálása a stackbe."""
        if key in self.pages:
            raise ValueError(f"Page already registered: {key}")

        self.pages[key] = page
        self.page_stack.addWidget(page)

        try:
            source_file = inspect.getfile(type(page))
        except TypeError:
            source_file = "?"
        self.log.info(f"OLDAL REGISZTRÁLVA: {key} -> {source_file}")

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

        # állandó naplózás: melyik oldal, melyik fájlból
        try:
            source_file = inspect.getfile(type(page))
        except TypeError:
            source_file = "?"
        self.log.info(f"AKTÍV OLDAL: {key} -> {source_file}")

        # oldal-aktiválás hook
        if hasattr(page, "on_activated"):
            page.on_activated()

        # fallback: ha van reload, hívd
        elif hasattr(page, "reload"):
            page.reload()

        # fallback: ha van refresh, hívd
        elif hasattr(page, "refresh"):
            page.refresh()

    def _sync_module_buttons(self) -> None:
        """
        A bal oldali modulválasztó gombok vizuális állapotának frissítése.
        """

        is_likviditas = self.current_module == "likviditas"

        self.btn_module_likviditas.setChecked(is_likviditas)
        self.btn_module_aranyszamla.setChecked(not is_likviditas)

        self.btn_module_likviditas.setObjectName(
            "moduleButtonActive" if is_likviditas else "moduleButton"
        )
        self.btn_module_aranyszamla.setObjectName(
            "moduleButtonActive" if not is_likviditas else "moduleButton"
        )

        self.btn_module_likviditas.style().unpolish(self.btn_module_likviditas)
        self.btn_module_likviditas.style().polish(self.btn_module_likviditas)

        self.btn_module_aranyszamla.style().unpolish(self.btn_module_aranyszamla)
        self.btn_module_aranyszamla.style().polish(self.btn_module_aranyszamla)

    def _sync_module_ui(self) -> None:
        """
        Az aktív modulhoz tartozó főablak-UI állapot szinkronizálása.

        Likviditás:
            - évszűrő panel látszik,
            - Likviditás NavBar látszik.

        Aranyszámla:
            - évszűrő panel nem látszik,
            - Likviditás NavBar nem látszik.
        """

        is_likviditas = self.current_module == "likviditas"

        self._sync_module_buttons()
        self._left_panel.setVisible(is_likviditas)
        self.navbar.setVisible(is_likviditas)

    def switch_to_likviditas_module(self) -> None:
        """
        Likviditás modul aktiválása.
        """

        self.current_module = "likviditas"
        self._sync_module_ui()

        # Likviditás kezdőoldal visszaállítása:
        self.set_page("home")

    def switch_to_aranyszamla_module(self) -> None:
        """
        Aranyszámla modul aktiválása.

        """

        self.current_module = "aranyszamla"
        self._sync_module_ui()

        # Aranyszámla kezdőoldal visszaállítása:
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
        for page in self.pages.values():
            if hasattr(page, "bind_db"):
                page.bind_db(self.db)

        # és frissítsünk mindent, ami tud reload-ot
        for page in self.pages.values():
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
            # Nem váltunk automatikusan a Tranzakciók oldalra.
            # Minden regisztrált oldal frissül, amely támogatja a reload() függvényt.
            self.reload_all_pages()

    def on_new_gold_trade(self) -> None:
        """Aranyszámla modul: vétel/eladás varázsló megnyitása."""

        wiz = GoldTradeWizard(self.db.db_name, parent=self)

        if wiz.exec() == QDialog.DialogCode.Accepted:
            # Mentés után frissítjük az Aranyszámla modult,
            # de nem váltunk át másik oldalra.
            aranyszamla_page = self.pages.get("aranyszamla_home")

            if aranyszamla_page and hasattr(aranyszamla_page, "refresh"):
                aranyszamla_page.refresh()

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

        from penzugyi_naplo.db.transaction_database import TransactionDatabase

        db_path = Path(self.db.db_name)

        # Régi TransactionDatabase-példány elengedése és egy explicit
        # gc.collect(), hogy minden esetlegesen még élő sqlite3 kapcsolat
        # (pl. egy éppen véget érő "with ... as conn:" blokkból) biztosan
        # felszabaduljon, mielőtt a fájlt töröljük. Windows alatt egy nyitva
        # felejtett kapcsolat zárolva tartja a fájlt, ez okozta a
        # "PermissionError: ... más folyamat használja" hibát.
        if hasattr(self.db, "close"):
            self.db.close()
        self.db = None
        gc.collect()

        if db_path.exists():
            last_error: PermissionError | None = None
            for _ in range(5):
                try:
                    db_path.unlink()
                    last_error = None
                    break
                except PermissionError as exc:
                    last_error = exc
                    gc.collect()
                    time.sleep(0.2)

            if last_error is not None:
                QMessageBox.critical(
                    self,
                    "Adatbázis törlése sikertelen",
                    "Az adatbázis-fájl más folyamat által zárolva van, ezért nem törölhető.\n\n"
                    "Zárd be az adatbázist esetleg megnyitó egyéb programokat "
                    "(pl. DB Browser for SQLite, VSCode SQLite kiterjesztés), "
                    "majd próbáld újra.\n\n"
                    f"Részletek: {last_error}",
                )
                # Az app működőképes maradjon: visszaállítjuk a kapcsolatot a meglévő fájlra.
                self.db = TransactionDatabase(str(db_path))
                return

        # A perzisztens "Utolsó mentés" / "Utoljára betöltve" bejegyzések
        # törlése is szükséges: a db_path (fájlnév) reset után ugyanaz
        # marad, tehát enélkül a régi időbélyeg a következő induláskor
        # tévesen visszaszivárogna, holott az új, üres DB-nek nincs
        # backup/restore előzménye.
        clear_backup_restore_status(db_path)

        self.db = TransactionDatabase(str(db_path))

        # Fontos: új TransactionDatabase példány = új, üres feliratkozó-listák,
        # ezért a statusbar jelzéseit újra be kell kötni rá, különben a reset
        # utáni kézi mentések/betöltések nem frissítenék a statusbart.
        self.db.on_save(self._on_db_saved)
        self.db.on_backup(self._on_db_backup)
        self.db.on_restore(self._on_db_restore)

        # Az adatbázis-törlés se kézi mentésnek, se kézi visszatöltésnek nem
        # számít, és az új, üres DB-példánynak nincs backup/restore előzménye
        # - ezért mindkét statusbar-felirat "—"-re áll vissza.
        self._refresh_backup_restore_labels()

        self.reload_all_pages()

        # oldalak újrakötése
        page = self.pages.get("transactions")
        if page and hasattr(page, "bind_db"):
            page.bind_db(self.db)

    def on_bill_requested(self, bill_id: int) -> None:
        # TODO: később rendes részletek

        QMessageBox.information(self, "Számla részletek", f"Bill ID: {bill_id}")

    def reload_all_pages(self) -> None:
        """
        Az összes regisztrált oldal újrakötése és frissítése.

        Új oldalnál elég reload() metódust adni az oldalnak,
        és automatikusan részt vesz a központi frissítésben.
        """

        for page in self.pages.values():
            bind_db = getattr(page, "bind_db", None)
            if callable(bind_db):
                bind_db(self.db)

        for page in self.pages.values():
            reload_method = getattr(page, "reload", None)
            if callable(reload_method):
                reload_method()

        # FONTOS: itt szándékosan NINCS "Utoljára betöltve" frissítés.
        # Ez a metódus minden sima oldal-frissítéskor lefut (pl. egy új
        # tétel rögzítése után is), és a statusbar "Utoljára betöltve"
        # feliratának KIZÁRÓLAG a kézi visszatöltésre (restore) szabad
        # frissülnie - lásd TransactionDatabase.mark_restore_done() és
        # backup_restore_handlers.handle_restore_database().

    def show_settings_dialog(self) -> None:
        """
        Megnyitja a Beállítások ablakot.

        Megjegyzés:
            - A Beállítások korábban külön oldalként/page-ként működött.
            - Az új működés szerint külön QDialog ablak nyílik.
            - Emiatt nem set_page("settings") hívás történik,
                hanem SettingsDialog példányosítás és dialog.exec().
            - A settings_page.py később kivezethető, ha már minden régi hivatkozás megszűnt.
        """

        dialog = SettingsDialog(self)

        # Fontos:
        # A QDialog külön top-level ablak, ezért nem mindig örökli szépen
        # a MainWindow stylesheetjét. Itt kézzel ráadjuk az aktuális témát.
        dialog.setStyleSheet(self.styleSheet())

        dialog.exec()

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