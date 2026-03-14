@echo off
:: schedule_setup.bat
:: מגדיר משימה מתוזמנת ב-Windows Task Scheduler
:: מריץ את run_all.py כל יומיים בשעה 08:00

set TASK_NAME=HomeworkAgent
set SCRIPT_DIR=C:\homework-agent
set PYTHON=%SCRIPT_DIR%\.venv\Scripts\python.exe
set SCRIPT=%SCRIPT_DIR%\run_all.py

echo.
echo === Homework Agent – Task Scheduler Setup ===
echo.

:: מחק משימה קיימת אם יש
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: צור משימה חדשה – כל יומיים בשעה 08:00
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON%\" \"%SCRIPT%\"" ^
  /sc daily ^
  /mo 2 ^
  /st 08:00 ^
  /sd %date% ^
  /rl highest ^
  /f

if %errorlevel% == 0 (
    echo.
    echo [OK] Task "%TASK_NAME%" created successfully!
    echo      Runs every 2 days at 08:00
    echo.
    echo To view: schtasks /query /tn "%TASK_NAME%"
    echo To run now: schtasks /run /tn "%TASK_NAME%"
    echo To delete: schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo.
    echo [ERROR] Failed to create task. Try running as Administrator.
)

pause
