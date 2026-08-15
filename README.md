# Pénzügyi Napló Dev — Fejlesztői kézikönyv

## Licenc

Ez a projekt a **CC BY-NC-SA 4.0** licenc alatt áll, kiegészítve egy
non-commercial záradékkal — **nem árulható és nem terjeszthető pénzért
vagy más termékbe építve**. Részletek: [LICENSE.md](./LICENSE.md)

Utoljára frissítve: 2026. augusztus 15.

> **Megjegyzés az AI-közreműködésről:** A kód nagy része AI (Claude) segítségével
> készült, emberi tervezés, irányítás és folyamatos ellenőrzés mellett. A
> funkcionalitásért és a projekt irányáért a szerző felel.

Ez a dokumentum nem felhasználói kézikönyv, hanem fejlesztői térkép —
**a `dev` ág aktuális, folyamatban lévő állapotáról**.

Célja, hogy hónapok múlva is gyorsan megtalálható legyen:

- melyik modul hol van,
- melyik fájl miért felel,
- milyen adatútvonalon megy végig egy funkció,
- milyen döntéseket hoztunk korábban,
- mik a nyitott célok és kockázatok.

> A `main` (stabil) ág saját, felhasználóknak szóló kézikönyvvel
> rendelkezik. A `windows/Preview` ágnak hasonló, de Windows
> csomagolás-specifikus fejlesztői kézikönyve van. Egyik sem tartalmazza
> az itt felsorolt terveket és TODO-kat.

---

## Kitűzött célok

**Likviditás / Tranzakciók:**

- Jobb gomb: oszlopszűrő lista az oszlopra kattintva
- Bal gomb: növekvő / csökkenő sorrend
- Részletes tételhez utólag lehessen új sort hozzáadni
- Tranzakcióvarázsló Összegző oldal hozzáadása QDialog helyett
- Tranzakciós lista frissítése a Varázsló bezárása után

**Pénztárcák:**

- Bank szekcióba Hitelkártya
- Előzmények lista törlésének lehetősége (vagy mindig az utolsó 30 nap mutatása)
- Kézi rögzítés típusához lenyíló nyíl

**Számlák:**

- Hónapok jelzése számmal

---

## Oldalak DEV módba tétele / kivétele

Az alkalmazásban egy oldal akkor számít DEV-only oldalnak, ha a
megjelenítése vagy regisztrálása `dev_mode` feltételhez van kötve.

### Oldal kivétele DEV módból

Ha egy oldal már stabil, és normál módban is használható, akkor:

1. Az oldal regisztrációját ki kell venni a `dev_mode` feltételből.
2. Az oldalnak mindig bekerülő normál oldalként kell regisztrálódnia.
3. Ellenőrizni kell, hogy a navigációs menüpont sincs-e külön `dev_mode` mögött.
4. Ellenőrizni kell, hogy az oldal frissítési / szűrési logikája normál módban is működik-e.

**DEV-only oldal placeholderrel:**

```python
if window.dev_mode:
    window.add_page("statistics", StatisticsPage(window.ctx, parent=window))
else:
    window.add_page("statistics", ComingSoonPage("Statisztika", parent=window))
```

**`else` nélkül, DEV-only oldal:**

```python
if window.dev_mode:
    window.add_page("statistics", StatisticsPage(window.ctx, parent=window))
```

**Normál, mindig elérhető oldal:**

```python
window.add_page("statistics", StatisticsPage(window.ctx, parent=window))
```

---

## Projekt fő részei

- `/core/` – közös alkalmazáslogika
- `/db/` – adatbázisréteg
- `/ui/main_window/` – főablak és kiszervezett MainWindow-logika
- `/ui/likviditas/` – Likviditás modul
- `/ui/bills/` – Számlák modul
- `/ui/importers/` – import varázslók
- `/importers/` – import feldolgozó logika
- `/ui/styles/` – QSS témák

---

## Adatbázis

`/db/data/transactions.sqlite3` — a Pénzügyi Napló fő SQLite adatbázisa.

Az adatmodellben a **B-modell** érvényesül:

- `amount` mindig nemnegatív
- `tx_type` külön jelöli a típust: `income` / `expense`
- a tranzakció `year` / `month` mezői külön tárolódnak

### Fő alkalmazástáblák

| Tábla | Felelősség |

|---|---|
| `transactions` | Tranzakciók fő táblája |
| `categories` | Kategóriák, `tx_type` és `is_bill` jelöléssel |
| `transaction_items` | Részletezett tranzakciók tételei |
| `plans` | Havi tervek |
| `settings` | Kulcs-érték beállítások |
| `schema_version` | Egyszerű séma-verziózás |
| `wallet_balances` | Készpénz / folyószámla jellegű egyenlegek |
| `account_valuations` | Értékpapír / nemesfém jellegű account értékelések |
| `bills` | Számlák adatmodellje |
| `bill_monthly_amounts` | Havi számlaösszegek |
| `bill_periodic_amounts` | Időszakos számlaösszegek |

### Fontos `transactions` mezők

`id`, `tx_date`, `tx_type`, `amount`, `category_id`, `name`, `description`,
`created_at`, `year`, `month`, `quantity`, `unit_price`, `has_details`,
`payment_source`, `period_start`, `period_end`, `invoice_number`

### Számlákhoz kapcsolódó mezők

- `categories.is_bill` — jelzi, hogy az adott kategória számlakategória-e
- `transactions.period_start` / `period_end` — időszakos számla kezdete/vége (pl. MVMNext, gáz)
- `transactions.invoice_number` — számla sorszáma (**nem** a `description` mezőbe kerül)
- `transactions.payment_source` — jelenleg jellemzően `bank` / `cash`

### Fontos indexek

`transactions(year, month)`, `transactions(tx_date)`, `transactions(tx_type)`,
`categories(tx_type)`, `plans(year, month)`, `transaction_items(transaction_id)`,
`wallet_balances(wallet_type, date)`, `account_valuations(account_type, date)`,
`bills(kind)`, `bill_monthly_amounts(year)`, `bill_periodic_amounts(bill_id)`

### Megjegyzés a sémáról

A `transaction_database.py` idempotens CREATE / ALTER logikát használ,
tehát régebbi adatbázis megnyitásakor a hiányzó oszlopokat fokozatosan
pótolja. Ha egy adatbázist még nem nyitott meg az app az új séma után,
akkor abban átmenetileg hiányozhatnak újabb oszlopok (pl.
`invoice_number`) — ez főleg dev/prod adatbázisok eltérő állapotánál
fordulhat elő.

---

## `/core/`

Közös alkalmazáslogika.

- `app_context.py` — alkalmazáskörnyezet / közös állapot
- `logging_utils.py` — naplózás, session start, log fájl
- `paths.py` — alkalmazás útvonalak, adat/log/config helyek
- `utils.py` — közös validálás és formázás, például dátum / összeg

**Fontos:**

- UI-független segédfüggvények ide kerüljenek.
- Ne legyen benne konkrét widget / PySide6 UI-logika, ha nem muszáj.

---

## Likviditás

### MainWindow — `/ui/main_window/likviditas/`

A MainWindow Likviditás-specifikus logikájának kiszervezett részei.

- `actions.py` — QAction-ok létrehozása / bekötése
- `menus.py` — Fájl menü és menüpontok
- `register_pages.py` — Likviditás oldalak regisztrálása
- `import_handlers.py` — import funkciók indítása
- `backup_restore_handlers.py` — mentés / betöltés kezelése
- `toolbar_mode.py` — toolbar/ribbon mód kezelése

Cél: a `main_window.py` rövidítése, hogy ne legyen újra 2000+ soros, és a
funkciócsoportok könnyebben megtalálhatók legyenek.

### Import / ODS import

Logikai importer: `/importers/ods_transaction_importer.py`

UI wizard:

- `/ui/importers/ods_transaction_import_wizard.py`
- `/ui/importers/ods_import_pages.py`

Felelősség: ODS fájl kiválasztása → munkalap kiválasztása → fejlécsor /
adatsor kezdete → előnézet → importálás.

Fontos döntés: ez **vezetett import varázsló**, nem sima fájlmegnyitás.

### Mappák — `/ui/likviditas/`

- `pages/` — fő oldalak (`home_page.py`, `transactions_page.py`,
  `statistics_page.py`, `accounts_page.py`, `settings_page.py`)
- `dialogs/` — egyszerű párbeszédablakok (`home_table_dialog.py`,
  `month_details_dialog.py`, `transaction_details_dialog.py`,
  `transaction_edit_dialog.py`)
- `widgets/` — beágyazott kisebb UI elemek (`home_summary_panel.py`,
  `transactions_filter_bar.py`)
- `wizard/` — többoldalas QWizard folyamatok

### Tranzakcióvarázsló — `/ui/likviditas/wizard/`

A main ághoz képest a varázsló itt **több fájlra bontva** él:

- `wizard_transaction.py` — a QWizard váz, oldalak összefűzése
- `wizard_helpers.py` — közös segédfüggvények (validáció, formázás)
- `wizard_pages_common.py` — közös/általános tranzakció-oldalak
  (bevétel, kiadás, kategória, dátum)
- `wizard_pages_bill.py` — számlabefizetés-specifikus oldalak
- `wizard_pages_gas.py` — **gáz (MVMNext-típusú) számla oldal**: kifizetett
  összeg, számla sorszáma, elszámolási időszak kezdete/vége, elszámolt
  hónap dátuma, korrekció/jóváírás jelölő checkbox, és a méterállás
  (m³/MJ) mező — csak MVMNext gáz típusnál jelenik meg

Korábbi helye (main-en még egyben): `wizard_transaction.py` egyetlen
fájlban tartalmazta mindezt.

Feladata összességében:

- normál bevétel / kiadás rögzítése
- részletezett tételek kezelése
- számlabefizetéses flow kezelése
- MVMNext / gáz esetén fizetési dátum, időszak kezdete/vége, számla
  sorszáma, méterállás

Későbbi Aranyszámla irány: `/ui/main_window/aranyszamla/wizard/gold_trade_wizard.py`

---

## Számlák modul (bills)

`/ui/bills/` fájlok:

- `bill_card.py`
- `bill_models.py`
- `bills_page.py`
- `monthly_grid_widget.py`
- `periodic_list_widget.py`
- `bill_details_dialog.py`
- **`invoice_edit_dialog.py`** *(új, Preview-specifikus)* — meglévő,
  már rögzített számlatétel utólagos szerkesztésére szolgáló dialógus,
  megerősítő kérdéssel ("Biztos szerkeszteni akarod a már rögzített
  adatokat?"). Mezők: fizetés dátuma, összeg, számla sorszám,
  korrekció/jóváírás checkbox.

> **Ismert korlát:** a `bills_page.py`-ban lévő `update_bill_entry()`
> (szerkesztés gomb) jelenleg csak havi (monthly) tételekre működik, és
> nem menti a `meter_value` mezőt — az időszakos (periodic) tételek,
> köztük a gáz méterállás, szerkesztése egyelőre nem érhető el ezen az
> úton. Új tételek felvétele helyesen menti az adatokat, csak az
> utólagos szerkesztés hiányos még.

### Adatfolyam

```
wizard_transaction.py (+ wizard_pages_*.py)
  -> TransactionDatabase.save_transaction()
  -> transactions tábla
  -> TransactionDatabase.get_bill_card_models(year)
  -> BillCardModel / MonthlyAmount / PeriodicAmount
  -> BillsPage
  -> BillCard
  -> MonthlyGridWidget vagy PeriodicListWidget
  -> BillDetailsDialog / InvoiceEditDialog
```

### Felelősségek

- **BillsPage** — Számlák oldal, kártyák betöltése, reload
- **BillCard** — kártya kerete, cím, belső widget kiválasztása
- **MonthlyGridWidget** — havi számlák, pl. Telekom / KalászNet
- **PeriodicListWidget** — időszakos számlák, pl. MVMNext / gáz
- **BillDetailsDialog** — részletező / törlő ablak
- **InvoiceEditDialog** — meglévő számlatétel szerkesztése
- **bill_models.py** — UI-only dataclass modellek (`@dataclass(frozen=True)`,
  `BillKind = Literal["monthly", "periodic"]`)

### Kockázatok / finomítandó pontok (monthly_grid_widget.py + periodic_list_widget.py)

1. **Pénz float + duplikált formázó** — `_fmt_huf(amount: float)` mindkét
   widgetben külön van implementálva, ugyanazzal a logikával
   (`f"{amount:,.0f}"`). Ezzel két gond van: pénz floatként tárolva
   (pontossági csúszás lehetősége), és a duplikált formázás később
   eltérő viselkedéshez vezethet.
   **Javaslat:** UI-modellekben és mindkét widgetben `amount: int` (HUF),
   és egy központi `format_number_hu` util a `/core/utils.py`-ból,
   ne legyen két külön `_fmt_huf`.

2. **Időszak string: ISO formátum, nem "emberi"** — jelenleg
   `period = f"{it.start} – {it.end}"` (ISO dátumokkal). Fejlesztéshez jó,
   de felhasználónak valószínűleg jobb lenne pontozott HU formátum
   (pl. `2026.01.01 – 2026.02.01`).
   **Javaslat:** központi `format_date_hu("YYYY-MM-DD") -> "YYYY.MM.DD"`
   util bevezetése.

3. **0 összeg megjelenítése** — a monthly widgetnél 0-ra "—" jelenik meg,
   a periodic-nál nem: ott 0 esetén "0 Ft" látszik. Ez eltérően
   kommunikálja az "üres" hónapot/időszakot a két widgetben.
   **Javaslat:** egységesíteni — UX-ben számláknál a "—" általában jobb
   jelzés (nincs fizetés / nincs adat).

**Rövid teendő-lista a fentiekhez:**

- 1 központi pénzformázó bevezetése (ne legyen két `_fmt_huf`)
- `amount` típus váltás `int`-re a bill modellekben és widgetekben
- egységes "0/hiány" megjelenítés (pl. "—")

### MVMNext / gáz számlák

A wizardban rögzített mezők: fizetés dátuma, időszak kezdete, időszak
vége, összeg, számla sorszáma (gáznál emellett méterállás m³/MJ-ban).

Megjelenítés:

- A számla sorszáma a kártyán jelenjen meg.
- A `BillDetailsDialog` Megjegyzés oszlopában csak a státusz legyen:
  Fizetve / Nincs fizetve.

Fontos: a számla sorszáma **nem** a `description` / Megjegyzés mezőbe
kerül, hanem külön `transactions.invoice_number` mezőként van tárolva.

---

## Widgetek

### Közös widgetek — `/ui/widgets/`

- `nav_bar.py` — oldalválasztó navigáció. Signal-kontraktus:
  `pageRequested = Signal(str)`, autoexclusive gombok, QSS hook
  (`navBar` / `navButton`).
  Tervezett finomítások: induló aktív gomb fixen beállítva (inkább
  MainWindow-ban), `set_active()` rossz key esetén dev jelzés,
  opcionálisan lambda helyett tisztább slot.

- `ribbon_bar.py` — Office-szerű szalag, tabokkal és QAction-alapú
  gombokkal (`setDefaultAction`), collapse/expand jelzéssel
  (`toggled(bool)`, QSettings-be menthető).

- `year_tabs_bar.py` — év-alapú navigáció. Signal-kontraktus:
  `yearChanged = Signal(int)`, autoexclusive gombok,
  `setProperty("active", ...)` + polish/unpolish minta QSS-hez,
  `emit` flag a `set_active_year`-ben (programból állítható reload
  kiváltása nélkül).

- `transactions_filter_bar.py` — újrahasznosítható szűrősáv.
  Signal-kontraktus: `searchRequested(text, all_years)`,
  `clearRequested()`. ReturnPressed keresés + gomb egységesen.

### `/ui/charts.py`

Diagram-rajzolás kiszervezve a MainWindow-ból: `ChartManager` +
`ChartsContext` felépítés, explicit dependency injection-nel (db,
selected_year, figure/canvas párok, formatter). A MainWindow-ban csak a
Figure/Canvas létrehozása és a `charts.update_all()` hívás marad.

---

## Dialógok

### `/ui/dialogs/transaction_edit_dialog.py`

Tranzakció szerkesztő dialógus. Kontraktus: HU típus visszaadása →
DB normalizál.

- `QLineEdit` dátumra — szándékosan szabad bevitel
- `QComboBox` kategóriára
- `QDoubleSpinBox` összegre
- `data()` metódus — explicit output kontraktus

### `/ui/pages/base_page.py`

Minimál, tiszta kontraktus osztály az oldalakhoz (MainWindow → oldal
évállapot). Csak az év-állapotot tárolja, setter/getterrel;
`set_year` felülírható oldalszinten.
