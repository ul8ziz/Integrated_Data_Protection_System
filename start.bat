@echo off
REM Start script with persistent window and MyDLP monitoring
REM يبدأ المشروع مع نافذة دائمة ومراقبة MyDLP

setlocal enabledelayedexpansion

echo ========================================
echo Integrated Data Protection System
echo نظام حماية البيانات المتكامل
echo ========================================
echo.

set PROJECT_ROOT=%~dp0
set BACKEND_PATH=%PROJECT_ROOT%backend
set VENV_PATH=%PROJECT_ROOT%venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe

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

REM Install requirements
echo Installing/updating packages...
"%PYTHON%" -m pip install -q --upgrade pip
"%PYTHON%" -m pip install -q -r "%BACKEND_PATH%\requirements.txt"
"%PYTHON%" -m pip install -q python-multipart

REM Go to backend
cd /d "%BACKEND_PATH%"

REM Create logs directory
if not exist "logs" mkdir logs

echo.
echo ========================================
echo Starting Server
echo ========================================
echo.
echo Server URL: http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo MyDLP Monitoring:
echo   - Status: Check http://127.0.0.1:8000/api/monitoring/status
echo   - Alerts: Check http://127.0.0.1:8000/api/alerts/
echo   - Logs: Check backend\logs\app.log
echo.
echo ========================================
echo.

REM Wait before opening browser
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000

REM Start server - window will stay open
echo [INFO] Starting uvicorn server...
echo [INFO] MyDLP monitoring is active
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

REM Start server - this keeps window open
"%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

REM If server stops, show message
echo.
echo ========================================
echo Server stopped.
echo ========================================
echo.
pause
