from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout


class VersionHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Verziótörténet")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        browser = QTextBrowser(self)
        browser.setHtml("""
        <h1>Verziótörténet – Pénzügyi Napló</h1>

        <h2>4.5 – 2026-04-22</h2>
        <ul>
            <li>Névjegy ablak main ághoz igazítva</li>
            <li>Fejlesztés kezdete megjelenítve</li>
        </ul>

        <h2>4.6-dev – folyamatban</h2>
        <ul>
            <li>Fejlesztői About dialog előkészítése</li>
            <li>Új style előkészítése</li>
        </ul>
        """)

        btn_close = QPushButton("Bezár", self)
        btn_close.clicked.connect(self.accept)

        layout.addWidget(browser)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)