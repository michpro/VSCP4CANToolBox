# pylint: disable=missing-module-docstring, too-many-instance-attributes, line-too-long

import sys
import customtkinter as ctk

class CTkFloatingWindow(ctk.CTkToplevel): # pylint: disable=too-few-public-methods
    """
    On-screen popup window class for customtkinter
    Author: Akascape
    """
    def __init__(self,
                 master=None,
                 corner_radius=15,
                 border_width=1,
                 **kwargs):

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
        self.withdraw()
        self.hidden = True


    def _withdraw_off(self):
        if self.hidden:
            self.withdraw()
        self.hidden = True


    def popup(self, x=None, y=None): # pylint: disable=missing-function-docstring
        # pylint: disable=attribute-defined-outside-init
        self.x = x
        self.y = y
        # pylint: enable=attribute-defined-outside-init
        self.deiconify()
        self.focus()
        self.geometry(f'+{self.x}+{self.y}')
        self.hidden = False
