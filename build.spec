# PyInstaller spec for RCX Submit Assistant.
# Build:  pyinstaller build.spec
# Produces a folder in dist/ ("onedir" — more reliable for Playwright than onefile).
# After building, install Chromium into dist/<app>/ms-playwright (see BUILD.md).

from PyInstaller.utils.hooks import collect_submodules

datas = [
    ("templates", "templates"),      # bundled HTML (read-only)
]
# Note: the macOS launcher (Start-RCX.command) is NOT bundled here. PyInstaller 6
# places datas inside an _internal/ subfolder, but a double-click launcher must sit
# at the folder root next to the app. The build workflow copies it there instead.

hiddenimports = collect_submodules("playwright")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RCX-Submit-Assistant",
    console=True,          # keep a console window so users can see status / close to quit
    disable_windowed_traceback=False,
    icon=None,             # set to "icon.ico" (Win) / "icon.icns" (Mac) if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="RCX-Submit-Assistant",
)
