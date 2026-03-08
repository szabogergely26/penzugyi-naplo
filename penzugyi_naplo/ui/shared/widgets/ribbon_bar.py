from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class RibbonBar(QWidget):
    toggled = Signal(bool)  # True = expanded (pinned), False = collapsed

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
        self.top_row = QWidget(self)
        self.top_row.setObjectName("ribbonTopRow")
        top_lay = QHBoxLayout(self.top_row)
        top_lay.setContentsMargins(6, 4, 6, 0)
        top_lay.setSpacing(6)
        top_lay.addWidget(self.file_btn, 0)
        top_lay.addWidget(self.tabbar, 1)

        # --- Elválasztók ---
        self.line_top = QFrame(self)
        self.line_top.setObjectName("ribbonLineTop")
        self.line_top.setFrameShape(QFrame.NoFrame)
        self.line_top.setFixedHeight(1)

        self.line_bottom = QFrame(self)
        self.line_bottom.setObjectName("ribbonLineBottom")
        self.line_bottom.setFrameShape(QFrame.NoFrame)
        self.line_bottom.setFixedHeight(10)  # shadow strip (expanded/overlay alatt)

        # --- Layout (PINNED módban a stack itt van!) ---
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)
        self._root.addWidget(self.top_row)
        self._root.addWidget(self.line_top)
        self._root.addWidget(self.stack)
        self._root.addWidget(self.line_bottom)

        # --- Viselkedés ---
        self.tabbar.currentChanged.connect(self._on_tab_changed)
        self.tabbar.tabBarDoubleClicked.connect(self._toggle_pinned)

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # Állapotok
        self._expanded_height = 100
        self._expanded = True  # pinned expanded
        self._temporary_open = False  # collapsed + overlay nyitva

        # indulás: pinned expanded
        self.setFixedHeight(self._expanded_height)
        self.stack.setVisible(True)
        self.line_bottom.setVisible(True)

        # Global click/esc figyelés (overlay záráshoz)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        # --- Overlay panel (NEM Qt.Popup!) ---
        # Tool + frameless + ShowWithoutActivating: nem tol, nem rángat, nem zavarja a menüt.
        self._overlay = QFrame(self.window())
        self._overlay.setObjectName("ribbonPopup")
        self._overlay.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self._overlay.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._overlay.setFocusPolicy(Qt.NoFocus)

        ov_lay = QVBoxLayout(self._overlay)
        ov_lay.setContentsMargins(0, 0, 0, 0)
        ov_lay.setSpacing(0)

        # Overlay tartalom konténer (ide költöztetjük át ideiglenesen a stack-et)
        self._overlay_host = QWidget(self._overlay)
        host_lay = QVBoxLayout(self._overlay_host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(0)
        ov_lay.addWidget(self._overlay_host)

        self._overlay.hide()

        self._shadow_strip = QFrame(self._overlay)
        self._shadow_strip.setObjectName("ribbonPopupShadow")
        self._shadow_strip.setFrameShape(QFrame.NoFrame)
        self._shadow_strip.setFixedHeight(8)

        ov_lay.addWidget(self._overlay_host)
        ov_lay.addWidget(self._shadow_strip)

    # -------- Tab change --------

    def _on_tab_changed(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)

        # Collapsed módban tabváltásra: ideiglenes overlay nyitás
        if not self._expanded:
            self._open_temporarily()

    # -------- Pinned toggle (double click) --------

    def _toggle_pinned(self, index: int) -> None:
        # Ha épp overlay nyitva volt, előbb zárjuk (különben összeakad)
        if self._temporary_open:
            self._close_temporarily()

        self._expanded = not self._expanded

        if self._expanded:
            # PINNED EXPANDED (layoutos)
            self._ensure_stack_in_ribbon()
            self.stack.setVisible(True)
            self.line_bottom.setVisible(True)
            self.setFixedHeight(self._expanded_height)
        else:
            # COLLAPSED (layoutban csak top_row + line_top marad)
            self._ensure_stack_in_ribbon()
            self.stack.setVisible(False)
            self.line_bottom.setVisible(False)
            h = self.top_row.sizeHint().height() + self.line_top.height()
            self.setFixedHeight(h)

        self.toggled.emit(self._expanded)

    # -------- Temporary overlay open/close --------

    def _open_temporarily(self) -> None:
        if self._expanded or self._temporary_open:
            return

        self._temporary_open = True

        # Collapsed magasság marad (NE toljon!)
        h = self.top_row.sizeHint().height() + self.line_top.height()
        self.setFixedHeight(h)
        self.stack.setVisible(False)
        self.line_bottom.setVisible(False)

        self._move_stack_to_overlay()
        self._position_overlay()
        self.stack.setVisible(True)
        self._overlay.show()

    def _close_temporarily(self) -> None:
        if not self._temporary_open:
            return

        self._temporary_open = False
        self._overlay.hide()
        self.stack.setVisible(False)

        self._move_stack_back_to_ribbon()

        # marad collapsed
        self.stack.setVisible(False)
        self.line_bottom.setVisible(False)
        h = self.top_row.sizeHint().height() + self.line_top.height()
        self.setFixedHeight(h)

    # -------- Overlay mechanics --------

    def _position_overlay(self) -> None:
        w = self.window()
        if w is None:
            return

        # A ribbonBar saját globál bal/jobb széle (EZ a helyes “container”)
        tl = self.mapToGlobal(self.rect().topLeft())
        tr = self.mapToGlobal(self.rect().topRight())

        left = tl.x()
        width = (tr.x() - tl.x()) + 1

        # y: a top_row alja globálban
        p = self.top_row.mapToGlobal(self.top_row.rect().bottomLeft())
        y = p.y() + self.line_top.height()

        height = max(
            80,
            self._expanded_height
            - (self.top_row.sizeHint().height() + self.line_top.height()),
        )

        self._overlay.resize(width, height)
        self._overlay.move(left, y)

    def _move_stack_to_overlay(self) -> None:
        # kivevés a ribbon layoutból (ha ott lenne)
        self._root.removeWidget(self.stack)
        self.stack.setParent(self._overlay_host)
        self._overlay_host.layout().addWidget(self.stack)

    def _move_stack_back_to_ribbon(self) -> None:
        # kivesszük az overlay hostból
        self._overlay_host.layout().removeWidget(self.stack)
        self.stack.setParent(self)
        # vissza a ribbon layoutba a line_top után
        self._root.insertWidget(2, self.stack)

    def _ensure_stack_in_ribbon(self) -> None:
        # ha valamiért overlayben maradt volna
        if self.stack.parent() is not self:
            self._move_stack_back_to_ribbon()

    # -------- Global close rules (click outside / ESC) --------

    def eventFilter(self, obj, event) -> bool:
        if not self._temporary_open:
            return super().eventFilter(obj, event)

        et = event.type()

        # ESC -> zár
        if et == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            self._close_temporarily()
            return True

        # Kattintás ribbon+overlayen kívül -> zár (de NE nyeljük le)
        if et == QEvent.MouseButtonPress:
            gp = event.globalPosition().toPoint()

            in_ribbon = self.rect().contains(self.mapFromGlobal(gp))
            in_overlay = (
                self._overlay.isVisible() and self._overlay.geometry().contains(gp)
            )

            # Ha a user menüt nyit (QMenu) – azt is overlay-nek tekintjük, különben villogna.
            in_menu = False
            aw = QApplication.activePopupWidget()
            if aw is not None and aw.isVisible():
                try:
                    in_menu = aw.geometry().contains(gp)
                except Exception:
                    in_menu = False

            if not in_ribbon and not in_overlay and not in_menu:
                self._close_temporarily()
                return False

        # ablak resize / mozgatás esetén igazítsuk az overlayt
        if et in (QEvent.Resize, QEvent.Move):
            if self._overlay.isVisible():
                self._position_overlay()

        return super().eventFilter(obj, event)

    # -------- API: tabs/buttons/separators --------

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
        lay.insertWidget(lay.count() - 1, btn)
        return btn

    def add_separator(self, tab_page: QWidget, *, spacing: int = 16) -> None:
        lay = tab_page.layout()
        lay.insertSpacing(lay.count() - 1, spacing)

        sep = QFrame(tab_page)
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        lay.insertWidget(lay.count() - 1, sep)
        lay.insertSpacing(lay.count() - 1, spacing)
