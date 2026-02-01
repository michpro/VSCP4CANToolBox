#!/bin/bash

# 1. Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# 2. Create virtual environment if it doesn't exist 
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv || { echo "Error: Failed to create .venv. Install python3-venv package."; exit 1; }
fi

# 3. Activate the environment 
echo "Activating environment..."
source .venv/bin/activate

# 4. Upgrade pip and install dependencies 
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    python3 -m pip install -r requirements.txt 
else
    echo "Warning: requirements.txt not found."
fi

# 5. Deactivate environment 
deactivate
echo "Installation complete!"
