@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python kisayol.py --run
pause
