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

        # Style (Classic/Modern)
        row_style = QHBoxLayout()
        row_style.addWidget(QLabel("Stílus:"))

        self.cmb_style = QComboBox()
        self.cmb_style.addItem("Classic", "classic")
        self.cmb_style.addItem("Modern", "modern")
        self.cmb_style.addItem("Modern Home", "modern_home")

        row_style.addWidget(self.cmb_style, 1)
        layout.addLayout(row_style)

        # Search
        self.chk_search_all_years = QCheckBox(
            "Keresés minden évben (ne csak az aktív évben)"
        )
        layout.addWidget(self.chk_search_all_years)

        layout.addStretch(1)

        # Signals
        self.cmb_toolbar.currentIndexChanged.connect(self._on_toolbar_changed)
        self.chk_search_all_years.toggled.connect(self._on_search_all_years_changed)

        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)

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
        mode = str(self._settings.value("ui/toolbar_mode", "menubar"))
        for i in range(self.cmb_toolbar.count()):
            if self.cmb_toolbar.itemData(i) == mode:
                self.cmb_toolbar.setCurrentIndex(i)
                break
        self.cmb_toolbar.blockSignals(False)

        # --- style_mode ---
        self.cmb_style.blockSignals(True)
        style = str(self._settings.value("ui/style_mode", "classic"))
        for i in range(self.cmb_style.count()):
            if self.cmb_style.itemData(i) == style:
                self.cmb_style.setCurrentIndex(i)
                break
        self.cmb_style.blockSignals(False)

        # --- search_all_years ---
        self.chk_search_all_years.blockSignals(True)
        all_years = self._settings.value("ui/search_all_years", True, type=bool)
        self.chk_search_all_years.setChecked(all_years)
        self.chk_search_all_years.blockSignals(False)

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

    def _on_search_all_years_changed(self, checked: bool) -> None:
        self._settings.setValue("ui/search_all_years", checked)

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
        self._settings.setValue("ui/style_mode", mode)
        self._settings.sync()  # optional, de jó “most rögtön” mentésre

        mw = self.window()
        if hasattr(mw, "apply_style_mode"):
            try:
                mw.apply_style_mode(mode)
            except Exception:
                pass
