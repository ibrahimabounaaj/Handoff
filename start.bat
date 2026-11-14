@echo off
cd /d "%~dp0"
title Handoff
if not exist backboard_key.txt (
  echo Paste your Backboard API key and press Enter:
  set /p KEY=
  call echo %%KEY%%> backboard_key.txt
)
set /p BACKBOARD_API_KEY=<backboard_key.txt
if not defined BACKBOARD_API_KEY (
  echo Paste your Backboard API key and press Enter:
  set /p BACKBOARD_API_KEY=
  call echo %%BACKBOARD_API_KEY%%> backboard_key.txt
)

set "PY="
set "LOCALPY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%LOCALPY%" set "PY=%LOCALPY%"
if not defined PY ( py -3 --version >nul 2>&1 && set "PY=py -3" )
if not defined PY (
  echo Python is not installed. Installing Python 3.12 now, accept any prompts...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if exist "%LOCALPY%" set "PY=%LOCALPY%"
)
if not defined PY (
  echo.
  echo Could not install Python automatically. Copy this window's text to Claude.
  pause
  exit /b
)

echo Using Python: %PY%
echo Installing requirements (first run only takes a minute)...
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Install failed. Copy this window's text to Claude.
  pause
  exit /b
)
echo Starting Handoff... your browser will open at http://localhost:8501
%PY% -m streamlit run app.py
pause
