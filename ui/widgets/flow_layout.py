# - penzugyi_naplo/ui/widgets/flow_layout.py
# ----------------------------------------------

"""
Egyedi Qt layout: FlowLayout (wrap/flex-szerű elrendezés)
(ui/widgets/flow_layout.py).

Kártyanézetekhez készült: balról jobbra rendez, majd sort tör, ha elfogy a szélesség.
Tipikus használat: BillsPage és más card-grid jellegű oldalak.

Topology (UI):
    MainWindow
      └─ BillsPage (ui/bills/bills_page.py)
           └─ QScrollArea + FlowLayout  ← this
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget


class FlowLayout(QLayout):
    """
    Egyszerű "flow / wrap" layout: balról jobbra pakol, majd sort tör.
    Kártyákhoz ideális (mint webes flex-wrap).
    """

    def __init__(
        self, parent: QWidget | None = None, margin: int = 0, spacing: int = 10
    ) -> None:
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items: list[QLayoutItem] = []

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0

        m = self.contentsMargins()
        effective_rect = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())

        x = effective_rect.x()
        y = effective_rect.y()
        right = effective_rect.right()

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()

            next_x = x + w + self.spacing()
            if next_x - self.spacing() > right and line_height > 0:
                x = effective_rect.x()
                y = y + line_height + self.spacing()
                next_x = x + w + self.spacing()
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, h)

        return (y + line_height - rect.y()) + m.bottom()
