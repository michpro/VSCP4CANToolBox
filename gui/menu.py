"""
Application Menu Module.

This module defines the main application menu bar using CTkMenuBar.
It handles file and settings menu options and their associated commands,
such as exiting the application.

@file menu.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

# import customtkinter as ctk
from CTkMenuBar import CTkMenuBar, CustomDropdownMenu

class Menu: # pylint: disable=too-few-public-methods
    """
    Manages the main menu bar for the application.

    Creates 'File' and 'Settings' menus with dropdown options.
    """

    def __init__(self, parent):
        """
        Initializes the Menu instance.

        Args:
            parent: The parent widget (typically the main Application window).
        """
        self.parent = parent
        menu = CTkMenuBar(parent)
        entry_file = menu.add_cascade("File")
        # entry_edit = menu.add_cascade("Edit")
        entry_settings = menu.add_cascade("Settings")
        # entry_about = menu.add_cascade("About")

        dropdown_file = CustomDropdownMenu(widget=entry_file, corner_radius=0)
        dropdown_file.add_separator()
        dropdown_file.add_option(option="Exit", command=self.exit_app)

        dropdown_settings = CustomDropdownMenu(widget=entry_settings, corner_radius=0)
        dropdown_settings.add_option(option="Preferences")
        dropdown_settings.add_option(option="Update")

        self.menu = menu


    def exit_app(self):
        """
        Closes the application.

        Destroys the parent window.
        """
        self.parent.destroy()
