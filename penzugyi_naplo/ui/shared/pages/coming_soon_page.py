from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class ComingSoonPage(QWidget):
    def __init__(
        self, title: str = "Hamarosan", msg: str = "Ez a funkció hamarosan érkezik."
    ):
        super().__init__()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        h1 = QLabel(title)
        h1.setObjectName("comingSoonTitle")
        h1.setAlignment(Qt.AlignLeft)

        box = QFrame()
        box.setObjectName("comingSoonBox")
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(16, 16, 16, 16)
        box_lay.setSpacing(8)

        info = QLabel(msg)
        info.setWordWrap(True)
        info.setObjectName("comingSoonText")

        hint = QLabel("💡 Tipp: Kapcsold be a DEV módot a teszteléshez.")
        hint.setWordWrap(True)
        hint.setObjectName("comingSoonHint")

        box_lay.addWidget(info)
        box_lay.addWidget(hint)

        lay.addWidget(h1)
        lay.addWidget(box, 0, Qt.AlignTop)
        lay.addStretch(1)
