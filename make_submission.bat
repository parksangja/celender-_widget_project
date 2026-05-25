@echo off
cd /d "%~dp0"

set OUT=calendar_widget_submission

if exist "%OUT%" (
    rmdir /s /q "%OUT%"
)

mkdir "%OUT%"

copy "main.py" "%OUT%\" >nul
copy "calendar_engine.py" "%OUT%\" >nul
copy "ai_parser_gpt.py" "%OUT%\" >nul
copy "openai_calendar_client.py" "%OUT%\" >nul
copy "korean_datetime_parser.py" "%OUT%\" >nul
copy "holiday_updater.py" "%OUT%\" >nul
copy "executor.py" "%OUT%\" >nul
copy "test_parser.py" "%OUT%\" >nul
copy "test_executor.py" "%OUT%\" >nul
copy "test_calendar_features.py" "%OUT%\" >nul
copy "test_holiday_updater.py" "%OUT%\" >nul
copy "test_openai_calendar_client.py" "%OUT%\" >nul
copy "requirements.txt" "%OUT%\" >nul
copy ".env.example" "%OUT%\" >nul
copy "setup_env.bat" "%OUT%\" >nul
copy "run_calendar.bat" "%OUT%\" >nul
copy "make_submission.bat" "%OUT%\" >nul
copy "README.md" "%OUT%\" >nul
copy "SUBMISSION.md" "%OUT%\" >nul
copy "프로젝트 개요.md" "%OUT%\" >nul

echo.
echo Submission folder created: %OUT%
echo Do not include .venv, __pycache__, events.json, or .git.
pause
