#!/bin/bash

# 1. Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# 2. Check if tkinter module is available, if not - install it
echo "Checking for tkinter library..."
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "tkinter library not found. Installing python3-tk package..."
    sudo apt update
    sudo apt install -y python3-tk || { echo "Error: Failed to install python3-tk."; exit 1; }
else
    echo "tkinter library is already installed."
fi

# 3. Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    if ! python3 -m venv .venv &> /dev/null; then
        echo "venv module is missing. Installing python3-venv package..."
        sudo apt update
        sudo apt install -y python3-venv || { echo "Error: Failed to install python3-venv."; exit 1; }

        echo "Retrying virtual environment creation..."
        python3 -m venv .venv || { echo "Error: Failed to create .venv."; exit 1; }
    fi
fi

# 4. Activate the environment
echo "Activating environment..."
source .venv/bin/activate

# 5. Upgrade pip and install dependencies
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    python3 -m pip install -r requirements.txt 
else
    echo "Warning: requirements.txt not found."
fi

# 6. Deactivate environment
deactivate
echo "Installation complete!"
