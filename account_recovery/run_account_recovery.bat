@echo off
title Account Recovery Safety Net - Google AI Plus Completer
cd /d "%~dp0"
echo =======================================================
echo    Account Recovery Safety Net: Profile Completer
echo =======================================================
echo.
echo This recovery tool attaches directly to your active,
echo authenticated browser session to complete uncompleted
echo user profiles without re-login or verification blocks.
echo.
echo Which browser has your active session?
echo   [1] Brave Browser
echo   [2] Google Chrome
echo   [3] Microsoft Edge
echo.
set /p choice="Enter choice [1-3] (Default 1): "
if "%choice%"=="" set choice=1

set "BROWSER_PARAM=brave"
if "%choice%"=="1" set "BROWSER_PARAM=brave"
if "%choice%"=="2" set "BROWSER_PARAM=chrome"
if "%choice%"=="3" set "BROWSER_PARAM=edge"

set "PY_EXE=python"
if exist "..\.venv\Scripts\python.exe" set "PY_EXE=..\.venv\Scripts\python.exe"

echo.
"%PY_EXE%" resume_browser_session.py %BROWSER_PARAM%
echo.
pause
