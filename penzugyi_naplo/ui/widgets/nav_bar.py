"""
Felső navigációs sáv (NavBar)
(ui/widgets/nav_bar.py).

Felelősség:
    - oldalgombok megjelenítése (home / transactions / statistics / bills / settings)
    - navigáció kérése a MainWindow felé: pageRequested(str)

Nem felelőssége:
    - oldalváltás végrehajtása (ezt a MainWindow intézi)
    - DB/üzleti logika
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QWidget


def v_separator(
    parent: QWidget | None = None, object_name: str = "navSeparator"
) -> QFrame:
    """
    Egyszerű vertikális elválasztó QHBoxLayout-hoz.

    Elv:
      - NINCS hardcode méret/szín Pythonból
      - csak objectName → style.qss (#navSeparator) stílusolja
    """
    sep = QFrame(parent)
    sep.setObjectName(object_name)
    sep.setFrameShape(QFrame.VLine)
    sep.setFrameShadow(QFrame.Plain)
    return sep


class NavBar(QFrame):
    """Felső navigációs sáv (pageRequested jelzéssel)."""

    pageRequested = Signal(str)

    # stabil, egy helyen karbantartható sorrend + felirat
    PAGE_ORDER: tuple[tuple[str, str], ...] = (
        ("home", "Kezdő"),
        ("transactions", "Tranzakciók"),
        ("statistics", "Statisztika"),
        ("bills", "Számlák"),
        ("accounts", "Pénztárcák"),
        ("settings", "Beállítások"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}

        # QSS hook
        self.setObjectName("navBar")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        # --- Fő navigáció (settings előtt) ---
        for key, text in self.PAGE_ORDER:
            if key == "settings":
                break
            self._add_btn(lay, key, text)

        lay.addStretch(1)

        # --- elválasztó ---
        lay.addWidget(v_separator(self))

        # --- settings ---
        self._add_btn(lay, "settings", "Beállítások")

        lay.addStretch(10)

    def _add_btn(self, lay: QHBoxLayout, key: str, text: str) -> None:
        btn = QPushButton(text, self)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)

        # QSS hookok
        btn.setObjectName("navSettings" if key == "settings" else "navButton")

        btn.clicked.connect(lambda _=False, k=key: self.request_page(k))
        lay.addWidget(btn)
        self._buttons[key] = btn

    def request_page(self, key: str) -> None:
        """Külső hívásból is kérhető oldalváltás (menü/ribbon/teszt)."""
        self.pageRequested.emit(key)

    def set_active(self, key: str) -> None:
        """Aktív gomb kijelölése (QSS :checked állapothoz)."""
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setChecked(True)
