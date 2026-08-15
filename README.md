# Pénzügyi Napló — Felhasználói kézikönyv

## Licenc

Ez a szoftver a **CC BY-NC-SA 4.0** licenc alatt érhető el, kiegészítve egy
non-commercial záradékkal — **nem árulható és nem terjeszthető pénzért vagy
más termékbe építve**. Részletek: [LICENSE.md](./LICENSE.md)

Utoljára frissítve: 2026. augusztus 15.

> **Megjegyzés az AI-közreműködésről:** A program nagy része AI (Claude)
> segítségével készült, emberi tervezés, irányítás és folyamatos
> ellenőrzés mellett.

---

## Mi ez a program?

A Pénzügyi Napló egy asztali alkalmazás a személyes pénzügyeid
nyomon követésére: bevételek és kiadások rögzítése, közüzemi/szolgáltatói
számlák befizetésének figyelése, egyenlegek és arany-megtakarítás
áttekintése, valamint havi/éves statisztikák.

---

## Indítás után — a főablak felépítése

A program indításkor egy nagy, maximalizált ablakban nyílik meg, a
következő elrendezéssel:

- **Bal oldali sáv (modulválasztó)** — a program két fő modulja között
  válthatsz: **Likviditás** (a napi pénzügyeid) és **Aranyszámla**
  (arany-megtakarítás).
- **Év-fülek** — a bal oldalon, a modulválasztó mellett választhatod ki,
  melyik év adatait szeretnéd nézni.
- **Szalag (ribbon)** — a felső sáv gyors hozzáférést ad a leggyakoribb
  műveletekhez (új tranzakció, biztonsági mentés, import/export stb.),
  fülekbe rendezve: **Fő**, **Adatok**, **Nézet**, **Súgó**.
- **Jobb oldali navigáció** — itt találod a Likviditás modul oldalait:
  Kezdőlap, Tranzakciók, Statisztika, Számlák, Pénztárcák.

A **Nézet** menüben (vagy a ribbon "Nézet" fülén) átválthatsz a klasszikus
menüsoros és a szalag (ribbon) megjelenítés között, ízlés szerint.

---

## Likviditás modul

### Kezdőlap

Havi összesítőket mutat az aktív év tranzakcióiból: hónapról hónapra
látod a bevételeket, kiadásokat és a megtakarítást. Ha egy hónaphoz még
nincs rögzített adat, ezt egyértelműen jelzi a felület. Egy hónapra
kattintva részletes táblázatos nézet nyílik meg az adott hónap
tételeiről.

### Tranzakciók

Ez a tranzakciók listás, kereshető és szűrhető nézete.

- A **keresőmezőben** kategória vagy leírás szerint kereshetsz.
- Minden tranzakciónál elérhető a **Szerkesztés** és **Törlés** funkció.
- Ha egy tranzakcióhoz részletezett tételek is tartoznak, ez a listában
  külön jelzésre kerül ("Tételrészletek elérhetők").

### Új tranzakció rögzítése (varázsló)

Az új tranzakció rögzítése egy lépésenkénti varázslóval történik (ribbon
"Fő" fül → új tranzakció, vagy Fájl menü). A varázsló első lépésében
kiválasztod, milyen pénzmozgást szeretnél rögzíteni:

- **Bevétel** — beérkező összeg, például fizetés, támogatás.
- **Kiadás** — kimenő összeg, például vásárlás, étkezés.
- **Számlabefizetés** — közüzemi vagy szolgáltatói számla befizetése
  (pl. Telekom, KalászNet, MVMNext, Vidanet, gáz).

A további lépésekben megadod a tranzakció nevét, kategóriáját, leírását
és dátumát. Számlabefizetés esetén a varázsló további, számla-specifikus
mezőket is kér (pl. időszak kezdete/vége, számla sorszáma az időszakos
számláknál, gáz esetén az óraállás m³/MJ-ban).

### Statisztika

Két fület tartalmaz:

- **Általános** — szöveges összefoglaló egy kiválasztott időszakról.
- **Diagramok** — trenddiagram, havi bevétel/kiadás/megtakarítás
  oszlopdiagramja, és a kiadások kategóriák szerinti megoszlása.

### Számlák

A rendszeresen fizetendő közüzemi/szolgáltatói számláid áttekintése,
két típusra bontva:

- **Havi számlák** (pl. KalászNet) — egy hónapos rács-nézetben mutatja,
  melyik hónapban mennyi lett befizetve.
- **Időszakos számlák** (pl. MVMNext) — az elszámolási időszak kezdetét,
  végét és — ha van — a számla sorszámát is mutatja.

Minden számla-kártyán megjelenik a fizetés dátuma és állapota.

### Pénztárcák / Egyenlegek

Készpénz, folyószámla és nemesfém-jellegű vagyonelemeid kézi
nyilvántartására szolgáló oldal.

- A **Bank** blokkban a folyószámla egyenlegét követheted.
- A **Kézi érték rögzítése** panelen egy típus (Készpénz, Folyószámla,
  Nemesfémek), dátum és érték megadásával rögzíthetsz új állapotot.
- Az **Előzmények** táblázat az utolsó 30 rögzített értéket mutatja
  (Dátum / Típus / Érték oszlopokkal).

> Fontos megkülönböztetés: ez **nem** ugyanaz, mint a "Számlák" oldal — a
> Pénztárcák a vagyon/egyenleg nyilvántartásáról szól, a Számlák pedig a
> rendszeres fizetési kötelezettségekről.

---

## Aranyszámla modul

Az arany-megtakarításod áttekintésére és kezelésére szolgáló, önálló
navigációval rendelkező modul (Kezdő / Kereskedés gombokkal a modulon
belül).

### Kezdő

- **Aranyszámla fül** — az "Aranytartalék" és a "Jelenlegi állapot"
  panelen látod az aranyszámládon nyilvántartott mennyiséget és a
  becsült értékét. A becsült érték a rögzített vásárlások, eladások és
  az aktuális árfolyam alapján számolódik.
- **Fizikai termékek fül** — ha fizikai aranytermékeket (érme, rúd stb.)
  is nyilvántartasz, itt látod a nyilvántartott bekerülési értéküket
  összesítve.

### Kereskedés

Itt jelennek meg az aranyszámládhoz rögzített vételi és eladási
tranzakciók, táblázatos formában (Dátum / Mennyiség / Megjegyzés /
Típus / Művelet oszlopokkal). Minden tételnél elérhető a törlés
lehetősége, megerősítő kérdéssel.

---

## Menük és gyakori műveletek

### Fájl menü

- **Új tranzakció** — a rögzítő varázsló megnyitása
- **Beállítások**
- **Kilépés**

### Adatok menü

- **Biztonsági mentés** / **Visszaállítás** — az adatbázis mentése és
  visszatöltése
- **Import** / **Export**
- **Adatbázis törlése** — figyelem, ez a program egyik legveszélyesebb
  művelete, csak megfontoltan használd (a ribbonban ez a gomb
  külön, piros jelöléssel is ki van emelve)

### Nézet menü

- Váltás a klasszikus menüsor és a szalag (ribbon) megjelenítés között

### Súgó menü

- **Névjegy**
- **Verzióinformáció**
- **Napló megtekintése** — hibakereséshez, technikai napló
- **Verziótörténet**

---

## Gyakori kérdések

**Hova kerülnek az adataim?**
A tranzakciók egy helyi SQLite adatbázisban tárolódnak a géped
felhasználói adatterületén (nem kerülnek fel semmilyen szerverre).

**Mit jelent a "FEJLESZTŐI MÓD AKTÍV" felirat, ha látom?**
Ez fejlesztői/tesztelési célú jelzés, plusz naplózással jár. Normál
használat során ez nem jelenik meg.

**Elveszíthetem az adataimat?**
A rendszeres **Biztonsági mentés** (Adatok menü) használatával
minimalizálható ennek kockázata.
