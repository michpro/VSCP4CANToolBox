"""
Tooltip Module.

This module provides a `ToolTip` class that displays a pop-up window with text
when the user hovers over a specified widget.

@file tooltip.py
@copyright SPDX-FileCopyrightText: Copyright 2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

import tkinter as tk
import customtkinter as ctk


class ToolTip: # pylint: disable=too-many-instance-attributes
    """
    Creates a tooltip for a given widget as the user hovers the mouse cursor.
    """

    def __init__(self, widget, text):
        """
        Initializes the tooltip.

        Args:
            widget: The widget to bind the tooltip to.
            text: The text to display in the tooltip.
        """
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
        self._id1 = self.widget.bind("<Enter>", self.enter)
        self._id2 = self.widget.bind("<Leave>", self.leave)


    def enter(self, _event=None):
        """
        Schedules the tooltip display on mouse enter.
        """
        self.schedule()


    def leave(self, _event=None):
        """
        Hides the tooltip on mouse leave.
        """
        self.unschedule()
        self.hide_tip()


    def schedule(self):
        """
        Schedules the tooltip to be displayed after a short delay.
        """
        self.unschedule()
        self.id = self.widget.after(500, self.show_tip)


    def unschedule(self):
        """
        Cancels the scheduled tooltip display.
        """
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)


    def show_tip(self, _event=None):
        """
        Creates and displays the tooltip window.
        """
        # Calculate position relative to the widget using winfo_root instead of bbox
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20

        if self.text:
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")

            # Attempt to set transparent background for the Toplevel window
            # This removes the white rectangle behind rounded corners (mainly for Windows)
            transparent_key = "#000001"
            bg_fallback = "gray20"

            try:
                tw.wm_attributes("-transparentcolor", transparent_key)
                tw.configure(bg=transparent_key)
            except Exception: # pylint: disable=broad-exception-caught
                # Fallback for systems that don't support -transparentcolor
                tw.configure(bg=bg_fallback)

            label = ctk.CTkLabel(tw, text=self.text, corner_radius=6,
                                 fg_color="gray60", text_color="black", width=200, wraplength=190)
            label.pack()


    def hide_tip(self):
        """
        Destroys the tooltip window.
        """
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()
