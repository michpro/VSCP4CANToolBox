"""
Main application panels module.

This module initializes the main split-view layout containing the left panel
(configuration/scanning) and the right panel (logging/events).
"""
# pylint: disable=too-many-ancestors


import customtkinter as ctk
from .panel_left import LeftPanel
from .panel_right import RightPanel


class AppFrame(ctk.CTkFrame):
    """
    Main application frame.

    Acts as the container for the LeftPanel and RightPanel widgets.
    """

    def __init__(self, parent):
        """
        Initialize the AppFrame.

        Args:
            parent: The parent widget associated with this frame.
        """
        super().__init__(parent)

        app = ctk.CTkFrame(parent, corner_radius=0)
        app.pack(side='top', fill='both', expand=True)

        self.left = LeftPanel(app)
        self.right = RightPanel(app)
