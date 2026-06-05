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
                        
        <h2>0.1.1 – 2026-06-05</h2>
        <ul>
            <li>Aláírt APT szoftverforrás létrehozása GitHub Pages alapon.</li>
            <li><code>InRelease</code> és <code>Release.gpg</code> fájlok generálása GPG aláírással.</li>
            <li>Publikus APT kulcs hozzáadása.</li>
            <li><code>.sources</code> + <code>Signed-By</code> alapú telepítési forrás támogatása.</li>
            <li>GitHub Actions workflow hozzáadása az APT repository publikálásához.</li>
        </ul>

        <h2>0.1.0 – 2026-06-01</h2>
        <ul>
            <li>Első helyi tesztelésre szánt DEB csomag.</li>
            <li>Alkalmazásikon, desktop bejegyzés és alap telepítési struktúra hozzáadása.</li>
            <li>Függőségek és csomagtartalom tisztítása.</li>
        </ul>

        <h2>4.5 – 2026-04-22-23</h2>
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