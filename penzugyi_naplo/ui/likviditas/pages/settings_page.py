from __future__ import annotations

import sys
from shutil import copy2
from typing import Optional

from PySide6.QtCore import QProcess, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
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
    active_db_path,
    dev_db_path,
    is_dev_mode,
    prod_db_path,
    set_dev_mode,

)


class SettingsPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._settings = QSettings(ORG_NAME, APP_NAME)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # -------------------------
        # Bal oldali menü
        # -------------------------
        self.side_list = QListWidget()
        self.side_list.setFixedWidth(200)

        outer.addWidget(self.side_list)

        # -------------------------
        # Jobb oldali stack
        # -------------------------
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        # Oldalak létrehozása
        self.page_general = self._build_general_page()
        self.page_display = self._build_display_page()
        self.page_dev = self._build_dev_page()

        self.stack.addWidget(self.page_general)
        self.stack.addWidget(self.page_display)
        self.stack.addWidget(self.page_dev)

        # Menü elemek
        for text in ["🧩 Általános", "🎨 Megjelenítés", "🛠 Fejlesztői"]:
            self.side_list.addItem(QListWidgetItem(text))

        self.side_list.setCurrentRow(0)
        self.side_list.currentRowChanged.connect(
            lambda row: self.stack.setCurrentIndex(row)
        )

        # Load
        self._load_values()

    # =========================================================
    # PAGE BUILDERS
    # =========================================================

    def _build_general_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Általános beállítások")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addSpacing(10)

        layout.addWidget(QLabel("Normál adatbázis helye:"))
        self.txt_prod_db = QLineEdit(str(prod_db_path()))
        self.txt_prod_db.setReadOnly(True)
        layout.addWidget(self.txt_prod_db)

        layout.addStretch(1)
        return page

    def _build_display_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Megjelenítés")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addSpacing(10)

        # Toolbar
        row_ui = QHBoxLayout()
        row_ui.addWidget(QLabel("Eszköztár típusa:"))

        self.cmb_toolbar = QComboBox()
        self.cmb_toolbar.addItem("Menüsor", "menubar")
        self.cmb_toolbar.addItem("Szalag", "ribbon")

        row_ui.addWidget(self.cmb_toolbar, 1)
        layout.addLayout(row_ui)

        # Style
        row_style = QHBoxLayout()
        row_style.addWidget(QLabel("Stílus:"))

        self.cmb_style = QComboBox()
        self.cmb_style.addItem("Classic", STYLE_CLASSIC)
        self.cmb_style.addItem("Modern", STYLE_MODERN)
        self.cmb_style.addItem("Modern Home", STYLE_MODERN_HOME)

        row_style.addWidget(self.cmb_style, 1)
        layout.addLayout(row_style)

        # Search
        # --- 2) Keresés: alapértelmezett hatókör ---
        # Itt azt állítjuk be, hogy az app indításkor alapból
        # csak az aktív évben vagy minden évben keressen.
        search_scope_row = QHBoxLayout()

        search_scope_label = QLabel("Keresés alapértelmezett hatóköre:", self)

        self.cmb_search_scope = QComboBox(self)
        self.cmb_search_scope.addItem("Aktuális év", "active_year")
        self.cmb_search_scope.addItem("Minden év", "all_years")
        self.cmb_search_scope.setMinimumWidth(180)

        search_scope_row.addWidget(search_scope_label)
        search_scope_row.addWidget(self.cmb_search_scope)
        search_scope_row.addStretch(1)

        layout.addLayout(search_scope_row)

        layout.addStretch(1)

        # Signals
        self.cmb_toolbar.currentIndexChanged.connect(self._on_toolbar_changed)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        
        self.cmb_search_scope.currentIndexChanged.connect(
            self._on_search_scope_changed
        )

        return page

    def _build_dev_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Fejlesztői mód")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        layout.addSpacing(10)

        # DEV checkbox
        self.chk_dev_mode = QCheckBox("Fejlesztői mód bekapcsolása")
        layout.addWidget(self.chk_dev_mode)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # DB paths
        layout.addWidget(QLabel("DEV adatbázis helye:"))
        self.txt_dev_db = QLineEdit(str(dev_db_path()))
        self.txt_dev_db.setReadOnly(True)
        layout.addWidget(self.txt_dev_db)

        layout.addWidget(QLabel("Aktív adatbázis:"))
        self.txt_active_db = QLineEdit(str(active_db_path()))
        self.txt_active_db.setReadOnly(True)
        layout.addWidget(self.txt_active_db)

        # Copy button
        self.btn_copy_db = QPushButton("PROD → DEV másolás")
        layout.addWidget(self.btn_copy_db)

        layout.addStretch(1)

        # Signals
        self.chk_dev_mode.toggled.connect(self._on_dev_mode_changed)
        self.btn_copy_db.clicked.connect(self._on_copy_db_clicked)

        return page

    # =========================================================
    # LOAD / SAVE
    # =========================================================

    def _load_values(self) -> None:
       # --- toolbar_mode ---
        self.cmb_toolbar.blockSignals(True)

        toolbar_mode = str(self._settings.value("ui/toolbar_mode", "menubar"))

        if toolbar_mode not in ("menubar", "ribbon"):
            toolbar_mode = "menubar"

        for i in range(self.cmb_toolbar.count()):
            if self.cmb_toolbar.itemData(i) == toolbar_mode:
                self.cmb_toolbar.setCurrentIndex(i)
                break

        self.cmb_toolbar.blockSignals(False)

        # --- style_mode ---
        self.cmb_style.blockSignals(True)
        style = str(self._settings.value(SETTINGS_KEY_STYLE_MODE, DEFAULT_STYLE_MODE))
        for i in range(self.cmb_style.count()):
            if self.cmb_style.itemData(i) == style:
                self.cmb_style.setCurrentIndex(i)
                break
        self.cmb_style.blockSignals(False)

        # --- search_scope ---
        self.cmb_search_scope.blockSignals(True)

        search_scope = str(self._settings.value("ui/search_scope", "active_year"))

        if search_scope not in ("active_year", "all_years"):
            search_scope = "active_year"

        for i in range(self.cmb_search_scope.count()):
            if self.cmb_search_scope.itemData(i) == search_scope:
                self.cmb_search_scope.setCurrentIndex(i)
            break

        self.cmb_search_scope.blockSignals(False)

        # --- dev_mode (FONTOS) ---
        self.chk_dev_mode.blockSignals(True)
        self.chk_dev_mode.setChecked(is_dev_mode())
        self.chk_dev_mode.blockSignals(False)

        # frissítsük a mezőket is (nem triggerel semmit)
        self.txt_prod_db.setText(str(prod_db_path()))
        self.txt_dev_db.setText(str(dev_db_path()))
        self.txt_active_db.setText(str(active_db_path()))

        # =========================================================
        # EVENTS
        # =========================================================

    def _on_toolbar_changed(self) -> None:
        mode = str(self.cmb_toolbar.currentData())
        self._settings.setValue("ui/toolbar_mode", mode)

        mw = self.window()
        if hasattr(mw, "set_toolbar_mode"):
            try:
                mw.set_toolbar_mode(mode)
            except Exception:
                pass

    def _on_search_scope_changed(self) -> None:
        """
        A keresés alapértelmezett hatókörének mentése.

        Ez csak az alapértéket menti.
        A tranzakciós oldalon lévő keresősáv ezt induláskor visszaolvassa,
        de ott később ideiglenesen felülírható lesz.
        """
        search_scope = self.cmb_search_scope.currentData()

        if search_scope not in ("active_year", "all_years"):
            search_scope = "active_year"

        self._settings.setValue("ui/search_scope", search_scope)
        self._settings.sync()

    def _on_dev_mode_changed(self, checked: bool) -> None:
        current = is_dev_mode()

        # Ha valamiért ugyanaz, ne csináljunk semmit
        if checked == current:
            return

        # Rákérdezés
        action = "bekapcsolása" if checked else "kikapcsolása"
        res = QMessageBox.question(
            self,
            "Fejlesztői mód",
            f"Biztosan szeretnéd a fejlesztői módot {action}?\n\n"
            "Az alkalmazás újra fog indulni.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if res != QMessageBox.StandardButton.Yes:
            # Nem -> vissza az előző állapotra, és semmit nem mentünk
            self.chk_dev_mode.blockSignals(True)
            self.chk_dev_mode.setChecked(current)
            self.chk_dev_mode.blockSignals(False)
            return

        # Igen -> mentés
        set_dev_mode(bool(checked))

        # UI mezők frissítése (még kilépés előtt)
        self.txt_active_db.setText(str(active_db_path()))

        # Újraindítás (ugyanazzal a python + argv-vel)
        QApplication.processEvents()
        QProcess.startDetached(sys.executable, sys.argv)
        QApplication.quit()

    def _on_copy_db_clicked(self) -> None:
        src = prod_db_path()
        dst = dev_db_path()

        if not src.exists():
            QMessageBox.warning(
                self,
                "Nincs forrás DB",
                f"A normál adatbázis nem található:\n{src}",
            )
            return

        try:
            copy2(src, dst)
            QMessageBox.information(
                self,
                "Kész",
                "A normál adatbázis átmásolva a DEV adatbázisba.",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Hiba",
                f"Másolási hiba:\n{e}",
            )

    def _on_style_changed(self) -> None:
        mode = str(self.cmb_style.currentData())

        if mode not in (STYLE_CLASSIC, STYLE_MODERN, STYLE_MODERN_HOME):
            return

        self._settings.setValue(SETTINGS_KEY_STYLE_MODE, mode)
        self._settings.sync()

        mw = self.window()
        if hasattr(mw, "apply_style_mode"):
            try:
                mw.apply_style_mode(mode)
            except Exception:
                pass