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

# Ensure MongoDB packages are installed
Write-Host "Ensuring MongoDB packages are installed..." -ForegroundColor Cyan
& $pythonCmd -m pip install motor beanie pymongo --quiet

# Check MongoDB connection
Write-Host ""
Write-Host "Checking MongoDB connection..." -ForegroundColor Yellow
$envFile = Join-Path $backendPath ".env"
$mongoRunning = $false

# Check if MongoDB service is running (Windows)
try {
    $mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
    if ($mongoService -and $mongoService.Status -eq "Running") {
        Write-Host "✅ MongoDB service is running" -ForegroundColor Green
        $mongoRunning = $true
    } else {
        Write-Host "⚠️  MongoDB service not found or not running" -ForegroundColor Yellow
        Write-Host "   Trying to connect anyway..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check MongoDB service status" -ForegroundColor Yellow
    Write-Host "   Trying to connect anyway..." -ForegroundColor Yellow
}

# Check if .env file exists
if (Test-Path $envFile) {
    Write-Host "✅ .env file found" -ForegroundColor Green
    
    # Check if MongoDB settings are in .env
    $envContent = Get-Content $envFile -Raw
    if ($envContent -notmatch "MONGODB_URL") {
        Write-Host "⚠️  Warning: MONGODB_URL not found in .env file" -ForegroundColor Yellow
        Write-Host "   Adding default MongoDB settings..." -ForegroundColor Yellow
        
        # Add MongoDB settings to .env
        Add-Content -Path $envFile -Value "`n# MongoDB Configuration`nMONGODB_URL=mongodb://localhost:27017`nMONGODB_DB_NAME=Secure_db"
        Write-Host "✅ MongoDB settings added to .env" -ForegroundColor Green
    } else {
        Write-Host "✅ MongoDB settings found in .env" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  .env file not found!" -ForegroundColor Yellow
    Write-Host "   Creating .env file with default settings..." -ForegroundColor Yellow
    
    # Create .env file with default settings
    $envContent = @"
# Application Settings
APP_NAME=Secure Data Protection System
APP_VERSION=1.0.0
DEBUG=true
SECRET_KEY=change-me-to-secure-key-in-production-please

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=Secure_db

# Encryption
ENCRYPTION_KEY=change-me-to-32-byte-key-in-production-please

# Presidio
PRESIDIO_LANGUAGE=ar
PRESIDIO_SUPPORTED_ENTITIES=PERSON,PHONE_NUMBER,EMAIL_ADDRESS,CREDIT_CARD,ADDRESS,ORGANIZATION

# MyDLP
MYDLP_ENABLED=true
MYDLP_API_URL=http://127.0.0.1:8080
MYDLP_API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"@
    Set-Content -Path $envFile -Value $envContent
    Write-Host "✅ .env file created with default settings" -ForegroundColor Green
}

# Try to test MongoDB connection
Write-Host "Testing MongoDB connection..." -ForegroundColor Cyan
try {
    $testResult = & $pythonCmd -c "from motor.motor_asyncio import AsyncIOMotorClient; import asyncio; async def test(): client = AsyncIOMotorClient('mongodb://localhost:27017', serverSelectionTimeoutMS=3000); await client.admin.command('ping'); client.close(); print('OK'); asyncio.run(test())" 2>&1
    if ($testResult -match "OK") {
        Write-Host "✅ MongoDB connection successful!" -ForegroundColor Green
        $mongoRunning = $true
    } else {
        Write-Host "⚠️  Could not connect to MongoDB" -ForegroundColor Yellow
        Write-Host "   Make sure MongoDB is installed and running" -ForegroundColor Yellow
        Write-Host "   The server will try to connect on startup" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not test MongoDB connection" -ForegroundColor Yellow
    Write-Host "   Make sure MongoDB is installed and running" -ForegroundColor Yellow
    Write-Host "   The server will try to connect on startup" -ForegroundColor Yellow
}

if (-not $mongoRunning) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "⚠️  MongoDB Warning" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "MongoDB may not be running or accessible." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To install MongoDB on Windows:" -ForegroundColor Cyan
    Write-Host "  1. Download from: https://www.mongodb.com/try/download/community" -ForegroundColor White
    Write-Host "  2. Install MongoDB Community Server" -ForegroundColor White
    Write-Host "  3. Start MongoDB service from Services" -ForegroundColor White
    Write-Host ""
    Write-Host "Or start MongoDB manually:" -ForegroundColor Cyan
    Write-Host "  mongod --dbpath C:\data\db" -ForegroundColor White
    Write-Host ""
    Write-Host "The server will continue to start, but database operations may fail." -ForegroundColor Yellow
    Write-Host "Press any key to continue..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Change to backend directory
Set-Location $backendPath

# Force UTF-8 output (prevents UnicodeEncodeError for Arabic logs on Windows consoles)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting server..." -ForegroundColor Cyan
Write-Host "Server will be available at:" -ForegroundColor Yellow
Write-Host "  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "API Documentation:" -ForegroundColor Yellow
Write-Host "  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host ""
if (-not $mongoRunning) {
    Write-Host "⚠️  Note: MongoDB connection will be tested on startup" -ForegroundColor Yellow
}
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
    & $pythonCmd -X utf8 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
} catch {
    Write-Host ""
    Write-Host "❌ Error: Server failed to start!" -ForegroundColor Red
    Write-Host "Error details: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Press any key to exit..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

