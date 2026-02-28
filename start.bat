@echo off
REM Start script with persistent window and MyDLP monitoring

setlocal enabledelayedexpansion

echo ========================================
echo Integrated Data Protection System
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
REM Ensure critical packages are installed
"%PYTHON%" -m pip install -q python-multipart
"%PYTHON%" -m pip install -q python-jose[cryptography]
"%PYTHON%" -m pip install -q passlib[bcrypt]
"%PYTHON%" -m pip install -q email-validator

REM Go to backend
cd /d "%BACKEND_PATH%"

REM Create logs directory
if not exist "logs" mkdir logs

REM Get local IP: prefer Wi-Fi or Ethernet adapter, skip virtual (vEthernet, Default Switch)
set LOCAL_IP=
set PREFERRED=0
for /f "delims=" %%L in ('ipconfig ^| findstr /n "."') do (
    set "LINE=%%L"
    set "LINE=!LINE:*:=!"
    echo !LINE! | findstr /i /c:"adapter" >nul
    if not errorlevel 1 (
        set PREFERRED=0
        echo !LINE! | findstr /i /c:"vEthernet" >nul
        if errorlevel 1 (
            echo !LINE! | findstr /i /c:"Default Switch" >nul
            if errorlevel 1 (
                echo !LINE! | findstr /i /c:"Wi-Fi" >nul
                if not errorlevel 1 set PREFERRED=1
                if "!PREFERRED!"=="0" echo !LINE! | findstr /i /c:"Wireless" >nul
                if not errorlevel 1 set PREFERRED=1
                if "!PREFERRED!"=="0" echo !LINE! | findstr /i /c:"Ethernet" >nul
                if not errorlevel 1 set PREFERRED=1
            )
        )
    )
    echo !LINE! | findstr /c:"IPv4" >nul
    if not errorlevel 1 if "!PREFERRED!"=="1" (
        for /f "tokens=2 delims=:" %%a in ("!LINE!") do (
            set IP_ADDR=%%a
            set IP_ADDR=!IP_ADDR: =!
            echo !IP_ADDR! | findstr /R "^127\." >nul
            if errorlevel 1 (
                echo !IP_ADDR! | findstr /R "^169\.254\." >nul
                if errorlevel 1 (
                    set LOCAL_IP=!IP_ADDR!
                    goto :found_ip
                )
            )
        )
    )
)
REM Fallback: any valid private IP except common virtual ranges (172.31, 172.18)
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP_ADDR=%%a
    set IP_ADDR=!IP_ADDR: =!
    if not "!IP_ADDR!"=="" (
        echo !IP_ADDR! | findstr /R "^127\." >nul
        if errorlevel 1 (
            echo !IP_ADDR! | findstr /R "^169\.254\." >nul
            if errorlevel 1 (
                echo !IP_ADDR! | findstr /R "^172\.31\." >nul
                if errorlevel 1 (
                    echo !IP_ADDR! | findstr /R "^172\.18\." >nul
                    if errorlevel 1 (
                        set LOCAL_IP=!IP_ADDR!
                        goto :found_ip
                    )
                )
            )
        )
    )
)
:found_ip
if "%LOCAL_IP%"=="" set LOCAL_IP=127.0.0.1

echo.
echo ========================================
echo Starting Server
echo ========================================
echo.
echo Server URL: http://0.0.0.0:8000
echo Local access: http://127.0.0.1:8000
echo Network access: http://%LOCAL_IP%:8000
echo API Docs: http://127.0.0.1:8000/docs
echo.
echo MyDLP Monitoring:
echo   - Status: Check http://127.0.0.1:8000/api/monitoring/status
echo   - Alerts: Check http://127.0.0.1:8000/api/alerts/
echo   - Logs: Check backend\logs\app.log
echo.
echo Note: Server is accessible from other devices on the network
echo ========================================
echo.

REM Wait before opening browser
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000

REM Start server - window will stay open
echo [INFO] Starting uvicorn server...
echo [INFO] MyDLP monitoring is active
echo [INFO] Server listening on all interfaces (0.0.0.0:8000)
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

REM Start server - this keeps window open
"%PYTHON%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

REM If server stops, show message
echo.
echo ========================================
echo Server stopped.
echo ========================================
echo.
pause
