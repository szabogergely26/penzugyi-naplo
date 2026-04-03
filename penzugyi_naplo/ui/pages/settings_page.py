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

from typing import Optional

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

# ------ Importok vége -----


# ------ SettingsPage osztály -----


class SettingsPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._settings = QSettings("SzaboG", "PenzugyiNaplo")

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

        # --- 2) Keresés: minden évben (váz) ---
        self.chk_search_all_years = QCheckBox(
            "Keresés minden évben (ne csak az aktív évben)", self
        )
        root.addWidget(self.chk_search_all_years)

        root.addStretch(1)

        # --- Betöltés + események ---
        self._load_values()
        self.cmb_toolbar.currentIndexChanged.connect(self._on_toolbar_changed)
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

    def _on_toolbar_changed(self) -> None:
        mode = str(self.cmb_toolbar.currentData())
        if mode not in ("menubar", "ribbon"):
            return

        self._settings.setValue("ui/toolbar_mode", mode)

        # Ha a parent MainWindow tudja kezelni, akkor azonnali váltás
        mw = self.window()
        if hasattr(mw, "set_toolbar_mode"):
            try:
                mw.set_toolbar_mode(mode)  # MainWindow metódus
            except Exception:
                pass

    def _on_search_all_years_changed(self, checked: bool) -> None:
        self._settings.setValue("ui/search_all_years", bool(checked))
