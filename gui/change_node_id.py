"""
Change Node ID dialog module for the VSCP application.

@file change_node_id.py
@copyright SPDX-FileCopyrightText: Copyright 2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import os
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import vscp


class ChangeNodeId(ctk.CTkToplevel): # pylint: disable=too-many-instance-attributes
    """
    Popup window to change a node's nickname.

    Provides a modal dialog to input a new Node ID in hexadecimal format.
    """
    def __init__(self, parent, current_id, callback):
        """
        Initialize the ChangeNodeId.

        Args:
            parent: The parent widget.
            current_id (int): The current node ID.
            callback (func): Function to call with (old_id, new_id) on success.
        """
        super().__init__(parent)
        self.callback = callback
        self.current_id = current_id
        self.title('Change Node ID')

        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icon_path = os.path.join(icon_dir, 'vscp_logo.ico')
        self.after(250, lambda: self.iconbitmap(icon_path))

        width = 270
        height = 130

        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (width / 2))
        y = int(app_window.winfo_rooty() + (app_window.winfo_height() / 2) - (height / 2))

        self.geometry(f'{width}x{height}+{x}+{y}')
        self.resizable(False, False)

        self.frame_input = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_input.pack(side='top', fill='both', expand=True)
        self.frame_input.grid_columnconfigure((0, 1, 2), weight=1)
        self.frame_input.grid_rowconfigure(0, weight=1)

        self.label_current = ctk.CTkLabel(self.frame_input, text=f"Current ID: 0x{current_id:02X}")
        self.label_current.grid(row=0, column=0, padx=(10, 5), sticky="e")

        self.label_new = ctk.CTkLabel(self.frame_input, text="New ID:")
        self.label_new.grid(row=0, column=1, padx=(5, 0), sticky="e")

        self.min_range = [0, 254]
        validate_cmd = (self.register(self._validate_input), '%P')
        self.new_id_var = ctk.StringVar(value="0x")
        self.entry = ctk.CTkEntry(self.frame_input, width=45, textvariable=self.new_id_var,
                                  validate="key", validatecommand=validate_cmd)
        self.entry.bind("<KeyRelease>", self._format_input)
        self.entry.grid(row=0, column=2, padx=(5, 10), sticky="w")

        # Focus handling after delay to ensure window/icon init doesn't steal it
        self.after(300, self._set_focus)

        self.frame_buttons = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_buttons.pack(side='top', fill='both', expand=True)
        self.frame_buttons.grid_columnconfigure((0, 1), weight=1)
        self.frame_buttons.grid_rowconfigure(0, weight=1)

        self.btn_ok = ctk.CTkButton(self.frame_buttons, text="OK", width=90, command=self._on_ok)
        self.btn_ok.grid(row=0, column=0, padx=(10, 20), sticky="e")

        self.btn_cancel = ctk.CTkButton(self.frame_buttons, text="Cancel", width=90, command=self.destroy) # pylint: disable=line-too-long
        self.btn_cancel.grid(row=0, column=1, padx=(20, 10), sticky="w")

        self.transient(parent)
        self.grab_set()


    def _set_focus(self):
        """Set initial focus to the entry widget and move cursor to end."""
        self.entry.focus_set()
        try:
            self.entry.icursor('end')
        except: # pylint: disable=bare-except
            pass


    def _format_input(self, _):
        """Format input to hex style (e.g., 0x01)."""
        input_str = self.new_id_var.get()
        if input_str.lower().startswith('0x'):
            self.new_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _validate_input(self, input_str):
        """
        Validate input range (0-254) and hex format.
        Also prevents deletion of the '0x' prefix.
        """
        # Block removal of '0x'
        if not input_str.lower().startswith('0x'):
            return False

        result = True
        if 0 != len(input_str):
            if input_str.lower().startswith('0x'):
                if 2 < len(input_str):
                    if input_str.startswith('0x00'):
                        result = False
                    else:
                        try:
                            result = self.min_range[0] <= int(input_str, 16) <= self.min_range[1]
                        except ValueError:
                            result = False
            else:
                # Should not reach here due to prefix check, but kept for logic safety
                if input_str.startswith('00'):
                    result = False
                else:
                    try:
                        result = self.min_range[0] <= int(input_str) <= self.min_range[1]
                    except ValueError:
                        result = False
        return result


    def _on_ok(self):
        """Handle OK button click."""
        try:
            val_str = self.new_id_var.get()
            if not val_str or val_str == '0x':
                return
            new_id = int(val_str, 0)

            if vscp.is_node_on_list(new_id):
                CTkMessagebox(title='Error', message=f'Node ID 0x{new_id:02X} already exists!', icon='cancel') # pylint: disable=line-too-long
                return

            if self.callback:
                self.callback(self.current_id, new_id)
            self.destroy()
        except ValueError:
            pass
