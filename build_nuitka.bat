@echo off
setlocal enabledelayedexpansion
title Google AI Plus Portal — Hardened Native Builder (Nuitka)

echo ================================================================================
echo    GOOGLE AI PLUS PORTAL - NATIVE C COMPILER BUILDER (NUITKA)
echo ================================================================================
echo.

cd /d "%~dp0"

:: 1. Detect Python executable
set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python: !PYTHON_EXE!
) else (
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
        echo [OK] Using system Python
    ) else (
        echo [ERROR] Python was not found! Please install Python or configure .venv.
        pause
        exit /b 1
    )
)

echo.
:: 2. Ensure Nuitka and Zstandard are installed
echo [*] Checking Nuitka and Zstandard installation...
"%PYTHON_EXE%" -c "import nuitka, zstandard" >nul 2>&1
if !errorlevel! neq 0 (
    echo [*] Installing Nuitka and Zstandard for optimized onefile compression...
    "%PYTHON_EXE%" -m pip install "nuitka>=4.0.0" "zstandard>=0.23.0"
)

echo.
:: 3. Run build_nuitka.py
"%PYTHON_EXE%" "%~dp0build_nuitka.py"

if !errorlevel! equ 0 (
    echo.
    echo [SUCCESS] Hardened portable binary generated in dist\ folder!
) else (
    echo.
    echo [ERROR] Build failed. Please inspect logs above.
)

pause
