# packaging/windows/pyinstaller.spec
# ------------------------------------
#
# PyInstaller spec - Pénzügyi Napló (Windows, stabil/main csatorna)
#
# Futtatás a repo gyökeréből:
#   pyinstaller packaging/windows/pyinstaller.spec --noconfirm
#
# A kimenet a dist/PenzugyiNaplo/ mappába kerül (--onedir mód -
# ez gyorsabban indul és könnyebben hibakereshető, mint az --onefile,
# ezt csomagolja majd be az Inno Setup egy telepítőbe).

import sys
from pathlib import Path

block_cipher = None

# A spec fájl a packaging/windows/ alatt van, a repo gyökere 2 szinttel feljebb.
REPO_ROOT = Path(SPECPATH).resolve().parents[1]

datas = [
    # Alkalmazásikonok (PNG - Névjegy ablak, ablak-ikon fallback stb.)
    (str(REPO_ROOT / "icons"), "icons"),

    # QSS stíluslapok - a main_window.py ezekhez relatív, __file__-alapú
    # útvonallal nyúl, a mappastruktúrát meg kell tartani a csomagolt exe-ben is.
    (str(REPO_ROOT / "penzugyi_naplo" / "ui" / "styles"), "penzugyi_naplo/ui/styles"),

    # Fizikai aranytermék képek - a config.app_root() alapján keresi
    # az app a "assets/gold_physical_images/" relatív útvonalon.
    (str(REPO_ROOT / "assets" / "gold_physical_images"), "assets/gold_physical_images"),
]

a = Analysis(
    [str(REPO_ROOT / "main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PenzugyiNaplo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(REPO_ROOT / "packaging" / "windows" / "icons" / "app_icon_main.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PenzugyiNaplo",
)
