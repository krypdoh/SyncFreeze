@echo off
echo SyncFreeze Build Script
echo =======================
echo.

REM Ensure the application icon is present
if not exist syncfreeze-icon.ico (
    echo ERROR: syncfreeze-icon.ico not found in the project root.
    exit /b 1
)

REM Stop running builds so PyInstaller can overwrite dist\*.exe
echo Stopping any running SyncFreeze processes...
taskkill /F /IM SyncFreeze.exe /T >nul 2>&1
taskkill /F /IM SyncFreeze_tray.exe /T >nul 2>&1

echo Building executables...
pyinstaller --noconfirm SyncFreeze.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)

echo.
echo Build complete! Executables:
echo   dist\SyncFreeze.exe       ^(CLI / launcher^)
echo   dist\SyncFreeze_tray.exe  ^(background tray process^)
pause
