# Script to start the Integrated Data Protection System
# يفحص البيئة الافتراضية وينشئها إذا لزم الأمر، ثم يشغل المشروع

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Integrated Data Protection System" -ForegroundColor Cyan
Write-Host "نظام حماية البيانات المتكامل" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$venvPath = Join-Path $projectRoot "venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"
$requirementsFile = Join-Path $backendPath "requirements.txt"

# Check if backend directory exists
if (-not (Test-Path $backendPath)) {
    Write-Host "❌ Error: Backend directory not found!" -ForegroundColor Red
    Write-Host "Please make sure you're running this script from the project root." -ForegroundColor Yellow
    exit 1
}

# Check if virtual environment exists
if (Test-Path $venvPath) {
    Write-Host "✅ Virtual environment found!" -ForegroundColor Green
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    
    # Activate virtual environment
    if (Test-Path $venvActivate) {
        & $venvActivate
        Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Warning: Activation script not found, using Python directly" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Virtual environment not found!" -ForegroundColor Yellow
    Write-Host "Creating new virtual environment..." -ForegroundColor Yellow
    
    # Create virtual environment
    python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Error: Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Virtual environment created!" -ForegroundColor Green
    
    # Activate virtual environment
    if (Test-Path $venvActivate) {
        & $venvActivate
        Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
    }
}

# Check if Python is available
if (-not (Test-Path $venvPython)) {
    Write-Host "⚠️  Warning: Python not found in venv, using system Python" -ForegroundColor Yellow
    $pythonCmd = "python"
} else {
    $pythonCmd = $venvPython
    Write-Host "✅ Using Python from virtual environment" -ForegroundColor Green
}

# Check if requirements.txt exists
if (-not (Test-Path $requirementsFile)) {
    Write-Host "⚠️  Warning: requirements.txt not found!" -ForegroundColor Yellow
    Write-Host "Skipping package installation..." -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "Checking and installing dependencies..." -ForegroundColor Yellow
    
    # Upgrade pip first
    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    & $pythonCmd -m pip install --upgrade pip --quiet
    
    # Install requirements
    Write-Host "Installing packages from requirements.txt..." -ForegroundColor Cyan
    & $pythonCmd -m pip install -r $requirementsFile
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Warning: Some packages may have failed to install" -ForegroundColor Yellow
    } else {
        Write-Host "✅ All packages installed successfully!" -ForegroundColor Green
    }
}

# Check and install critical packages (required for authentication and file upload)
Write-Host ""
Write-Host "Checking for critical packages..." -ForegroundColor Yellow
$multipartCheck = & $pythonCmd -c "import multipart; print('installed')" 2>$null
if (-not $multipartCheck) {
    Write-Host "Installing python-multipart (required for file upload)..." -ForegroundColor Cyan
    & $pythonCmd -m pip install python-multipart --quiet
    Write-Host "✅ python-multipart installed!" -ForegroundColor Green
}

# Ensure authentication packages are installed
Write-Host "Ensuring authentication packages are installed..." -ForegroundColor Cyan
& $pythonCmd -m pip install python-jose[cryptography] --quiet
& $pythonCmd -m pip install passlib[bcrypt] --quiet
& $pythonCmd -m pip install email-validator --quiet

# Change to backend directory
Set-Location $backendPath

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting server..." -ForegroundColor Cyan
Write-Host "Server will be available at:" -ForegroundColor Yellow
Write-Host "  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Wait a bit before opening browser
Start-Sleep -Seconds 2

# Open browser
Write-Host "Opening browser..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8000"

# Start the server
Write-Host "Starting uvicorn server..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

try {
    & $pythonCmd -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} catch {
    Write-Host ""
    Write-Host "❌ Error: Server failed to start!" -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

