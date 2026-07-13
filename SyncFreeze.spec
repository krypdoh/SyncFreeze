# -*- mode: python ; coding: utf-8 -*-

# ── CLI executable ────────────────────────────────────────────────────────────
a_cli = Analysis(
    ['syncfreeze\\main.py'],
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
pyz_cli = PYZ(a_cli.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    a_cli.binaries,
    a_cli.datas,
    [],
    name='SyncFreeze',
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
    icon=['syncfreeze-icon.ico'],
)

# ── Tray executable ───────────────────────────────────────────────────────────
a_tray = Analysis(
    ['syncfreeze\\tray_main.py'],
    pathex=[],
    binaries=[],
    datas=[('syncfreeze-icon.ico', '.')],
    hiddenimports=['pystray._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_tray = PYZ(a_tray.pure)

exe_tray = EXE(
    pyz_tray,
    a_tray.scripts,
    a_tray.binaries,
    a_tray.datas,
    [],
    name='SyncFreeze_tray',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['syncfreeze-icon.ico'],
)
