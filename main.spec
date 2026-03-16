# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas_fitz, binaries_fitz, hiddenimports_fitz = collect_all('fitz')
datas_pymupdf, binaries_pymupdf, hiddenimports_pymupdf = collect_all('pymupdf')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries_fitz + binaries_pymupdf,
    datas=datas_fitz + datas_pymupdf,
    hiddenimports=hiddenimports_fitz + hiddenimports_pymupdf + ['frontend', 'PIL', 'PIL.Image', 'PIL.ImageTk'],
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
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)