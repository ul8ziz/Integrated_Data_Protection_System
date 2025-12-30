@echo off
REM Fixed version - ensures window stays open
setlocal enabledelayedexpansion

echo ========================================
echo Integrated Data Protection System
echo ========================================
echo.

set PROJECT_ROOT=%~dp0
set BACKEND_PATH=%PROJECT_ROOT%backend
set VENV_PATH=%PROJECT_ROOT%venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe

if not exist "%BACKEND_PATH%" (
    echo ERROR: Backend folder not found!
    pause
    exit /b 1
)

if not exist "%VENV_PATH%" (
    echo Creating virtual environment...
    python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo ERROR: Failed to create venv!
        pause
        exit /b 1
    )
)

if exist "%VENV_PYTHON%" (
    set PYTHON=%VENV_PYTHON%
) else (
    set PYTHON=python
)

echo Installing/updating packages...
"%PYTHON%" -m pip install -q --upgrade pip
"%PYTHON%" -m pip install -r "%BACKEND_PATH%\requirements.txt"
"%PYTHON%" -m pip install -q python-multipart

cd /d "%BACKEND_PATH%"

echo.
echo ========================================
echo Server starting...
echo URL: http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo ========================================
echo.

timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000

REM Start server - the key is to NOT use cmd /k but ensure error handling
"%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

REM If we reach here, server stopped
echo.
echo ========================================
echo Server stopped.
echo ========================================
pause

