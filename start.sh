#!/bin/bash
# Script to start the Integrated Data Protection System
# يفحص البيئة الافتراضية وينشئها إذا لزم الأمر، ثم يشغل المشروع

echo "========================================"
echo "Integrated Data Protection System"
echo "نظام حماية البيانات المتكامل"
echo "========================================"
echo ""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PATH="$PROJECT_ROOT/backend"
VENV_PATH="$PROJECT_ROOT/venv"
VENV_PYTHON="$VENV_PATH/bin/python"
VENV_ACTIVATE="$VENV_PATH/bin/activate"
REQUIREMENTS_FILE="$BACKEND_PATH/requirements.txt"

# Check if backend directory exists
if [ ! -d "$BACKEND_PATH" ]; then
    echo "❌ Error: Backend directory not found!"
    echo "Please make sure you're running this script from the project root."
    exit 1
fi

# Check if virtual environment exists
if [ -d "$VENV_PATH" ]; then
    echo "✅ Virtual environment found!"
    echo "Activating virtual environment..."
    source "$VENV_ACTIVATE"
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment activated!"
    else
        echo "⚠️  Warning: Failed to activate virtual environment"
    fi
else
    echo "⚠️  Virtual environment not found!"
    echo "Creating new virtual environment..."
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to create virtual environment!"
        exit 1
    fi
    echo "✅ Virtual environment created!"
    
    # Activate virtual environment
    source "$VENV_ACTIVATE"
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment activated!"
    fi
fi

# Check if Python is available
if [ ! -f "$VENV_PYTHON" ]; then
    echo "⚠️  Warning: Python not found in venv, using system Python"
    PYTHON_CMD="python3"
else
    PYTHON_CMD="$VENV_PYTHON"
    echo "✅ Using Python from virtual environment"
fi

# Check if requirements.txt exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "⚠️  Warning: requirements.txt not found!"
    echo "Skipping package installation..."
else
    echo ""
    echo "Checking and installing dependencies..."
    
    # Upgrade pip first
    echo "Upgrading pip..."
    "$PYTHON_CMD" -m pip install --upgrade pip --quiet
    
    # Install requirements
    echo "Installing packages from requirements.txt..."
    "$PYTHON_CMD" -m pip install -r "$REQUIREMENTS_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ All packages installed successfully!"
    else
        echo "⚠️  Warning: Some packages may have failed to install"
    fi
fi

# Check if python-multipart is installed
echo ""
echo "Checking for python-multipart..."
"$PYTHON_CMD" -c "import multipart" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing python-multipart (required for file upload)..."
    "$PYTHON_CMD" -m pip install python-multipart --quiet
    echo "✅ python-multipart installed!"
fi

# Ensure authentication packages are installed
echo ""
echo "Ensuring authentication packages are installed..."
"$PYTHON_CMD" -m pip install python-jose[cryptography] --quiet
"$PYTHON_CMD" -m pip install passlib[bcrypt] --quiet
"$PYTHON_CMD" -m pip install email-validator --quiet

# Change to backend directory
cd "$BACKEND_PATH"

echo ""
echo "========================================"
echo "Starting server..."
echo "Server will be available at:"
echo "  http://127.0.0.1:8000"
echo "  http://localhost:8000"
echo "========================================"
echo ""

# Wait a bit before opening browser
sleep 2

# Open browser (Linux/Mac)
if command -v xdg-open > /dev/null; then
    echo "Opening browser..."
    xdg-open "http://127.0.0.1:8000" &
elif command -v open > /dev/null; then
    echo "Opening browser..."
    open "http://127.0.0.1:8000" &
fi

# Start the server
echo "Starting uvicorn server..."
echo "Press Ctrl+C to stop the server"
echo ""

"$PYTHON_CMD" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

