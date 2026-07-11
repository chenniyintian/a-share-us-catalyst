@echo off
setlocal

cd /d "%~dp0\.."

REM Activate venv
call .venv\Scripts\activate.bat

REM Auto-detect and add --send-email if .env has SMTP config
set EXTRA_ARGS=
setlocal enabledelayedexpansion
findstr /B "SMTP_USER=." .env >nul 2>&1
if !errorlevel! equ 0 (
    findstr /B "SMTP_PASSWORD=." .env >nul 2>&1
    if !errorlevel! equ 0 (
        findstr /B "EMAIL_TO=." .env >nul 2>&1
        if !errorlevel! equ 0 (
            set EXTRA_ARGS=--send-email
        )
    )
)
findstr /B "TELEGRAM_BOT_TOKEN=." .env >nul 2>&1
if !errorlevel! equ 0 (
    findstr /B "TELEGRAM_CHAT_ID=." .env >nul 2>&1
    if !errorlevel! equ 0 (
        set EXTRA_ARGS=!EXTRA_ARGS! --send-telegram
    )
)

REM Run
set PYTHONPATH=src
python -m ashare_us_catalyst.cli --top 5 %EXTRA_ARGS%

endlocal
echo [%date% %time%] Report completed
