@echo off
setlocal enabledelayedexpansion
title Gemini AI Plus Portal — Portable Packager (PyInstaller)

echo ================================================================================
echo    GEMINI AI PLUS PORTAL - STANDALONE PORTABLE BUILDER (PYINSTALLER)
echo ================================================================================
echo.

cd /d "%~dp0.."

:: 1. Detect Python executable
set "PYTHON_EXE="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
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
:: 2. Ensure PyInstaller is installed
echo [*] Checking PyInstaller installation...
"%PYTHON_EXE%" -m pip show pyinstaller >nul 2>&1
if !errorlevel! neq 0 (
    echo [*] Installing PyInstaller in environment...
    "%PYTHON_EXE%" -m pip install pyinstaller
)

echo.
:: 3. Delegate to scripts\build_portable.py
"%PYTHON_EXE%" "%~dp0build_portable.py"

if !errorlevel! equ 0 (
    echo.
    echo [SUCCESS] Portable binary generated in dist\ folder!
) else (
    echo.
    echo [ERROR] Build failed. Please inspect logs above.
)

pause
