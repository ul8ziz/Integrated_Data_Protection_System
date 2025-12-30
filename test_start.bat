@echo off
REM Test script to see what's happening
echo Test script running...
echo.
echo Current directory: %CD%
echo.
echo Checking Python...
python --version
echo.
echo Checking if venv exists...
if exist "venv" (
    echo venv folder exists!
) else (
    echo venv folder NOT found!
)
echo.
echo Press any key to continue...
pause >nul
echo.
echo Testing venv Python...
if exist "venv\Scripts\python.exe" (
    echo venv Python found!
    venv\Scripts\python.exe --version
) else (
    echo venv Python NOT found!
)
echo.
echo Script finished. Window will stay open.
pause

