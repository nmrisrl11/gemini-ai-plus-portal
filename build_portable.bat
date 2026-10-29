@echo off
setlocal enabledelayedexpansion
title Google AI Plus Portal — Portable Packager

echo ================================================================================
echo    GOOGLE AI PLUS PORTAL - STANDALONE PORTABLE BUILDER
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
:: 2. Ensure PyInstaller is installed
echo [*] Checking PyInstaller installation...
"%PYTHON_EXE%" -m pip show pyinstaller >nul 2>&1
if !errorlevel! neq 0 (
    echo [*] Installing PyInstaller in environment...
    "%PYTHON_EXE%" -m pip install pyinstaller
)

echo.
:: 3. Resolve App Version & Output Target Name
set "APP_VERSION="
for /f "tokens=*" %%v in ('"%PYTHON_EXE%" -c "import constants; print(constants.APP_VERSION)"') do set "APP_VERSION=%%v"
if "!APP_VERSION!"=="" set "APP_VERSION=v1.0.0"
set "APP_NAME=Google AI Plus Portal !APP_VERSION!"

echo [OK] Target Name: !APP_NAME!.exe

echo.
:: 4. Clean previous build artifacts
echo [*] Cleaning previous build cache...
if exist "build" rd /s /q "build"
if exist "dist\!APP_NAME!.exe" del /f /q "dist\!APP_NAME!.exe"
if exist "dist\GoogleAIPlusPortal.exe" del /f /q "dist\GoogleAIPlusPortal.exe"

echo.
:: 5. Build single-file executable with embedded assets & drivers
echo [*] Compiling standalone portable executable...
echo     Target: dist\!APP_NAME!.exe
echo     Options: Onefile, Windowed (no background console), Embedded High-DPI Icon
echo.

"%PYTHON_EXE%" -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --name "!APP_NAME!" ^
    --icon "images/app_icon.ico" ^
    --add-data "images;images" ^
    --collect-all "customtkinter" ^
    --collect-all "playwright" ^
    --clean ^
    main.py

echo.
:: 6. Verification & Completion
if exist "dist\!APP_NAME!.exe" (
    echo ================================================================================
    echo    BUILD SUCCESSFUL!
    echo ================================================================================
    echo.
    echo Portable standalone executable is ready:
    echo   %~dp0dist\!APP_NAME!.exe
    echo.
    echo This file is fully portable - you can move or share it freely without needing Python.
    echo.
    set /p OPEN_DIR="Open dist folder in File Explorer? (Y/N, default Y): "
    if "!OPEN_DIR!"=="" set "OPEN_DIR=Y"
    if /i "!OPEN_DIR!"=="Y" (
        explorer.exe "dist"
    )
) else (
    echo ================================================================================
    echo    BUILD FAILED! Please review the error messages above.
    echo ================================================================================
)

echo.
pause
