# Pénzügyi Napló

**Pénzügyi Napló** egy saját fejlesztésű, asztali pénzügyi napló alkalmazás Python / PySide6 alapon.

Az alkalmazás célja, hogy helyben, átlátható módon lehessen kezelni a mindennapi pénzügyi adatokat: bevételeket, kiadásokat, számlákat, likviditási adatokat és aranyszámla jellegű nyilvántartásokat.

> Állapot: GitHub `.deb` tesztverzió előkészítés alatt  
> Verzió: `0.1.0`  
> Platform: Linux, később Windows és Android irány

---

## Fő funkciók

- bevételek és kiadások rögzítése;
- tranzakciók listázása és szűrése;
- éves / havi likviditási nézetek;
- számlák kezelése;
- statisztikai nézetek;
- adatbázis mentés és betöltés;
- aranyszámla modul előkészítése és fejlesztése;
- többoldalas varázslók új tranzakciókhoz;
- sötét / modern Qt-alapú felület.

---

## Jelenlegi állapot

A projekt aktív fejlesztés alatt áll.

A jelenlegi GitHub / `.deb` csomagolási cél:

- tiszta Linux telepíthető csomag készítése;
- alkalmazásikon és `.desktop` indító hozzáadása;
- személyes adatok kizárása a csomagból;
- Discover / alkalmazásindító kompatibilitás javítása;
- későbbi automatikus frissítési út előkészítése.

Ez még nem végleges stabil kiadás, hanem tesztelésre és saját használatra szánt csomagolt verzió.

---

## Telepítés `.deb` csomagból

A projektből készített Debian csomag például így telepíthető:

```bash
sudo apt install ./penzugyi-naplo_0.1.0_all.deb
```

Eltávolítás:

```bash
sudo apt remove penzugyi-naplo
```

A telepített indító parancs:

```bash
penzugyi-naplo
```

---

## `.deb` csomag építése

A csomagolás scriptje:

```bash
packaging/deb/build_deb.sh
```

Futtatás a projekt gyökeréből:

```bash
bash packaging/deb/build_deb.sh
```

A kész csomag a `build/` mappába kerül:

```text
build/penzugyi-naplo_0.1.0_all.deb
```

---

## Csomagtartalom ellenőrzése

Build után érdemes ellenőrizni, hogy nem került-e személyes adat a csomagba:

```bash
cd build
dpkg-deb -c penzugyi-naplo_*.deb | grep -Ei "\.env|\.github|\.vscode|Mentes|\.db|\.sqlite|\.sqlite3|\.log|/logs/|/data/"
```

Az ideális eredmény:

```text
nincs találat
```

A teljes csomagtartalom listázása:

```bash
dpkg-deb -c penzugyi-naplo_*.deb > deb-tartalom.txt
```

---

## Adatvédelem és helyi adatok

A `.deb` csomagba **nem kerülhetnek** személyes pénzügyi adatok.

A csomagolásból kizárt elemek többek között:

- `.env`
- `.github`
- `.vscode`
- `data/`
- `logs/`
- `*.db`
- `*.sqlite`
- `*.sqlite3`
- `*.log`
- `Mentes/`
- build és fejlesztői cache mappák

A valós felhasználói adatbázisnak nem az alkalmazás telepítési mappájában kell lennie, hanem felhasználói adatkönyvtárban, például:

```text
~/.local/share/PenzugyiNaplo/
```

---

## Projektstruktúra röviden

```text
penzugyi_naplo/
├── core/                  közös alkalmazáslogika
├── db/                    adatbázis-kezelő Python modulok
├── importers/             import feldolgozó logika
├── ui/                    Qt / PySide6 felület
│   ├── bills/             számlák modul
│   ├── likviditas/        likviditás modul
│   ├── main_window/       főablak és kiszervezett főablak-logika
│   ├── settings/          beállítások
│   ├── shared/            közös UI elemek
│   └── styles/            QSS stílusok
├── app_version.py         központi alkalmazás-verzióadatok
└── config.py              konfiguráció
```

---

## Verziózás

A verziószám központi helye:

```text
penzugyi_naplo/app_version.py
```

A cél az, hogy a verziószámot csak egy helyen kelljen növelni, és innen használja:

- a Névjegy ablak;
- a Verzió infó ablak;
- a `.deb` build script;
- később a GitHub release folyamat.

Jelenlegi verzió:

```text
0.1.0
```

---

## Fejlesztői dokumentáció

A részletes fejlesztői kézikönyv, moduljegyzetek és belső döntések külön dokumentációba kerülnek.

Javasolt fájl később:

```text
DEVELOPER.md
```

vagy külön `dev` ágon vezetett fejlesztői dokumentáció.

A GitHub fő README célja innentől nem a teljes fejlesztői térkép tárolása, hanem egy tiszta, külső szemmel is érthető projektbemutató.

---

## Megjegyzés

Ez a projekt saját használatra és folyamatos fejlesztésre készül. A publikus GitHub / `.deb` csomagolás célja első körben a tiszta telepítés, biztonságos csomagtartalom és későbbi frissítési folyamat megalapozása.
