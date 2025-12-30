@echo off
REM Start server and open monitoring window
REM يبدأ السيرفر ويفتح نافذة المراقبة

echo Starting server in background...
start "Secure Server" cmd /k "%~dp0start.bat"

timeout /t 5 /nobreak >nul

echo Starting MyDLP Monitor...
cd /d "%~dp0"

REM Check if monitor script exists
if exist "venv\Scripts\python.exe" (
    start "MyDLP Monitor" cmd /k "venv\Scripts\python.exe monitor_mydlp.py"
) else (
    start "MyDLP Monitor" cmd /k "python monitor_mydlp.py"
)

echo.
echo Server and Monitor started!
echo - Server window: "Secure Server"
echo - Monitor window: "MyDLP Monitor"
echo.
echo Press any key to exit this window...
pause >nul

