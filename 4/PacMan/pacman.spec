# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for packaging Pac-Man into a standalone executable
# (e.g. for upload to itch.io). Run with: make package
# (or: pyinstaller --noconfirm pacman.spec)
# The `mazegenerator` package itself is pulled in automatically via normal
# import analysis (it must already be installed, e.g. via `make install`).
#
# Note: config.json is NOT bundled here as a PyInstaller resource, since
# pac-man.py reads its config argument as a plain file path (not via
# PyInstaller's internal resource path). The `package` Makefile target
# copies the real config.json next to the built executable instead, so
# it can be passed normally on the command line: ./pacman config.json

a = Analysis(
    ['pac-man.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pacman',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
