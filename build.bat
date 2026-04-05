@echo off
REM ============================================================
REM  pic_app — Quick build (assumes venv is already active)
REM
REM  For first-time setup, run setup_and_build.bat instead.
REM
REM  Usage:
REM    .venv\Scripts\activate
REM    build.bat
REM ============================================================

echo [build] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [build] Running PyInstaller...
pyinstaller pic_app.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo [build] ERROR: PyInstaller failed.
    exit /b %ERRORLEVEL%
)

echo.
echo [build] Done ^> dist\pic_app.exe
