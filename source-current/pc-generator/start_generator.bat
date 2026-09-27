@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python wurde nicht gefunden. Installiere Python 3 von https://www.python.org/downloads/ und aktiviere "Add Python to PATH".
  pause
  exit /b 1
)
py HistoScroll_PC_Generator.py
if errorlevel 1 pause
