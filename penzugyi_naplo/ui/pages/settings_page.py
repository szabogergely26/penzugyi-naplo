# - penzugyi_naplo/ui/pages/settings_page.py
# -----------------------------------------------

"""
Beállítások oldal a fő alkalmazásban
(ui/pages/settings_page.py).

Felelősség:
    - felhasználói beállítások megjelenítése és mentése (QSettings)

Kezelt opciók (jelenleg):
    - eszköztár típusa (menüsor / szalag)
    - keresés hatóköre (csak aktív év / minden év)

Integráció:
    - bizonyos beállítások azonnal érvényesülnek, ha a MainWindow támogatja
      (pl. set_toolbar_mode, filter all_years)

Bővíthetőség:
    - téma, backup, import/export későbbi helye

Topology (UI):
    MainWindow
      └─ SettingsPage  ← this
"""


# ---- Importok ------

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QDialog,
)

from penzugyi_naplo.config import (
    APP_NAME, 
    ORG_NAME,
    SETTINGS_KEY_STYLE_MODE,
    STYLE_CLASSIC,
    STYLE_MODERN,
    STYLE_MODERN_HOME,
    DEFAULT_STYLE_MODE,
    )

# ------ Importok vége -----


# ------ SettingsPage osztály -----


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # A SettingsDialog parentje a MainWindow.
        # Így innen közvetlenül elérjük a MainWindow metódusait.
        self.main_window = parent

        self.setWindowTitle("Beállítások")
        self.resize(720, 480)

        self._settings = QSettings(ORG_NAME, APP_NAME)

        self.setObjectName("settingsPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel("Beállítások", self)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setObjectName("pageTitle")
        root.addWidget(title)

        hint = QLabel(
            "Felület, keresés, és később téma/backup/import-export beállítások.", self
        )
        hint.setWordWrap(True)
        hint.setObjectName("pageHint")
        root.addWidget(hint)
        
        
        sep = QFrame(self)
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep)

        # --- 1) Felület: Menüsor / Szalag ---
        row_ui = QHBoxLayout()
        lbl_ui = QLabel("Eszköztár típusa:", self)
        self.cmb_toolbar = QComboBox(self)
        self.cmb_toolbar.addItem("Menüsor", "menubar")
        self.cmb_toolbar.addItem("Szalag", "ribbon")

        row_ui.addWidget(lbl_ui)
        row_ui.addWidget(self.cmb_toolbar, 1)
        root.addLayout(row_ui)

        # --- 2) Téma (stílus) ---
        row_style = QHBoxLayout()
        lbl_style = QLabel("Téma:", self)

        self.cmb_style = QComboBox(self)
        self.cmb_style.addItem("Classic", STYLE_CLASSIC)
        self.cmb_style.addItem("Modern", STYLE_MODERN)
        self.cmb_style.addItem("Modern Home", STYLE_MODERN_HOME)

        row_style.addWidget(lbl_style)
        row_style.addWidget(self.cmb_style, 1)
        root.addLayout(row_style)

        # --- 2) Keresés: minden évben (váz) ---
        self.chk_search_all_years = QCheckBox(
            "Keresés minden évben (ne csak az aktív évben)", self
        )
        root.addWidget(self.chk_search_all_years)

        root.addStretch(1)

        # --- Betöltés + események ---
        self._load_values()
        self.cmb_toolbar.currentIndexChanged.connect(self._on_toolbar_changed)
        self.cmb_style.currentIndexChanged.connect(self._on_style_changed)
        self.chk_search_all_years.toggled.connect(self._on_search_all_years_changed)

    # -------------------------
    # Load / Save
    # -------------------------
    def _load_values(self) -> None:
        mode = str(self._settings.value("ui/toolbar_mode", "menubar"))
        if mode not in ("menubar", "ribbon"):
            mode = "menubar"

        # combobox adat alapján állítjuk
        for i in range(self.cmb_toolbar.count()):
            if self.cmb_toolbar.itemData(i) == mode:
                self.cmb_toolbar.setCurrentIndex(i)
                break

        all_years = bool(self._settings.value("ui/search_all_years", True))
        self.chk_search_all_years.setChecked(all_years)

        # --- STYLE ---
        style = str(self._settings.value(SETTINGS_KEY_STYLE_MODE, DEFAULT_STYLE_MODE))

        for i in range(self.cmb_style.count()):
            if self.cmb_style.itemData(i) == style:
                self.cmb_style.setCurrentIndex(i)
                break







    def _on_toolbar_changed(self) -> None:
        mode = str(self.cmb_toolbar.currentData())

        if mode not in ("menubar", "ribbon"):
            return

        self._settings.setValue("ui/toolbar_mode", mode)

        # QDialog esetén a self.window() már maga a dialog lehet,
        # ezért a MainWindow-t a parentként eltett self.main_window alapján érjük el.
        if hasattr(self.main_window, "set_toolbar_mode"):
            try:
                self.main_window.set_toolbar_mode(mode)
            except Exception as e:
                if hasattr(self, "status_label"):
                    self.status_label.setText(
                        "Az eszköztár módja mentve lett, de csak újraindítás után lép teljesen életbe."
                    )
                print("DEBUG: toolbar mode live apply failed:", e)





    def _on_search_all_years_changed(self, checked: bool) -> None:
        self._settings.setValue("ui/search_all_years", bool(checked))





    def _on_style_changed(self) -> None:
        mode = str(self.cmb_style.currentData())

        if mode not in (STYLE_CLASSIC, STYLE_MODERN, STYLE_MODERN_HOME):
            return

        self._settings.setValue(SETTINGS_KEY_STYLE_MODE, mode)

        # Live apply a MainWindow-n.
        if hasattr(self.main_window, "apply_style_mode"):
            try:
                self.main_window.apply_style_mode(mode)

                if hasattr(self, "status_label"):
                    self.status_label.setText("A téma frissítve lett.")

            except Exception as e:
                if hasattr(self, "status_label"):
                    self.status_label.setText(
                        "A téma mentve lett, de csak újraindítás után lép teljesen életbe."
                    )
                print("DEBUG: style live apply failed:", e)
        