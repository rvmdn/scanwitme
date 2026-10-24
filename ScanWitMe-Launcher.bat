@echo off
setlocal
cd /d "%~dp0"

echo [ScanWitMe] Memulai aplikasi ScanWitMe PC...

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m scanwitme
    exit /b 0
)

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" -m scanwitme
    exit /b 0
)

if exist "dist\ScanWitMe\ScanWitMe.exe" (
    start "" "dist\ScanWitMe\ScanWitMe.exe"
    exit /b 0
)

echo [ScanWitMe] Error: ScanWitMe.exe atau lingkungan .venv tidak ditemukan.
pause
exit /b 1
