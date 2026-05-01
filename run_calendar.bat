@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Run setup_env.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
