# - ui/widgets/ribbon_bar.py
#  ----------------------------

"""
Szalag (RibbonBar) widget: tabok + gombok
(ui/widgets/ribbon_bar.py).

Felelősség:
    - tabos eszköztár felület gombokkal
    - gombok QAction-ekre kötése (setDefaultAction)
    - expand/collapse támogatás (pl. dupla klikk a tab sávon)
    - állapotjelzés: toggled(bool)

Nem felelőssége:
    - oldalváltás / DB logika (a MainWindow kezeli)

Topology (UI):
    MainWindow
      ├─ RibbonBar  ← this
      └─ QStackedWidget (pages)

"""


# ----- Importok -------

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

# ---- Importok vége ----


class RibbonBar(QWidget):
    toggled = Signal(bool)  # True = expanded, False = collapsed

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ribbonBar")

        # --- Fájl gomb ---
        self.file_btn = QToolButton(self)
        self.file_btn.setObjectName("ribbonFileButton")
        self.file_btn.setText("Fájl")
        self.file_btn.setPopupMode(QToolButton.InstantPopup)

        # --- Tabbar ---
        self.tabbar = QTabBar(self)
        self.tabbar.setObjectName("ribbonTabs")
        self.tabbar.setExpanding(False)
        self.tabbar.setMovable(False)

        # --- Stack (szalag tartalom) ---
        self.stack = QStackedWidget(self)
        self.stack.setObjectName("ribbonStack")

        # --- Top row: Fájl + tabok ---
        top_row = QWidget(self)
        top_row.setObjectName("ribbonTopRow")
        top_lay = QHBoxLayout(top_row)
        top_lay.setContentsMargins(6, 4, 6, 0)
        top_lay.setSpacing(6)
        top_lay.addWidget(self.file_btn, 0)
        top_lay.addWidget(self.tabbar, 1)

        # --- Elválasztók (két külön példány) ---
        line_top = QFrame(self)
        line_top.setObjectName("ribbonLineTop")
        line_top.setFrameShape(QFrame.HLine)
        line_top.setFrameShadow(QFrame.Sunken)

        line_bottom = QFrame(self)
        line_bottom.setObjectName("ribbonLineBottom")
        line_bottom.setFrameShape(QFrame.HLine)
        line_bottom.setFrameShadow(QFrame.Sunken)

        # --- Layout ---
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(top_row)
        root.addWidget(line_top)
        root.addWidget(self.stack)
        root.addWidget(line_bottom)

        # --- Viselkedés ---
        self.tabbar.currentChanged.connect(self.stack.setCurrentIndex)

        # Magasság: legyen stabil, de ne roppanjon
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self._expanded_height = 128
        self._collapsed_height = self.tabbar.sizeHint().height() + 18
        self._expanded = True
        self.setFixedHeight(self._expanded_height)

        self.tabbar.tabBarDoubleClicked.connect(self._toggle_collapse)

    def add_tab(self, title: str) -> QWidget:
        idx = self.tabbar.addTab(title)

        page = QWidget(self)
        lay = QHBoxLayout(page)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)
        lay.addStretch(1)

        self.stack.insertWidget(idx, page)
        if self.tabbar.count() == 1:
            self.tabbar.setCurrentIndex(0)
            self.stack.setCurrentIndex(0)
        return page

    def add_action_button(
        self, tab_page: QWidget, action, *, text_under_icon: bool = True
    ) -> QToolButton:
        lay = tab_page.layout()
        btn = QToolButton(tab_page)
        btn.setDefaultAction(action)
        btn.setToolButtonStyle(
            Qt.ToolButtonTextUnderIcon
            if text_under_icon
            else Qt.ToolButtonTextBesideIcon
        )
        btn.setAutoRaise(False)
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # a stretch elé szúrjuk (utolsó elem a stretch)
        lay.insertWidget(lay.count() - 1, btn)
        return btn

    def _toggle_collapse(self, index: int) -> None:
        self._expanded = not self._expanded
        self.setFixedHeight(
            self._expanded_height if self._expanded else self._collapsed_height
        )
        self.stack.setVisible(self._expanded)
        self.toggled.emit(self._expanded)

    def add_separator(self, tab_page: QWidget, *, spacing: int = 16) -> None:
        lay = tab_page.layout()

        lay.insertSpacing(lay.count() - 1, spacing)

        sep = QFrame(tab_page)
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        lay.insertWidget(lay.count() - 1, sep)
        lay.insertSpacing(lay.count() - 1, spacing)
