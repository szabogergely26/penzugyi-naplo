#!/usr/bin/env bash
set -e

PACKAGE_NAME="penzugyi-naplo"
VERSION="0.1.0"
ARCH="all"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

BUILD_ROOT="$PROJECT_ROOT/build"
BUILD_DIR="$BUILD_ROOT/${PACKAGE_NAME}_${VERSION}_${ARCH}"
DEBIAN_DIR="$BUILD_DIR/DEBIAN"

echo "Projekt gyökér: $PROJECT_ROOT"
echo "Build mappa: $BUILD_DIR"

rm -rf "$BUILD_DIR"

mkdir -p "$DEBIAN_DIR"
mkdir -p "$BUILD_DIR/usr/share/$PACKAGE_NAME"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor"
mkdir -p "$BUILD_DIR/usr/share/doc/$PACKAGE_NAME"

cp "$SCRIPT_DIR/control" "$DEBIAN_DIR/control"

# Csak az alkalmazáshoz szükséges fájlokat másoljuk.
# A fejlesztői mappák, cache-ek, build fájlok és packaging fájlok nem kerülnek a csomagba.
rsync -a \
  --exclude ".git" \
  --exclude ".gitignore" \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".ruff_cache" \
  --exclude ".mypy_cache" \
  --exclude ".pytest_cache" \
  --exclude "*.pyc" \
  --exclude "build" \
  --exclude "dist" \
  --exclude "*.deb" \
  --exclude "packaging" \
  --exclude "menubejegyzes" \
  --exclude "build-venv.sh" \
  --exclude "start.sh" \
  --exclude "penzugyi_naplo.sh" \
  --exclude "/icons/hicolor/***" \
  --exclude "/data/***" \
  "$PROJECT_ROOT/" "$BUILD_DIR/usr/share/$PACKAGE_NAME/"

# Futtató wrapper: ez lesz az Exec=penzugyi-naplo célja.
cat > "$BUILD_DIR/usr/bin/$PACKAGE_NAME" <<EOF
#!/usr/bin/env bash
cd /usr/share/$PACKAGE_NAME
exec python3 main.py "\$@"
EOF

chmod 755 "$BUILD_DIR/usr/bin/$PACKAGE_NAME"

# Desktop bejegyzés.
cp "$SCRIPT_DIR/penzugyi-naplo.desktop" \
  "$BUILD_DIR/usr/share/applications/penzugyi-naplo.desktop"

# Ikonok.
cp -r "$PROJECT_ROOT/packaging/icons/hicolor/"* \
  "$BUILD_DIR/usr/share/icons/hicolor/"

# Debian changelog.
cat > "$BUILD_DIR/usr/share/doc/$PACKAGE_NAME/changelog" <<EOF
penzugyi-naplo (0.1.0) unstable; urgency=low

  * Első helyi tesztelésre szánt deb csomag.
  * Alkalmazásikon, desktop bejegyzés és alap telepítési struktúra hozzáadva.
  * Függőségek és csomagtartalom tisztítása.

 -- Gergely Szabó <local@example.com>  Mon, 01 Jun 2026 12:00:00 +0200
EOF

gzip -9 "$BUILD_DIR/usr/share/doc/$PACKAGE_NAME/changelog"

# Copyright fájl.
cat > "$BUILD_DIR/usr/share/doc/$PACKAGE_NAME/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: penzugyi-naplo
Source: local project

Files: *
Copyright: 2026 Gergely Szabó
License: proprietary
 All rights reserved.
EOF

# Jogosultságok rendezése.
find "$BUILD_DIR" -type d -exec chmod 755 {} \;
find "$BUILD_DIR" -type f -exec chmod 644 {} \;
chmod 755 "$BUILD_DIR/usr/bin/$PACKAGE_NAME"

# Csomag építése root tulajdonosi metaadatokkal.
dpkg-deb --root-owner-group --build "$BUILD_DIR"

echo
echo "Kész:"
echo "$BUILD_ROOT/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
