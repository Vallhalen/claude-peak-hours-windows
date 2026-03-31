@echo off
echo === Claude Peak Hours — Windows Build ===
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Build with PyInstaller
echo.
echo Building executable...
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "Claude Peak Hours" ^
    --icon "assets\icon.ico" ^
    --add-data "src\strings.py;." ^
    --add-data "src\peak_hours_manager.py;." ^
    --add-data "src\tray_app.py;." ^
    src\main.pyw

echo.
if exist "dist\Claude Peak Hours.exe" (
    echo [OK] Build successful!
    echo     dist\Claude Peak Hours.exe
) else (
    echo [ERROR] Build failed.
)
echo.
pause
