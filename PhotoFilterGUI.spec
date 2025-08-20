# -*- mode: python ; coding: utf-8 -*-

import certifi


a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[(certifi.where(), 'certifi')],
    hiddenimports=['pillow_heif', 'rawpy'],
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
    name='PhotoFilterGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='PhotoFilterGUI',
)
app = BUNDLE(
    coll,
    name='PhotoFilterGUI.app',
    icon=None,
    bundle_identifier=None,
)
