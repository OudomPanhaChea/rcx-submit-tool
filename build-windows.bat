@echo off
REM ============================================================
REM  One-click builder for the Windows app.
REM  Double-click this file. When it finishes, send users the
REM  zip it prints at the end. Requires Python installed once.
REM ============================================================
setlocal
cd /d "%~dp0"

echo === Building RCX Submit Assistant (Windows) ===
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo.
    echo ERROR: Python was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during install, then run this again.
    pause
    exit /b 1
  )
)

set "PY=.venv\Scripts\python.exe"

echo Installing dependencies (first time can take a few minutes)...
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo.
echo Building the app...
"%PY%" -m PyInstaller build.spec --noconfirm
if errorlevel 1 goto :fail

echo.
echo Downloading the browser into the app folder...
set "PLAYWRIGHT_BROWSERS_PATH=%cd%\dist\RCX-Submit-Assistant\ms-playwright"
"%PY%" -m playwright install chromium
if errorlevel 1 goto :fail

echo.
echo Zipping the app for delivery...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\RCX-Submit-Assistant' -DestinationPath 'dist\RCX-Submit-Assistant-windows.zip' -Force"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo  DONE. Send this single file to your users:
echo.
echo     %cd%\dist\RCX-Submit-Assistant-windows.zip
echo.
echo  They unzip it, open the RCX-Submit-Assistant folder, and
echo  double-click RCX-Submit-Assistant.exe
echo ============================================================
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Scroll up to see the error, or send me the message above.
pause
exit /b 1
