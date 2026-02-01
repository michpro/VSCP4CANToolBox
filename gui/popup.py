"""
Custom popup window module.

Provides a floating window class for CustomTkinter that can be used for menus
or temporary dialogs.
"""
# pylint: disable=too-many-instance-attributes, line-too-long


import sys
import customtkinter as ctk


class CTkFloatingWindow(ctk.CTkToplevel): # pylint: disable=too-few-public-methods
    """
    On-screen popup window class for customtkinter.
    
    Based on work by Akascape. Handles platform-specific transparency and focus behavior.
    """

    def __init__(self,
                 master=None,
                 corner_radius=15,
                 border_width=1,
                 **kwargs):
        """
        Initialize the floating window.

        Args:
            master: The parent window.
            corner_radius: Corner radius of the popup frame.
            border_width: Width of the border around the frame.
            **kwargs: Additional arguments passed to the CTkFrame.
        """
        super().__init__(takefocus=1)

        self.focus()
        self.master_window = master
        self.corner = corner_radius
        self.border = border_width
        self.hidden = True

        # add transparency to suitable platforms
        if sys.platform.startswith("win"):
            self.after(200, lambda: self.overrideredirect(True))
            self.transparent_color = self._apply_appearance_mode(self._fg_color)
            self.attributes("-transparentcolor", self.transparent_color)
        elif sys.platform.startswith("darwin"):
            self.overrideredirect(True)
            self.transparent_color = 'systemTransparent'
            self.attributes("-transparent", True)
        else:
            self.attributes("-type", "splash")
            self.transparent_color = '#000001'
            self.corner = 0
            self.withdraw()

        self.frame = ctk.CTkFrame(self, bg_color=self.transparent_color, corner_radius=self.corner,
                                  border_width=self.border, **kwargs)
        self.frame.pack(expand=True, fill="both")

        self.master.bind("<Button-1>", lambda event: self._withdraw_off(), add="+") # hide menu when clicked outside
        self.bind("<Button-1>", lambda event: self._withdraw()) # hide menu when clicked inside
        self.master.bind("<Configure>", lambda event: self._withdraw()) # hide menu when master window is changed

        self.resizable(width=False, height=False)
        self.transient(self.master_window)

        self.update_idletasks()

        self.withdraw()


    def _withdraw(self):
        """Hide the window and mark it as hidden."""
        self.withdraw()
        self.hidden = True


    def _withdraw_off(self):
        """Hide the window if it is already marked as hidden (helper callback)."""
        if self.hidden:
            self.withdraw()
        self.hidden = True


    def popup(self, x=None, y=None):
        """
        Show the popup window at specific coordinates.

        Args:
            x: Screen X coordinate.
            y: Screen Y coordinate.
        """
        # pylint: disable=attribute-defined-outside-init
        self.x = x
        self.y = y
        # pylint: enable=attribute-defined-outside-init
        self.deiconify()
        self.focus()
        self.geometry(f'+{self.x}+{self.y}')
        self.hidden = False
