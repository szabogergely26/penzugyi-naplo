--- README for


/db/data/transactions.sqlite3:
------------------------------


    A /data/transactions.sqlite3 állományban jelenleg egy letisztult, működő alap-séma van (5 tábla, releváns indexekkel), és a “B-modell” elv 
    (amount mindig nemnegatív, külön tx_type) már érvényesül a transactions táblában.



   / Tartalma:
    ----------

        / Táblák
        ---------

            - transactions: tranzakciók (bevétel/kiadás) + név + mennyiség/egységár opció

            - categories: kategóriák (tx_type, is_bill)

            - plans: havi terv (year+month PK)

            - settings: kulcs-érték beállítások

            - schema_version: verziózás (most version = 1)

            - Fontosabb mezők és constraint-ek (transactions)

            - tx_date TEXT NOT NULL (komment szerint YYYY-MM-DD)

            - tx_type TEXT NOT NULL CHECK (income|expense)

            - amount REAL NOT NULL CHECK (amount >= 0)

            - year INTEGER NOT NULL, month INTEGER NOT NULL CHECK (1..12)

            - name TEXT NOT NULL DEFAULT ''

            - quantity INTEGER DEFAULT 1

            - unit_price REAL

            - FK: category_id -> categories(id)


        Indexek (jók, célzottak)

            - transactions(tx_date), transactions(tx_type), transactions(year, month)

            - categories(tx_type)

            - plans(year, month)



    / Javasolt további fejlesztések:
    -------------------------------

        1. Konkrét, rövid “következő lépés” javaslat a te mostani irányodhoz

        2. Új kategória: “Ebéd” (expense) – és a meglévő “Ebéd” tranzakciót át lehet majd sorolni.

        3. DB bővítés: transaction_items tábla (a részletek ablak miatt).

        4. Pénzmezők jövőállóvá tétele (REAL → INTEGER) – ez lehet későbbi migráció is, de érdemes tervbe venni.











/db/transaction_database.py:
-------------------------------

A transaction_database.py már most is egy használható, “központi DB-réteg” 
(jó separation: UI nem SQL-ezik; FK-k bekapcsolva; idempotens CREATE/ALTER; B-modell logika; bill/has_details/transaction_items előkészítve). 




/ui/bills/bill_card.py:
--------------------------
 nagyon rendben van: tiszta, UI-only komponens, jó separation (nincs DB/logika), és a “kártya” viselkedés (kattintás, inaktív stílus) korrektül meg van oldva. 



Ami kifejezetten jó:

        - Egyszerű, jól olvasható felelősség: BillCardModel → cím + belső widget; kattintás → clicked(bill_id). 


        - Külső tartalom kiválasztása kind alapján: MonthlyGridWidget vs PeriodicListWidget jó komponenshatár. 


        - Stílus hookok: objectName="billCard" és az inactive property később QSS-ben jól kezelhető. 



        - Cursor: PointingHandCursor jó UX jelzés.



/ui/bills/bill_model.py:
--------------------------
A /ui/bills/bill_models.py jó, tiszta UI-adatmodell réteg: “frozen” dataclass, egyszerű típusok, és a BillKind literal miatt a kódbázis többi része 
(pl. BillCard) jól típusoztatva marad.


Ami kifejezetten erős

        - Immutable modellek (@dataclass(frozen=True)): UI-state kiszámíthatóbb, nem “csúsznak el” referenciák. 



        - BillKind = Literal["monthly","periodic"]: jó “ön-dokumentáló” megoldás, és a BillCard-ban a kind alapján történő render tiszta. 

    bill_card

        - Töltet szétválasztása: monthly vs periodic a kind alapján — ez illeszkedik a UI-kártyás logikához. 

bill_models






/ui/bills/bills_page.py:
--------------------------
jelenlegi állapotában stabil, tiszta “oldal-komponens”, és jó alapot ad a későbbi DB-rákötéshez. A szerkezet (QScrollArea + FlowLayout + BillCard) ergonomikus, a szűrőállapot (_year, _all_years) pedig helyesen a MainWindow felől vezérelt. 



Ami most kifejezetten jó

        - Jó UI-architektúra: set_filter() csak állapotot állít, reload() az adatbetöltés belépőpontja, _render() csak kirajzol. Ez jól tesztelhető és később DB-re cserélhető. 


        - Kártyák tiszta kezelése: _clear_cards() deleteLater-rel korrekt. 


        - Eseménylánc: BillCard.clicked -> billRequested(bill_id) jó, a page nem “tud” részletekről, csak jelzi. 


        - Demó adatok évfüggése: jó szemléltetés arra, hogy év szerint változhat az összeg.




/ui/bills/monthly_grid_widget.py:
-------------------------------------
összességében rendben van: egyszerű, stabil widget, jó QSS-hook (objectName="monthlyGrid", property-k a cellákon), és a 12 hónapos fix táblázatos 
megjelenítés a számlák kártyáján UX-ben korrekt.

A MonthlyGridWidget egy jól szervezett, tiszta komponens, amely hatékony



Ami jó és maradhat

        - Egyszerű leképezés: items -> dict[month]=amount, majd fix 12 sor. Olcsó és megbízható. 


        - Header + jobb igazítás: “Fizetett” oszlop AlignRight, olvashatóság oké. 


        - 0/hiány jelölése “—”: jó vizuális jelzés. 


        - QSS felkészítés: cell és cellHeader property-k nagyon hasznosak lesznek.



Javasolt további fejlesztések:
-------------------------------

Rövid, konkrét teendőlista (kis munka, nagy konzisztencia):
-------------------------------------------------------------

    - MonthlyAmount.amount → int (vagy legalább itt kezeld intként).

    - _fmt_huf() helyett központi util használata.

    - Duplikált hónapok: vagy assert, vagy aggregálás (attól függ, DB-ből hogyan fogod adni).






/ui/bills/periodic_list_widget.py:
-------------------------------------
Ugyanolyan “jó alap, de érdemes egységesíteni” kategória, mint a MonthlyGridWidget: tiszta, kicsi widget, QSS-hookokkal, és a periodikus tételeket jól listázza.


Ami jó:
--------


    - Letisztult felelősség: csak megjelenít, semmi logika/DB. 


    - Rendezett layout: 2 oszlop (Időszak | Összeg), fix spacingek, margók 0 – jól beágyazható kártyába. 


    - QSS property-k: cell és cellHeader egységes a monthly widgettel. 


    - Jobbra igazított összeg: helyes olvashatóság.



Kockázatok / finomítandó pontok:
----------------------------------

    1) Pénz float + duplikált formázó

             _fmt_huf(amount: float) ugyanazt a helyi formázást csinálja, mint a monthly widget (f"{amount:,.0f}"). Ezzel két gond van:

            pénz floatként (pontossági csúszás),

            duplikált formázás (később eltérő viselkedéshez vezet). 

  
        Javaslat:

            UI-modellekben és itt is: amount: int (HUF).

            Formázás: központi util (format_number_hu) használata a /core/utils.py-ból, ne legyen két külön _fmt_huf. (Ugyanez igaz a monthly widgetre is.) 



    2) Időszak string: ISO oké, de nem “emberi”

                Most period = f"{it.start} – {it.end}" (ISO dátumokkal). Ez fejlesztéshez jó, de felhasználónak valószínű jobb lesz:

                2026.01.01 – 2026.02.01 (pontozott HU),

                vagy rövidebben: 2026.01.01 – 02.01 (ha az év azonos),

                vagy akár “2026. jan. 01 – febr. 01”.

        
            Javaslat (későbbre is jó):

                legyen egy központi format_date_hu("YYYY-MM-DD") -> "YYYY.MM.DD" util, és itt azt használd.

    3) 0 összeg megjelenítése

            A  monthly widgetnél van “—” 0-ra, itt nincs: 0 esetén “0 Ft” jelenik meg. A BillsPage demóban konkrétan van 0 összegű periodikus sor, 
            tehát a két widget eltérően kommunikálja az “üres” hónapot/időszakot. 

            Javaslat:

                Egységesíts: vagy itt is “—” 0-ra, vagy a monthly-ban is “0 Ft”.

                UX-ben számláknál a “—” általában jobb (jelzi, hogy nincs fizetés / nincs adat).


Javasolt további fejlesztések:
----------------------------------

        Rövid teendő a monthly_grid_widget.py + periodic_list_widget.py pároshoz:

        Vezess be 1 központi pénzformázót (ne legyen két _fmt_huf). 



        Válts amount típuson int-re a bill modellekben és widgetekben. 

        Egységes “0/hiány” megjelenítés (pl. “—”). 



Összefoglaló:
--------------------------


Ezzel a Bills UI-rész gyakorlatilag kész arra, hogy DB-ből jövő valós adatokkal is konzisztensen viselkedjen.






/ui/dialogs/transaction_edit_dialog.py:
-------------------------------------------

Az a hely, ahol minden eddigi döntésed találkozik (DB-modell, HU/EN típus, dátum- és pénzkezelés)


Összkép – röviden

    👉 A dialógus szerkezete jó, érthető, használható.
    👉 A kontraktus tiszta (HU típus visszaadása → DB normalizál).
    👉 A problémák nem logikai hibák, hanem “rendszerszintű konzisztencia” kérdések, amik most még könnyen javíthatók.

Ez már nem kísérleti kód, hanem egy valódi UI-réteg.


✔️ Egyszerű, érthető mezők

    - QLineEdit dátumra → szándékosan szabad bevitel ✔️

    - QComboBox kategóriára ✔️

    - QDoubleSpinBox összegre ✔️

    - data() metódus → explicit output kontraktus ✔️


Ez így UI-szinten korrekt.




/ui/pages/base_page.py:
------------------------

teljesen rendben van: egy minimál, tiszta “kontraktus” osztály az oldalakhoz, és pont azt a célt szolgálja, amit korábban is terveztél 
(MainWindow → oldal évállapot).


Ami jó (és maradjon):

    - Egyszerű felelősség: csak az év-állapotot tárolja, és setter/getter van rá. 

    - Típusok: int | None helyes; a from __future__ import annotations korrekt, itt a fájl elején van (nincs “future import” hiba). 

    - Bővíthető: a docstring jelzi, hogy set_year felülírható oldalszinten.



/ui/pages/home_page.py:
------------------------

funkcionálisan jó, és a “Terv–Tény dashboard” logikád már most is koherens. Viszont ebben a fájlban van a legtöbb olyan pont, ami később “kicsi, de idegesítő” hibákhoz és inkonzisztenciához vezethet (pénzformátum, float, itemChanged rekurzió, évkezelés). Érdemes most rendbe tenni, mert ez lesz a napi használt képernyő.



/ui/widgets/nav_bar.py
-------------------------

jó, egyszerű, célszerű – és pont olyan, amire egy ilyen appnál szükség van. Két apró korrekciót és egy ajánlott bővítést látok, hogy később se legyen “miért nem jelölődik ki rendesen?” típusú kellemetlenség


Ami jó (maradhat):

    - Tiszta jelzés: pageRequested = Signal(str) és key-t küld (“home”, “transactions”…). 

    - AutoExclusive gombok: egyszerűen megoldja az “aktív oldal” kijelölést. 

    - QSS hook: navBar + navButton objectName jó. 

    - Layout: settings jobbra tolása addStretch(1)-gyel UX-ben jó.




Összegzés:

    Ez a NavBar rendben van, nem kell túlgondolni. A három “életszagú” fejlesztés:

    induló aktív gomb legyen fixen beállítva valahol (inkább MainWindow),

    set_active() rossz key esetén dev jelzés,

    (opcionális) lambda helyett tisztább slot.




/ui/widgets/ribbon_bar.py:
--------------------------

jó alap, egyszerű és érthető, és pontosan arra való, amire neked kell (Office-szerű “szalag”, tabok, QAction-gombok, collapse). Viszont van benne 2 konkrét technikai kockázat, amit érdemes most javítani, plusz 2 finomítás, amitől “késztermék”


    Ami kifejezetten jó:

        - QAction-alapú gombok: setDefaultAction(action) a legjobb Qt-s minta (shortcutok, enabled/disabled állapot, icon/text automatikus). 

        - Szalag felépítés: QTabBar + QStackedWidget teljesen korrekt, minimál dependenciával. 

        - Collapse/expand jelzés: toggled(bool) jel nagyon jó a MainWindow-nak (el tudja menteni QSettings-be is). 

        - QSS hookok: objectName-ek jól elő vannak készítve.



    Összegzés:
    -----------

        - A RibbonBar jó, és szépen illik az eddigi UI irányodhoz.




/ui/widgets/transactions_filter_bar.py
-----------------------------------------
kifejezetten jó irány: egy kicsi, újrahasznosítható, UI-only komponens, tiszta signal-kontraktussal. Ez pont az, ami később segít abban, hogy a TransactionsPage ne legyen tele “vezérlő UI” kóddal. 


    mi nagyon jó (maradjon így):


        - Signal alapú kimenet: searchRequested(text, all_years) + clearRequested() – ez a helyes Qt/arch minta. 

        - ReturnPressed keresés: jó UX, és a gombbal is egységes. 

        - Layout arányok: a search mező stretch=1, a többi fix – jól fog kinézni. 

        - Docstring / kontraktus: fejlesztőbarát, később is érthető.




Kapcsolat a TransactionsPage-el:

    Ez a widget pont azt javítja, amit a TransactionsPage ellenőrzésénél kiemeltem:

        ott volt egy “Keresés” gomb, ami nem volt bekötve / nem volt konzisztens

        itt viszont ez már rendezett, és később a page csak a signalokat hallgatja






/ui/widgets/year_tabs_bar.py
-------------------------------

    Ami kifejezetten jó:

        - Signal-kontraktus tiszta: yearChanged(int) – ez kell a MainWindow számára. 

        - AutoExclusive gombok: egyszerre egy aktív év, jó UX. 

        - QSS-integráció profi: setProperty("active", ...) + polish/unpolish – ez a helyes minta, ha QSS-sel “active tab” kinézetet akarsz. 

        - emit flag a set_active_year-ben: nagyon jó, így tudsz programból állítani anélkül, hogy minden reload elsülne.





    Összegzés:
    -------------

        Ez a widget mehet, és tényleg “kulcsszereplő” az év-alapú navigációban, ahogy a docstringed is írja



/ui/charts.py
----------------
A szándékod (diagram-rajzolás kiszervezése a MainWindow-ból) teljesen helyes, és a ChartManager + ChartsContext felépítés jó alap. Ugyanakkor ebben a fájlban van néhány konkrét technikai/arch kockázat, amit érdemes most megfogni, különben később nehéz lesz konzisztensen karbantartani.


    Ami kifejezetten jó

        - Kiszervezés: a MainWindow-ban csak Figure/Canvas létrehozás + charts.update_all() marad – ez tiszta felelősségi határ. 

        - Context objektum: nem globálok, nem “varázs importok”, hanem explicit dependency injection (db, selected_year, 3 fig/canvas pár, formatter). 

        - update_context_year(): jó, hogy külön tudod frissíteni a kiválasztott évet.






ui/dialog_transaction_editor.py
------------------------------------
