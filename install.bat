@echo off
setlocal enabledelayedexpansion

:: 1. Check if python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: python is not installed or not in PATH.
    pause
    exit /b 1
)

:: 2. Create virtual environment if it doesn't exist 
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv 
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Activate the environment 
echo Activating environment...
call .\.venv\Scripts\activate.bat 

:: 4. Upgrade pip and install dependencies 
echo Upgrading pip...
python -m pip install --upgrade pip 

if exist requirements.txt (
    echo Installing requirements from requirements.txt...
    python -m pip install -r requirements.txt 
) else (
    echo Warning: requirements.txt not found.
)

:: 5. Deactivate environment 
echo Deactivating environment...
call deactivate 

echo Installation complete!
pause
