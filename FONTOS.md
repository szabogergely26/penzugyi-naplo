# Pénzügyi Napló – Preview → Main kiadási ellenőrzőlista

Ez a dokumentum azt foglalja össze, mit kell ellenőrizni és szükség esetén átírni, mielőtt a **Preview** ágon tesztelt változatból **main/stabil** kiadás készül.

A cél:

- a `penzugyi-naplo-preview` csomag külön tesztelhető legyen a stabil mellé telepítve;
- a stabil `penzugyi-naplo` csomagot ne írja felül a preview;
- a preview adatbázis/profil később különüljön el a stabil adatbázistól;
- a stabil kiadás előtt minden preview-specifikus név, ikon, csomag és APT beállítás ellenőrizve legyen.

---

## 1. Alaplogika

### Stabil csomag

```text
Package: penzugyi-naplo
Command: penzugyi-naplo
Desktop file: penzugyi-naplo.desktop
Menu name: Pénzügyi Napló
Icon name: penzugyi-naplo
Install dir: /usr/share/penzugyi-naplo
APT suite: stable
```

### Preview csomag

```text
Package: penzugyi-naplo-preview
Command: penzugyi-naplo-preview
Desktop file: penzugyi-naplo-preview.desktop
Menu name: Pénzügyi Napló (Előzetes)
Icon name: penzugyi-naplo-preview
Install dir: /usr/share/penzugyi-naplo-preview
APT suite: preview
```

Fontos: a preview akkor valóban külön alkalmazás, ha a csomagnév, indítóparancs, desktop fájl, ikon és telepítési mappa is különbözik.

---

## 2. Verzió ellenőrzése

Fájl:

```text
penzugyi_naplo/app_version.py
```

### Preview kiadásnál

Példa:

```python
APP_VERSION = "0.1.8~preview1"
```

vagy alkalmazáskijelzéshez külön kezelve:

```python
APP_VERSION = "0.1.8-preview1"
DEB_VERSION = "0.1.8~preview1"
```

### Stabil/main kiadásnál

Példa:

```python
APP_VERSION = "0.1.8"
```

Ellenőrizendő:

- ne maradjon `preview`, `előzetes`, `beta` jelölés a stabil verzióban;
- a stabil verzió nagyobb legyen, mint az előzetes Debian-verzió.

Példa Debian rendezésre:

```text
0.1.8~preview1 < 0.1.8
```

---

## 3. `build_deb.sh` ellenőrzése

Fájl:

```text
packaging/deb/build_deb.sh
```

### Preview build értékek

```bash
APP_NAME="penzugyi-naplo-preview"
BIN_NAME="penzugyi-naplo-preview"
ICON_NAME="penzugyi-naplo-preview"
DESKTOP_FILE="$ROOT_DIR/packaging/deb/penzugyi-naplo-preview.desktop"
```

### Stabil/main build értékek

```bash
APP_NAME="penzugyi-naplo"
BIN_NAME="penzugyi-naplo"
ICON_NAME="penzugyi-naplo"
DESKTOP_FILE="$ROOT_DIR/packaging/deb/penzugyi-naplo.desktop"
```

### Preview desktop szövegek

```bash
DESKTOP_NAME="Pénzügyi Napló (Előzetes)"
DESKTOP_GENERIC_NAME="Pénzügyi napló alkalmazás – előzetes verzió"
DESKTOP_COMMENT="Előzetes verzió – helyi adatbázist használó pénzügyi napló..."
```

### Stabil desktop szövegek

```bash
DESKTOP_NAME="Pénzügyi Napló"
DESKTOP_GENERIC_NAME="Pénzügyi napló alkalmazás"
DESKTOP_COMMENT="Helyi adatbázist használó pénzügyi napló bevételek, kiadások, számlák, statisztikák és aranyszámla nyilvántartásához"
```

---

## 4. Debian control fájl

Fájl:

```text
packaging/deb/control.in
```

A csomagnév legyen sablonos:

```text
Package: @PACKAGE_NAME@
Version: @VERSION@
Section: utils
Priority: optional
Architecture: all
Maintainer: Gergely Szabó <szabogergely26@gmail.com>
Depends: python3, libpyside6-py3-6.8, python3-pyside6.qtcharts, python3-odf
Description: Pénzügyi Napló
 Saját fejlesztésű, helyi adatbázist használó pénzügyi napló alkalmazás.
 Kezeli a bevételeket, kiadásokat, számlákat, statisztikákat és az aranyszámla
 nyilvántartást.
```

A `build_deb.sh` cserélje:

```bash
sed \
  -e "s|@PACKAGE_NAME@|$APP_NAME|g" \
  -e "s|@VERSION@|$VERSION|g" \
  "$CONTROL_TEMPLATE" > "$PKG_DIR/DEBIAN/control"
```

### Fontos

Preview csomaghoz ne legyen:

```text
Conflicts: penzugyi-naplo
Replaces: penzugyi-naplo
```

Mert akkor a preview nem települhetne a stabil mellé.

---

## 5. Desktop fájlok

### Preview desktop fájl

```text
packaging/deb/penzugyi-naplo-preview.desktop
```

Tartalma:

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=@DESKTOP_NAME@
GenericName=@DESKTOP_GENERIC_NAME@
Comment=@DESKTOP_COMMENT@
Exec=@BIN_NAME@
Icon=@ICON_NAME@
Terminal=false
Categories=Office;Finance;
Keywords=pénzügy;napló;bevétel;kiadás;számla;statisztika;aranyszámla;megtakarítás;finance;budget;gold;
StartupNotify=true
```

### Stabil desktop fájl

```text
packaging/deb/penzugyi-naplo.desktop
```

Ugyanez a sablon használható, csak a `build_deb.sh` stabil értékeket adjon neki:

```text
Name=Pénzügyi Napló
Exec=penzugyi-naplo
Icon=penzugyi-naplo
```

Preview buildnél:

```text
Name=Pénzügyi Napló (Előzetes)
Exec=penzugyi-naplo-preview
Icon=penzugyi-naplo-preview
```

---

## 6. Rendszerikonok

Stabil ikonok:

```text
/usr/share/icons/hicolor/1024x1024/apps/penzugyi-naplo.png
/usr/share/icons/hicolor/128x128/apps/penzugyi-naplo.png
/usr/share/icons/hicolor/256x256/apps/penzugyi-naplo.png
/usr/share/icons/hicolor/64x64/apps/penzugyi-naplo.png
/usr/share/icons/hicolor/48x48/apps/penzugyi-naplo.png
/usr/share/icons/hicolor/32x32/apps/penzugyi-naplo.png
```

Preview ikonok:

```text
/usr/share/icons/hicolor/1024x1024/apps/penzugyi-naplo-preview.png
/usr/share/icons/hicolor/128x128/apps/penzugyi-naplo-preview.png
/usr/share/icons/hicolor/256x256/apps/penzugyi-naplo-preview.png
/usr/share/icons/hicolor/64x64/apps/penzugyi-naplo-preview.png
/usr/share/icons/hicolor/48x48/apps/penzugyi-naplo-preview.png
/usr/share/icons/hicolor/32x32/apps/penzugyi-naplo-preview.png
```

A preview csomag nem telepíthet `penzugyi-naplo.png` nevű rendszerikont, mert az ütközik a stabil csomaggal.

A `build_deb.sh` preview ikonmásolása:

```bash
if [ -d "$ROOT_DIR/packaging/icons/hicolor" ]; then
  while IFS= read -r -d '' icon_file; do
    rel_dir="$(dirname "${icon_file#$ROOT_DIR/packaging/icons/hicolor/}")"
    ext="${icon_file##*.}"

    mkdir -p "$PKG_DIR/usr/share/icons/hicolor/$rel_dir"
    cp "$icon_file" "$PKG_DIR/usr/share/icons/hicolor/$rel_dir/$ICON_NAME.$ext"
  done < <(find "$ROOT_DIR/packaging/icons/hicolor" -type f \( -name "*.png" -o -name "*.svg" \) -print0)
fi
```

---

## 7. Telepítési mappák és indítók

### Stabil

```text
/usr/bin/penzugyi-naplo
/usr/share/penzugyi-naplo/
/usr/share/applications/penzugyi-naplo.desktop
```

### Preview

```text
/usr/bin/penzugyi-naplo-preview
/usr/share/penzugyi-naplo-preview/
/usr/share/applications/penzugyi-naplo-preview.desktop
```

Ha a preview csomag bármelyik stabil útvonalat telepíti, akkor javítani kell.

---

## 8. Adatbázis és profil – későbbi fontos feladat

A preview ne használja a stabil adatbázist.

### Stabil javasolt adatprofil

```text
~/.local/share/PenzugyiNaplo/PenzugyiNaplo/
```

### Preview javasolt adatprofil

```text
~/.local/share/PenzugyiNaploPreview/PenzugyiNaploPreview/
```

Ennek célja:

- a preview ne tudja elrontani a napi használatú stabil adatbázist;
- adatbázis-séma változtatás preview-ben biztonságosan tesztelhető legyen;
- valós adatokkal teszteléshez inkább másolatot/importot használjunk.

Későbbi technikai irány:

```bash
export PENZUGYI_NAPLO_CHANNEL="preview"
```

A preview indító script ezt átadhatja az alkalmazásnak, az app pedig ez alapján külön adatkönyvtárat választhat.

---

## 9. APT repository ellenőrzés

### Preview repo

```text
Suite: preview
Package: penzugyi-naplo-preview
Version: 0.1.8~preview1
```

### Stable repo

```text
Suite: stable
Package: penzugyi-naplo
Version: 0.1.8
```

Preview Packages ellenőrzés:

```bash
grep -nE "Package:|Version:|Filename:" dists/preview/main/binary-all/Packages
```

Jó preview eredmény:

```text
Package: penzugyi-naplo-preview
Version: 0.1.8~preview1
Filename: pool/preview/main/p/penzugyi-naplo-preview/penzugyi-naplo-preview_0.1.8~preview1_all.deb
```

Stabil Packages ellenőrzés:

```bash
grep -nE "Package:|Version:|Filename:" dists/stable/main/binary-all/Packages
```

Jó stabil eredmény:

```text
Package: penzugyi-naplo
Version: 0.1.8
Filename: pool/stable/main/p/penzugyi-naplo/penzugyi-naplo_0.1.8_all.deb
```

---

## 10. Build ellenőrzések

### Build futtatása

```bash
./packaging/deb/build_deb.sh
```

### Csomag metaadatok

Preview:

```bash
dpkg-deb -f build/penzugyi-naplo-preview_0.1.8~preview1_all.deb Package Version Architecture
```

Jó eredmény:

```text
Package: penzugyi-naplo-preview
Version: 0.1.8~preview1
Architecture: all
```

Stabil:

```bash
dpkg-deb -f build/penzugyi-naplo_0.1.8_all.deb Package Version Architecture
```

Jó eredmény:

```text
Package: penzugyi-naplo
Version: 0.1.8
Architecture: all
```

---

## 11. Csomagtartalom ellenőrzése

### Preview kritikus fájlok

```bash
dpkg-deb -c build/penzugyi-naplo-preview_0.1.8~preview1_all.deb | grep -E "usr/bin/penzugyi-naplo-preview|applications/penzugyi-naplo-preview.desktop|usr/share/penzugyi-naplo-preview/$"
```

Jó eredmény:

```text
./usr/bin/penzugyi-naplo-preview
./usr/share/applications/penzugyi-naplo-preview.desktop
./usr/share/penzugyi-naplo-preview/
```

### Stabil kritikus fájlok

```bash
dpkg-deb -c build/penzugyi-naplo_0.1.8_all.deb | grep -E "usr/bin/penzugyi-naplo|applications/penzugyi-naplo.desktop|usr/share/penzugyi-naplo/$"
```

Jó eredmény:

```text
./usr/bin/penzugyi-naplo
./usr/share/applications/penzugyi-naplo.desktop
./usr/share/penzugyi-naplo/
```

---

## 12. Csomagtisztaság ellenőrzése

Ezek ne kerüljenek a csomagba:

```text
.env
.ruff_cache
.vscode
Mentes
menubejegyzes
packaging
logs
requirements-dev.txt
build-venv.sh
venv-How-to.txt
```

Ellenőrzés:

```bash
dpkg-deb -c build/penzugyi-naplo-preview_0.1.8~preview1_all.deb | grep -E "/(\.env|\.ruff_cache|\.vscode|Mentes|menubejegyzes|packaging|requirements-dev\.txt|build-venv\.sh|venv-How-to\.txt|logs)(/|$)"
```

Jó eredmény: nincs kimenet.

---

## 13. Telepítési próba

### Preview telepítés stabil mellé

```bash
sudo apt install ./build/penzugyi-naplo-preview_0.1.8~preview1_all.deb
```

Ellenőrzés:

```bash
apt policy penzugyi-naplo penzugyi-naplo-preview
```

Jó állapot:

```text
penzugyi-naplo          -> telepítve stabil verzió
penzugyi-naplo-preview  -> telepítve preview verzió
```

Indítás:

```bash
penzugyi-naplo
penzugyi-naplo-preview
```

Mindkettőnek külön kell indulnia.

---

## 14. MAIN-re húzás előtti utolsó ellenőrzés

Mielőtt Preview-ből main/stabil kiadás lesz:

- [ ] `APP_VERSION` stabil verzióra állítva
- [ ] `APP_NAME=penzugyi-naplo`
- [ ] `BIN_NAME=penzugyi-naplo`
- [ ] `ICON_NAME=penzugyi-naplo`
- [ ] `DESKTOP_FILE=penzugyi-naplo.desktop`
- [ ] desktop név: `Pénzügyi Napló`
- [ ] csomagnév: `penzugyi-naplo`
- [ ] ikonok: `penzugyi-naplo.png`
- [ ] APT suite: `stable`
- [ ] preview adatprofil nem írja felül a stabil adatbázist
- [ ] build lefutott
- [ ] `.deb` metaadatok ellenőrizve
- [ ] csomagtartalom ellenőrizve
- [ ] helyi telepítési próba sikeres
- [ ] GitHub Actions build sikeres
- [ ] APT repo publikálás sikeres

---

## 15. Tiltott / veszélyes állapotok

Preview csomagban veszélyes:

```text
Package: penzugyi-naplo
Exec=penzugyi-naplo
Icon=penzugyi-naplo
/usr/bin/penzugyi-naplo
/usr/share/applications/penzugyi-naplo.desktop
/usr/share/icons/hicolor/.../penzugyi-naplo.png
/usr/share/penzugyi-naplo/
```

Stabil csomagban veszélyes:

```text
Package: penzugyi-naplo-preview
Exec=penzugyi-naplo-preview
Icon=penzugyi-naplo-preview
Pénzügyi Napló (Előzetes)
```

Ha ezek bármelyike rossz csatornában jelenik meg, a kiadást meg kell állítani.

