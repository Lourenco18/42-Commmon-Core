# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for packaging Pac-Man into a standalone executable
# (e.g. for upload to itch.io). Run with: pyinstaller --noconfirm pacman.spec
# The `mazegenerator` package itself is pulled in automatically via normal
# import analysis (it must already be installed, e.g. via `make install`).

a = Analysis(
    ['pac-man.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.')],
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
