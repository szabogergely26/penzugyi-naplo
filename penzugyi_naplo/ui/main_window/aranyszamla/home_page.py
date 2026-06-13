# /ui/main_window/aranyszamla/home_page.py
# -------------------------------------------

# Aranyszámla kezdő oldal: aranykupac + gramm + érték

"""
Aranyszámla kezdőoldal.

Feladata:
- az Aranyszámla modul nyitóképernyőjének megjelenítése
- füles nézet biztosítása:
  - Aranyszámla: összesített aranyszámla, fizikai termékek nélkül
  - Fizikai termékek: megvásárolt fizikai termékek diagramjai
- aranykupac / aranytartalék jellegű vizuális blokk
- összes gramm és becsült érték megjelenítése

Később:
- valós adatok bekötése adatbázisból
- fizikai termékek külön adatmodellje
- érték számítása aktuális árfolyam alapján
- finom animáció / látványelemek

Térkép az Aranyszámla oldalakhoz:

Aranyszámla fül page
└── layout
    └── hero_card
        objectName: aranyszamlaHeroCard
        Mire hat: nagy külső kártya

        └── hero_layout
            ├── visual_box
            │   objectName: aranyszamlaVisualBox
            │   Mire hat: bal oldali ikonpanel
            │
            │   ├── gold_icon
            │   │   objectName: aranyszamlaGoldIcon
            │   │   Mire hat: 🪙 emoji
            │   │
            │   └── gold_caption
            │       objectName: aranyszamlaGoldCaption
            │       Mire hat: "Aranytartalék" felirat
            │
            └── info_box
                objectName: aranyszamlaInfoBox
                Mire hat: jobb oldali információs panel

                ├── section_title
                │   objectName: aranyszamlaSectionTitle
                │   Mire hat: "Jelenlegi állapot" cím
                │
                ├── grams_label
                │   objectName: aranyszamlaInfoLabel
                │   Mire hat: "Aranyszámla" kis címke
                │
                ├── self.grams_value
                │   objectName: aranyszamlaMainValue
                │   Mire hat: nagy "0,000 g" érték
                │
                ├── estimated_label
                │   objectName: aranyszamlaInfoLabel
                │   Mire hat: "Becsült érték" kis címke
                │
                ├── self.estimated_value
                │   objectName: aranyszamlaSecondaryValue
                │   Mire hat: nagy "0 Ft" érték
                │
                └── hint
                    objectName: aranyszamlaHintText
                    Mire hat: alsó magyarázó szöveg

Konténerek, tehát mehet nekik háttér:

    - hero_card.setObjectName("aranyszamlaHeroCard")
    - visual_box.setObjectName("aranyszamlaVisualBox")
    - info_box.setObjectName("aranyszamlaInfoBox")


aranyszamlaHeroCard      = nagy külső doboz
aranyszamlaVisualBox     = bal oldali ikon doboz
aranyszamlaInfoBox       = jobb oldali infó doboz

aranyszamlaGoldIcon      = csak az emoji
aranyszamlaGoldCaption   = "Aranytartalék"
aranyszamlaSectionTitle  = címek
aranyszamlaInfoLabel     = kis címkék
aranyszamlaMainValue     = nagy gramm érték
aranyszamlaSecondaryValue= nagy forint érték
aranyszamlaHintText      = halvány magyarázó szöveg


"""

from __future__ import annotations

from pathlib import Path


from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)

from penzugyi_naplo.db.gold_database import (
    get_gold_physical_summary,
    get_gold_summary,
    list_gold_physical_items,
)



class PhysicalGoldItemCard(QFrame):
    """
    Fizikai aranytermék kártya hover-effekttel.

    Hover állapotban:
    - a kártya pár pixellel feljebb mozdul,
    - az árnyék erősebb lesz,
    - ettől olyan hatása lesz, mintha kiemelkedne a háttérből.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._normal_pos = None

    def enterEvent(self, event) -> None:
        """
        Egér ráhúzásakor enyhén megemeljük a kártyát.
        """

        if self._normal_pos is None:
            self._normal_pos = self.pos()

        # Hover-re mozgás:
        self.move(self.x(), self.y() - 20)

        shadow = self.graphicsEffect()

        if isinstance(shadow, QGraphicsDropShadowEffect):
            shadow.setBlurRadius(38)
            shadow.setOffset(0, 14)
            shadow.setColor(QColor(70, 45, 10, 120))

        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """
        Egér elhagyásakor visszaállítjuk az alap pozíciót és árnyékot.
        """

        if self._normal_pos is not None:
            self.move(self._normal_pos)

        shadow = self.graphicsEffect()

        if isinstance(shadow, QGraphicsDropShadowEffect):
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 10)
            shadow.setColor(QColor(90, 60, 15, 95))

        super().leaveEvent(event)






class AranyszamlaHomePage(QWidget):
    """
    Az Aranyszámla modul kezdőoldala.

    Fülek:
        - Aranyszámla: teljes aranyszámla, fizikai termékek nélkül
        - Fizikai termékek: fizikai aranytermékek diagramjai
    """

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)

        self.db_path = db_path

        self.setObjectName("aranyszamlaHomePage")
        self._build_ui()
        self.refresh()



    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(24)

        title = QLabel("Aranyszámla")
        title.setObjectName("aranyszamlaPageTitle")

        subtitle = QLabel("Arany megtakarításod egyszerű áttekintése")
        subtitle.setObjectName("aranyszamlaPageSubtitle")

        self.tabs = QTabWidget()
        self.tabs.setObjectName("aranyszamlaHomeTabs")

        self.account_tab = self._create_account_tab()
        self.physical_products_tab = self._create_physical_products_tab()

        self.tabs.addTab(self.account_tab, "Aranyszámla")
        self.tabs.addTab(self.physical_products_tab, "Fizikai termékek")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addWidget(self.tabs, 1)


    # Aranyszámla Tab:
        # nagy fő aranykártya, bal oldali kép blokk
        # jobb oldali infó blokk

    def _create_account_tab(self) -> QWidget:
        page = QWidget()    # ha adnák neki style-t: page.setObjectName("aranyszamlaAccountTabPage")
                            # akkor az egész fül hátterére hatna

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)


        # Aranyszámla fül : központi kártya - Teljes aranyszámla fül

        hero_card = QFrame()
        hero_card.setObjectName("aranyszamlaHeroCard")
        hero_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Ez szintén nem látható elem:
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(42, 38, 42, 38)
        hero_layout.setSpacing(36)


        # bal oldali box.
        # Csak a bal oldali aranyikonos doboz hátterére / keretére / lekerekítésére hat!.
        visual_box = QFrame()
        visual_box.setObjectName("aranyszamlaVisualBox")

        # csak elrendezés:
        visual_layout = QVBoxLayout(visual_box)
        visual_layout.setContentsMargins(24, 24, 24, 24)
        visual_layout.setSpacing(12)
        visual_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Emoji:
        gold_icon = QLabel("🪙")
        gold_icon.setObjectName("aranyszamlaGoldIcon")
        gold_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)



        # Emoji alatti szöveg:
        # QSS: QLabel#aranyszamlaGoldCaption
        gold_caption = QLabel("Aranytartalék")
        gold_caption.setObjectName("aranyszamlaGoldCaption")
        gold_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # A visual_box belsejébe függőlegesen középre igazítja
        visual_layout.addStretch(1)
        visual_layout.addWidget(gold_icon)
        visual_layout.addWidget(gold_caption)
        visual_layout.addStretch(1)


        # jobb oldali infó doboz: Jelenlegi állapot, becsült érték....
        # QSS: QFrame#aranyszamlaInfoBox
        info_box = QFrame()
        info_box.setObjectName("aranyszamlaInfoBox")

        info_layout = QVBoxLayout(info_box)
        info_layout.setContentsMargins(28, 28, 28, 28)
        info_layout.setSpacing(18)

        # Jobb oldali blokk címe:
        # QSS: QLabel#aranyszamlaSectionTitle
        section_title = QLabel("Jelenlegi állapot")
        section_title.setObjectName("aranyszamlaSectionTitle")

        grams_label = QLabel("Aranyszámla")
        grams_label.setObjectName("aranyszamlaInfoLabel")

        self.grams_value = QLabel("0,000 g")
        self.grams_value.setObjectName("aranyszamlaMainValue")

        estimated_label = QLabel("Becsült érték")
        estimated_label.setObjectName("aranyszamlaInfoLabel")

        self.estimated_value = QLabel("0 Ft")
        self.estimated_value.setObjectName("aranyszamlaSecondaryValue")

        hint = QLabel(
            "Az érték később a rögzített vásárlások, eladások és az aktuális "
            "aranyár alapján számolható."
        )
        hint.setObjectName("aranyszamlaHintText")
        hint.setWordWrap(True)


        # Elrendezés: Az info_box belsejébe egymás alá kerül a szöveg, kisebb nagyobb sorközzel.
        info_layout.addWidget(section_title)
        info_layout.addSpacing(8)
        info_layout.addWidget(grams_label)
        info_layout.addWidget(self.grams_value)
        info_layout.addSpacing(10)
        info_layout.addWidget(estimated_label)
        info_layout.addWidget(self.estimated_value)
        info_layout.addStretch(1)
        info_layout.addWidget(hint)

        hero_layout.addWidget(visual_box, 2)
        hero_layout.addWidget(info_box, 3)

        layout.addWidget(hero_card, 1)

        return page





    def _create_physical_products_tab(self) -> QWidget:
        """
        Fizikai aranytermékek fül létrehozása.

        Ez a fül a gold_physical_items táblában tárolt fizikai
        aranytermékeket jeleníti meg kártyás nézetben.

        Első körben:
        - összesítő információk
        - görgethető termékkártyák
        """

        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        card = QFrame()
        # Fizikai termékek fül nagy sárga panelje.
        # Erre kerül a "Fizikai termékek" cím, az összesítő sorok,
        # és ezen belül van a görgethető kártyaterület.
        card.setObjectName("aranyszamlaPhysicalProductsPanel")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        title = QLabel("Fizikai termékek")

        # Csak a "Fizikai termékek" cím feliratára hat.
        # Nem háttérpanel.
        title.setObjectName("aranyszamlaSectionTitle")

        self.physical_summary_label = QLabel("Összes fizikai arany: 0,000 g")

        # Csak az összes fizikai arany szövegsorra hat.
        # Nem háttérpanel.
        self.physical_summary_label.setObjectName("aranyszamlaInfoLabel")

        self.physical_value_label = QLabel("Nyilvántartott bekerülési érték: 0 Ft")

        # Csak a bekerülési érték szövegsorra hat.
        # Nem háttérpanel.
        self.physical_value_label.setObjectName("aranyszamlaInfoLabel")

        self.physical_scroll = QScrollArea()

        # A termékkártyák görgethető területe.
        # Ez az a rész, ami most fehéren maradt a kártyák mögött.
        self.physical_scroll.setObjectName("aranyszamlaPhysicalScroll")

        self.physical_scroll.setWidgetResizable(True)
        self.physical_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.physical_cards_container = QWidget()

        # A kártyák mögötti belső rács-konténer.
        # Ha ez fehér, akkor a kártyák mögött nagy fehér téglalap látszik.
        self.physical_cards_container.setObjectName("aranyszamlaPhysicalCardsContainer")

        self.physical_cards_layout = QGridLayout(self.physical_cards_container)

        # Felső margó kell, mert hover-nél a kártya felfelé mozdul.
        # Ha nincs puffer, a scroll area levágja a kártya tetejét.
        self.physical_cards_layout.setContentsMargins(0, 20, 0, 12)
        self.physical_cards_layout.setHorizontalSpacing(16)
        self.physical_cards_layout.setVerticalSpacing(12)

        self.physical_scroll.setWidget(self.physical_cards_container)

        card_layout.addWidget(title)
        card_layout.addWidget(self.physical_summary_label)
        card_layout.addWidget(self.physical_value_label)
        card_layout.addWidget(self.physical_scroll, 1)

        layout.addWidget(card, 1)

        return page





    def refresh(self) -> None:
        """
        Aranyszámla kezdőoldali összesítők frissítése.

        Frissíti:
        - az Aranyszámla fül gramm / forint összesítőjét
        - a Fizikai termékek fül összesítőjét és kártyáit
        """

        summary = get_gold_summary(self.db_path)

        total_grams = float(summary.get("total_grams", 0))
        total_huf = int(summary.get("total_huf", 0))

        self.grams_value.setText(self._format_grams(total_grams))
        self.estimated_value.setText(self._format_huf(total_huf))

        self._refresh_physical_products()




    # Segédfüggvények:

    def _refresh_physical_products(self) -> None:
        """
        Fizikai aranytermékek fül frissítése.

        Betölti:
        - a fizikai aranytermékek összesítőjét
        - a termékkártyákat a gold_physical_items táblából
        """

        summary = get_gold_physical_summary(self.db_path)

        total_grams = float(summary.get("total_grams", 0))
        total_huf = int(summary.get("total_huf", 0))

        self.physical_summary_label.setText(
            f"Összes fizikai arany: {self._format_grams(total_grams)}"
        )
        self.physical_value_label.setText(
            f"Nyilvántartott bekerülési érték: {self._format_huf(total_huf)}"
        )

        items = list_gold_physical_items(self.db_path)

        self._clear_layout(self.physical_cards_layout)

        if not items:
            empty_label = QLabel("Még nincs rögzített fizikai aranytermék.")
            empty_label.setObjectName("aranyszamlaHintText")
            empty_label.setWordWrap(True)
            empty_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )

            self.physical_cards_layout.addWidget(
                empty_label,
                0,
                0,
                1,
                2,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            )

            self.physical_cards_layout.setColumnStretch(0, 1)
            self.physical_cards_layout.setColumnStretch(1, 1)

            return

        max_columns = 4
        columns = min(max_columns, max(1, len(items)))

        for index, item in enumerate(items):
            row = index // columns
            column = index % columns

            card = self._create_physical_item_card(item)
            self.physical_cards_layout.addWidget(
                card,
                row,
                column,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            )

        # Először nullázzuk a lehetséges oszlopnyújtásokat,
        # hogy refresh után se maradjon bent régi 4 oszlopos elosztás.
        for column in range(max_columns):
            self.physical_cards_layout.setColumnStretch(column, 0)

        # Csak a ténylegesen használt oszlopokat nyújtjuk.
        # Így 3 terméknél 3 oszlop lesz, nem 4 oszlop + üres jobb oldal.
        for column in range(columns):
            self.physical_cards_layout.setColumnStretch(column, 1)

    def _create_physical_item_card(self, item: dict) -> QFrame:
        """
        Egy fizikai aranytermék megjelenítő kártya létrehozása.

        A kártya tartalma:
            - kép
            - terméknév
            - gyártó
            - darabszám + gramm
            - tárolási hely
            - érték
        """

        card = PhysicalGoldItemCard()

        # Egy konkrét fizikai aranytermék kártyája.
        # CSAK EZ legyen fehér a sárga háttéren.
        card.setObjectName("aranyszamlaPhysicalItemCard")
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        card.setMinimumWidth(220)
        card.setMaximumWidth(280)

        # Finom 3D-s árnyék:
        # ettől a kártya kissé kiemelkedik az arany háttérből.
        self._apply_physical_card_shadow(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # ---------------------------------------------------------
        # Bal oldal: termékkép
        # ---------------------------------------------------------
        image_label = QLabel("Nincs kép")
        image_label.setObjectName("aranyszamlaPhysicalImage")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedSize(110, 99)

        # Képek betöltése:
        image_path = str(item.get("image_path", "")).strip()
        resolved_image_path = self._resolve_app_asset_path(image_path)

        if resolved_image_path is not None:
            pixmap = QPixmap(str(resolved_image_path))

            if not pixmap.isNull():
                image_label.setPixmap(
                    pixmap.scaled(
                        110,
                        90,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                image_label.setText("")
            else:
                image_label.setText("Hibás kép")
        else:
            image_label.setText("Kép nem található" if image_path else "Nincs kép")

        # ---------------------------------------------------------
        # Jobb oldal: szöveges adatok
        # ---------------------------------------------------------
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        title = QLabel(str(item.get("product_name", "")))
        title.setObjectName("aranyszamlaSectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        manufacturer = QLabel(str(item.get("manufacturer", "")))
        manufacturer.setObjectName("aranyszamlaInfoLabel")
        manufacturer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        quantity = str(item.get("quantity", 1))
        total_weight = self._format_grams(float(item.get("total_weight_grams", 0)))

        quantity_line = QLabel(f"{quantity} db · {total_weight}")
        quantity_line.setObjectName("aranyszamlaInfoLabel")
        quantity_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        storage = str(item.get("storage_location", "")).strip()

        storage_line = QLabel(
            f"Tárolás: {storage if storage else '—'}"
        )
        storage_line.setObjectName("aranyszamlaInfoLabel")
        storage_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        source_text = self._format_physical_source(str(item.get("source", "")))

        source_line = QLabel(f"Forrás: {source_text if source_text else '—'}")
        source_line.setObjectName("aranyszamlaInfoLabel")
        source_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_line = QLabel(
            f"Értéke: {self._format_optional_huf(item.get('total_huf')) or '—'}"
        )
        value_line.setObjectName("aranyszamlaInfoLabel")
        value_line.setAlignment(Qt.AlignmentFlag.AlignCenter)

        note_text = str(item.get("note", "")).strip()

        note_line = QLabel(f"Megjegyzés: {note_text if note_text else '—'}")
        note_line.setObjectName("aranyszamlaHintText")
        note_line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note_line.setWordWrap(True)     # sortördelés

        info_layout.addWidget(title)
        info_layout.addWidget(manufacturer)
        info_layout.addWidget(quantity_line)
        info_layout.addWidget(storage_line)
        info_layout.addWidget(source_line)
        info_layout.addWidget(value_line)
        info_layout.addWidget(note_line)
        info_layout.addStretch(1)

        layout.addWidget(image_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(info_layout)

        return card



    def _clear_layout(self, layout: QVBoxLayout) -> None:
        """
        Egy layout összes elemének eltávolítása.

        Erre azért van szükség, mert refresh közben újraépítjük
        a fizikai termékek kártyalistáját.
        """

        while layout.count():
            item = layout.takeAt(0)

            widget = item.widget()
            child_layout = item.layout()

            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)






    def _format_optional_huf(self, value) -> str:
        """
        Opcionális forint érték megjelenítése.

        Ha az adatbázisban nincs megadva érték, üres szöveget ad vissza.
        """

        if value is None:
            return ""

        try:
            return self._format_huf(int(value))
        except (TypeError, ValueError):
            return ""



    def _format_physical_source(self, value: str) -> str:
        """
        Fizikai termék forrásának magyar megjelenítése.

        Az adatbázis belső értékei angol kulcsok lehetnek,
        a felületen viszont magyar címkét jelenítünk meg.
        """

        source_map = {
            "gold_account": "Aranyszámla",
            "external": "Külső vásárlás",
        }

        return source_map.get(value, value)








    def _format_grams(self, value: float) -> str:
        """
        Gramm érték magyaros megjelenítése.
        """

        return f"{value:,.3f} g".replace(",", " ").replace(".", ",")



    def _format_huf(self, value: int) -> str:
        """
        Forint érték magyaros megjelenítése.
        """

        return f"{value:,} Ft".replace(",", " ")


    def _apply_physical_card_shadow(self, card: QFrame) -> None:
        """
        Erősebb, de még elegáns 3D-s árnyék a fizikai aranytermék kártyákhoz.

        Alapállapotban a kártya kissé kiemelkedik az arany háttérből.
        Hover állapotban majd tovább erősítjük ezt a hatást.
        """

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(90, 60, 15, 95))

        card.setGraphicsEffect(shadow)



    def _resolve_app_asset_path(self, relative_path: str | None) -> Path | None:
        """
        Alkalmazáshoz tartozó képek / asset fájlok feloldása.

        Működjön:
            - fejlesztői futtatásnál projektmappából
            - telepített .deb csomagnál /usr/share/penzugyi-naplo alól
            - abszolút útvonal esetén közvetlenül
        """

        if not relative_path:
            return None

        raw_path = Path(relative_path).expanduser()

        if raw_path.is_absolute():
            if raw_path.exists() and raw_path.is_file():
                return raw_path
            return None

        project_root = Path(__file__).resolve().parents[4]

        candidates = [
            project_root / raw_path,
            Path.cwd() / raw_path,
            Path("/usr/share/penzugyi-naplo") / raw_path,
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        return None


    # --- Segédfüggvények vége