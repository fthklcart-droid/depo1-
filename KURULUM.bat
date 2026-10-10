@echo off
chcp 65001 >nul
cd /d "%~dp0"
python kurulum.py %*
if errorlevel 1 (
  echo.
  echo Kurulum tamamlanamadi. Python 3.11+ yuklu mu? https://www.python.org/downloads/
)
pause
