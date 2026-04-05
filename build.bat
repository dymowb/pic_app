@echo off
REM ============================================================
REM  pic_app — Windows build script
REM  Produces: dist\pic_app.exe (single-file, no console window)
REM
REM  Prerequisites:
REM    .venv\Scripts\activate
REM    pip install -r requirements-dev.txt
REM ============================================================

echo [build] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [build] Running PyInstaller...
pyinstaller src\main.py ^
  --name pic_app ^
  --onefile ^
  --windowed ^
  --icon assets\icons\app.ico ^
  --add-data "assets;assets"

if %ERRORLEVEL% NEQ 0 (
    echo [build] ERROR: PyInstaller failed.
    exit /b %ERRORLEVEL%
)

echo.
echo [build] Done. Output: dist\pic_app.exe
