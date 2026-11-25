@echo off
title Gemini AI Plus Portal
cd /d "%~dp0"

set "VENV_DIR=%~dp0.venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PYTHONW_EXE=%VENV_DIR%\Scripts\pythonw.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

if not exist "%PYTHON_EXE%" (
    echo ========================================================
    echo  Setting up environment for Gemini AI Plus Portal...
    echo ========================================================
    python -m venv "%VENV_DIR%"
    "%PIP_EXE%" install -r "%~dp0requirements.txt"
)

:: If CLI mode is requested, run in this console window
if "%1"=="--cli" (
    "%PYTHON_EXE%" "%~dp0main.py" %*
    goto :end
)

:: Launch GUI in background with pythonw and immediately close CMD window
start "" "%PYTHONW_EXE%" "%~dp0main.py" %*
exit /b 0

:end
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] An error occurred while launching.
    pause
)
