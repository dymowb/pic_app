@echo off
setlocal enabledelayedexpansion
title pic_app — Setup and Build

echo ============================================================
echo  pic_app — One-Click Setup and Build
echo  Output: dist\pic_app.exe
echo ============================================================
echo.

REM ── 1. Check Python ────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.11+ from https://python.org
    echo         Make sure "Add Python to PATH" is checked during install.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found.

REM ── 2. Create virtual environment ────────────────────────
if not exist ".venv" (
    echo [..] Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause & exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

REM ── 3. Activate venv ───────────────────────────────
call .venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not activate virtual environment.
    pause & exit /b 1
)
echo [OK] Virtual environment activated.

REM ── 4. Upgrade pip silently ──────────────────────────
echo [..] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM ── 5. Install dependencies ────────────────────────────
echo [..] Installing dependencies (this may take a minute)...
pip install -r requirements-dev.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Dependency installation failed.
    pause & exit /b 1
)
echo [OK] Dependencies installed.

REM ── 6. Run tests ──────────────────────────────────────
echo [..] Running tests...
python -m pytest tests/ -q --tb=short 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Some tests failed — build will continue but please review above.
    echo        Press any key to continue anyway, or Ctrl+C to abort.
    pause
)

REM ── 7. Clean previous build ────────────────────────────
echo [..] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

REM ── 8. Build with PyInstaller ────────────────────────────
echo [..] Building exe with PyInstaller...
pyinstaller pic_app.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed. See output above for details.
    pause & exit /b 1
)

REM ── 9. Done ──────────────────────────────────────────
echo.
echo ============================================================
echo  [SUCCESS] Build complete!
echo  Executable: %CD%\dist\pic_app.exe
echo ============================================================
echo.
echo Opening dist\ folder...
explorer dist

pause
