@echo off
setlocal enabledelayedexpansion

echo ════════════════════════════════════════════════
echo   KNOWLEDGE MERGER v4.3.2 - MSI BUILDER
echo ════════════════════════════════════════════════

echo [1/3] Compiling React Frontend...
call npm run build

echo [2/3] Checking for Inno Setup (ISCC.exe)...
set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not exist "!ISCC_PATH!" (
    echo [!] ISCC.exe not found in default path.
    echo [!] Attempting auto-install via winget...
    winget install JRSoftware.InnoSetup -e --silent
    set "ISCC_PATH=ISCC.exe"
)

echo [3/3] Generating Threaded Installer Package...
"!ISCC_PATH!" build-installer.iss

echo ════════════════════════════════════════════════
echo   BUILD COMPLETE - check setup/output/
echo ════════════════════════════════════════════════
pause
