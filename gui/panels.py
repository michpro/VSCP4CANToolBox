# pylint: disable=missing-module-docstring, missing-class-docstring, too-many-ancestors

# from dataclasses import dataclass
import customtkinter as ctk
from .panel_left import LeftPanel
from .panel_right import RightPanel

class AppFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        app = ctk.CTkFrame(parent, corner_radius=0)
        app.pack(side='top', fill='both', expand=True)

        self.left = LeftPanel(app)
        self.right = RightPanel(app)
