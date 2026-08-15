# Windows build útmutató — Pénzügyi Napló

Ez a leírás azoknak szól, akik **saját maguk** szeretnék lefordítani és
telepíteni a Pénzügyi Naplót Windows-on, a forráskódból kiindulva.

> A fejlesztő (Szabó Gergely) Linux alatt dolgozik, és jelenleg nem vállal
> folyamatos Windows csomagolást/karbantartást. Ez a leírás egyszeri,
> önkiszolgáló útmutató — ha valami elakad, a hibaüzenet és a lenti
> "Gyakori hibák" szakasz általában elég támpontot ad.

---

## Amire szükséged lesz

- Windows 10/11 (x64)
- [Python 3.11+](https://www.python.org/downloads/) (telepítéskor pipáld be a "Add python.exe to PATH"-t)
- [Inno Setup 6/7](https://jrsoftware.org/isinfo.php) (a telepítő `.exe` legyártásához)
- Git (ha forrásból, branch-ekkel dolgozol)

---

## 1. lépés — Forráskód beszerzése

```powershell
git clone https://github.com/<repo-url>/penzugyi-naplo.git
cd penzugyi-naplo
```

Ha kifejezetten az **Előzetes (Preview)** verziót akarod, váltás a megfelelő branch-re:

```powershell
git checkout windows/Preview
```

Stabil verzióhoz maradj a `main` (vagy `windows/main`) ágon.

---

## 2. lépés — Python virtuális környezet

```powershell
python -m venv venv
```

**Aktiválás** — ez az a lépés, ahol elsőre szinte mindenki elakad:

```powershell
venv\Scripts\activate
```

Ha ezt a hibát kapod:

```
File ...\venv\Scripts\Activate.ps1 cannot be loaded because running scripts is disabled on this system.
```

akkor a PowerShell biztonsági beállítása blokkolja a szkriptet. Ez a parancs
**csak az aktuális ablakra** oldja fel (nem kell rendszerszinten semmit módosítani):

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
```

Sikeres aktiválás esetén a sor elején megjelenik: `(venv)`.

Ezután telepítsd a függőségeket:

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

---

## 3. lépés — Standalone .exe legyártása (PyInstaller)

**Fontos:** ezt a lépést **minden alkalommal újra kell futtatni**, ha
branch-et váltasz (pl. stable → preview), különben a régi, elavult build
kerül becsomagolásra a telepítőbe — ablakcímben, Névjegyben stb. a rossz
verzió fog megjelenni.

```powershell
pyinstaller main.py --name PenzugyiNaplo --windowed --icon packaging\icons\app_icon_main.ico --workpath build\pyinstaller --distpath dist --noconfirm
```

(Preview branch-en cseréld az ikont `app_icon_preview.ico`-ra, ha van ilyen.)

Sikeres futás után a kimenet itt lesz:

```
dist\PenzugyiNaplo\PenzugyiNaplo.exe
dist\PenzugyiNaplo\_internal\...
```

**Ellenőrzés:** indítsd el az exe-t (`dist\PenzugyiNaplo\PenzugyiNaplo.exe`),
és nézd meg hogy az ablak címsora és a Névjegy a helyes verziót mutatja-e
(Stabil vagy Előzetes), mielőtt tovább mennél a telepítő csomagolására.

---

## 4. lépés — Telepítő csomagolása (Inno Setup)

Nyisd meg az Inno Setup Compiler-t, és töltsd be a megfelelő **variant**
fájlt — **soha ne a `common.iss`-t közvetlenül**, az önmagában nem fordítható:

- Stabil verzióhoz: `packaging\windows\installer-stable.iss`
- Előzetes verzióhoz: `packaging\windows\installer-preview.iss`

Fordítás: `Build → Compile` (vagy `Ctrl+F9`).

> Az `F9` (Run) a fordítás **mellett** rögtön el is indítja a telepítőt — ha
> csak fordítani szeretnél anélkül, hogy ténylegesen telepítenél valamit a
> gépedre, használd inkább a `Ctrl+F9`-et.

Sikeres fordítás után a telepítő itt jön létre:

```
windows\PenzugyiNaplo_Setup.exe            (stabil)
windows\PenzugyiNaplo_Preview_Setup.exe    (előzetes)
```

---

## Gyakori hibák

| Hiba | Ok | Megoldás |
|---|---|---|
| `pyinstaller : term not recognized` | A venv nincs aktiválva | `venv\Scripts\activate` (lásd 2. lépés) |
| `running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Inno Setup: `Reading file (LicenseFile)` → Compile aborted | A `.iss` egy `.txt` fájlra hivatkozik, de csak `.md` van a lemezen (vagy fordítva) | Ellenőrizd hogy a `LicenseFile=` sor a ténylegesen létező fájlnévre mutat |
| Inno Setup: "`...bmp` does not exist" | Elgépelt fájlnév, vagy a kép nincs a `packaging\windows\pictures\` mappában | Ellenőrizd a fájlnevet karakterről karakterre a `common.iss`-ben és a lemezen |
| A telepített program Névjegye/ablakcíme a **másik** variant nevét mutatja | A `dist\PenzugyiNaplo\` egy korábbi, elavult build maradványa | Futtasd újra a 3. lépést (PyInstaller) a jelenlegi branch forrásából, **mielőtt** az Inno Setup-ot fordítod |
| Windows SmartScreen: "Az Intelligens alkalmazáskezelés letiltott egy alkalmazást" | A telepítő nincs digitálisan aláírva (code signing certificate) | Ez várt viselkedés aláíratlan, ismeretlen kiadótól származó programoknál. A "További információ" → "Futtatás mindenképp" opcióval felülbírálható, saját felelősségre. Végleges, széles körű terjesztéshez code signing certificate szükséges (ez egy külön, fizetős lépés, jelenleg nem része ennek a projektnek). |

---

## Miért két branch (stable/preview)?

A projekt Inno Setup csomagolása egy közös logikafájlból (`common.iss`) és
két vékony "variant" fájlból áll (`installer-stable.iss` /
`installer-preview.iss`), hasonlóan ahhoz, ahogy a Linux APT csomagolás is
egyetlen workflow-ból ágazik el `stable`/`preview` suite-ra. A két variant
más `AppId`-t, ikont, célmappát használ, hogy a két verzió **egymás
mellett**, egymást nem felülírva telepíthető legyen ugyanarra a gépre.

---

*Ez a leírás a 2026 augusztusi Windows preview csomagolás tapasztalatai
alapján készült. Ha újabb buktatóba futsz, érdemes ide is felvenni, hogy a
következő embernek (vagy neked, fél év múlva) ne kelljen újra kitalálnia.*
