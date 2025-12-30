@echo off
REM Simplified version - keeps window open always
REM نسخة مبسطة - تبقى النافذة مفتوحة دائماً

echo ========================================
echo Integrated Data Protection System
echo ========================================
echo.

REM Get project root
set PROJECT_ROOT=%~dp0
set BACKEND_PATH=%PROJECT_ROOT%backend
set VENV_PATH=%PROJECT_ROOT%venv
set VENV_PYTHON=%VENV_PATH%\Scripts\python.exe

REM Check backend
if not exist "%BACKEND_PATH%" (
    echo ERROR: Backend folder not found!
    pause
    exit /b 1
)

REM Check/create venv
if not exist "%VENV_PATH%" (
    echo Creating virtual environment...
    python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        echo ERROR: Failed to create venv!
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
echo Installing packages...
"%PYTHON%" -m pip install -q --upgrade pip
"%PYTHON%" -m pip install -r "%BACKEND_PATH%\requirements.txt"
"%PYTHON%" -m pip install -q python-multipart

REM Go to backend
cd /d "%BACKEND_PATH%"

REM Start server
echo.
echo ========================================
echo Server starting at http://127.0.0.1:8000
echo Press Ctrl+C to stop
echo ========================================
echo.

timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000

REM Keep window open by using cmd /k
cmd /k ""%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

