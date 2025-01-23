# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

# import customtkinter as ctk
from CTkMenuBar import CTkMenuBar, CustomDropdownMenu

class Menu:
    def __init__(self, parent):
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
        self.parent.destroy()
