@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "OUT=calendar_widget_submission"

if exist "%OUT%" (
    rmdir /s /q "%OUT%"
)

mkdir "%OUT%" || goto fail

call :copy_file "main.py" || goto fail
call :copy_file "ui_support.py" || goto fail
call :copy_file "ui_styles.py" || goto fail
call :copy_file "calendar_engine.py" || goto fail
call :copy_file "ai_parser_gpt.py" || goto fail
call :copy_file "openai_calendar_client.py" || goto fail
call :copy_file "korean_datetime_parser.py" || goto fail
call :copy_file "holiday_updater.py" || goto fail
call :copy_file "data_safety.py" || goto fail
call :copy_file "executor.py" || goto fail
call :copy_file "requirements.txt" || goto fail
call :copy_file ".env.example" || goto fail
call :copy_file "setup_env.bat" || goto fail
call :copy_file "run_calendar.bat" || goto fail
call :copy_file "make_submission.bat" || goto fail
call :copy_file "README.md" || goto fail
call :copy_file "SUBMISSION.md" || goto fail
call :copy_file "프로젝트 개요.md" || goto fail

echo.
echo Submission folder created: %OUT%
echo Do not include .venv, __pycache__, events.json, holiday_cache.json, backup files, or .git.
pause
exit /b 0

:copy_file
copy "%~1" "%OUT%\" >nul
if errorlevel 1 (
    echo Failed to copy: %~1
    exit /b 1
)
exit /b 0

:fail
echo.
echo Submission folder creation failed.
pause
exit /b 1
