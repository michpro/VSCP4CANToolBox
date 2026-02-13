#!/bin/bash

cd "$(dirname "$0")"

if [ -f "./.venv/bin/python" ]; then
    ./.venv/bin/python VSCP4CANToolBox.pyw &
else
    echo ".venv/bin/python not found, attempting to use system python..."
    python3 VSCP4CANToolBox.pyw &
fi
