@echo off
setlocal

cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_full_allure_report.ps1"

echo.
echo Finished. Press any key to close this window.
pause >nul
