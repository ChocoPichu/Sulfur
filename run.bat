@echo off
chcp 65001 >nul
echo Starting Sulfur...
call .venv\Scripts\activate.bat
python brain.py
pause
