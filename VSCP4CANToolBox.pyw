# pylint: disable=invalid-name
"""
VSCP4CAN Toolbox Application Entry Point.

This script serves as the bootstrap for the VSCP4CAN Toolbox application.
It handles the initialization of the backend server, configures the
asynchronous execution wrapper for Tkinter, and manages the application's
main lifecycle loop.

@file VSCP4CANToolBox.pyw
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

import tk_async_execute as tae
from gui import app, server


def main():
    """
    Initialize and run the main application lifecycle.

    This function performs the following operations:
    1. Starts the communication server.
    2. Initializes the async executor for non-blocking UI operations.
    3. Launches the Tkinter main event loop (blocking).
    4. Handles graceful shutdown of services when the window is closed.
    """
    # Start the backend server logic
    server.start()

    # Initialize the thread/async wrapper for Tkinter
    tae.start()

    # Start the GUI event loop (blocks until window is closed)
    app.mainloop()

    # Cleanup: Stop the async executor
    tae.stop()

    # Cleanup: Stop the backend server
    server.stop()


if __name__ == "__main__":
    main()
