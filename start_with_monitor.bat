@echo off
REM Start script with MyDLP monitoring display
REM يبدأ المشروع ويعرض مراقبة MyDLP في الوقت الفعلي

setlocal enabledelayedexpansion

REM Colors (if supported)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "CYAN=[96m"
set "RESET=[0m"

echo ========================================
echo Integrated Data Protection System
echo نظام حماية البيانات المتكامل
echo ========================================
echo.

set PROJECT_ROOT=%~dp0
set BACKEND_PATH=%PROJECT_ROOT%backend
set VENV_PATH=%PROJECT_ROOT%venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe
set LOG_FILE=%BACKEND_PATH%\logs\app.log

REM Check backend
if not exist "%BACKEND_PATH%" (
    echo [ERROR] Backend folder not found!
    pause
    exit /b 1
)

REM Check/create venv
if not exist "%VENV_PATH%" (
    echo Creating virtual environment...
    python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo [ERROR] Failed to create venv!
        pause
        exit /b 1
    )
)

REM Use venv Python if available
if exist "%VENV_PYTHON%" (
    set PYTHON=%VENV_PYTHON%
) else (
    set PYTHON=python
)

REM Install requirements (silent if already installed)
echo Installing/updating packages...
"%PYTHON%" -m pip install -q --upgrade pip
"%PYTHON%" -m pip install -q -r "%BACKEND_PATH%\requirements.txt"
"%PYTHON%" -m pip install -q python-multipart

REM Go to backend
cd /d "%BACKEND_PATH%"

REM Create logs directory if not exists
if not exist "logs" mkdir logs

echo.
echo ========================================
echo Starting Server with MyDLP Monitoring
echo ========================================
echo.
echo Server URL: http://127.0.0.1:8000
echo Logs: %LOG_FILE%
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Wait before opening browser
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000

REM Start server in background and monitor logs
echo [INFO] Starting uvicorn server...
start /b "" "%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 >nul 2>&1

REM Wait a bit for server to start
timeout /t 5 /nobreak >nul

REM Monitor MyDLP status and logs
:MONITOR_LOOP
cls
echo ========================================
echo MyDLP Monitoring Dashboard
echo ========================================
echo.
echo [%date% %time%]
echo.

REM Check MyDLP status via API
echo [STATUS] Checking MyDLP status...
curl -s http://127.0.0.1:8000/api/monitoring/status > temp_status.json 2>nul
if exist temp_status.json (
    findstr /C:"mydlp" temp_status.json >nul
    if errorlevel 1 (
        echo [WARNING] Server not ready yet, waiting...
    ) else (
        echo [OK] Server is running
        type temp_status.json | findstr /C:"mydlp"
        del temp_status.json
    )
) else (
    echo [WARNING] Cannot connect to server
)

echo.
echo ========================================
echo Recent Logs (Last 20 lines)
echo ========================================
if exist "%LOG_FILE%" (
    powershell -Command "Get-Content '%LOG_FILE%' -Tail 20"
) else (
    echo No log file found yet. Logs will appear here once server starts.
)

echo.
echo ========================================
echo MyDLP Activity Monitor
echo ========================================
echo.
echo Monitoring for:
echo   - MyDLP connection status
echo   - Data blocking events
echo   - Policy violations
echo   - Email monitoring
echo.
echo Press Ctrl+C to stop monitoring
echo Refreshing every 5 seconds...
echo.

timeout /t 5 /nobreak >nul
goto MONITOR_LOOP

