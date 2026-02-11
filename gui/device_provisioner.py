"""
Device Provisioner Module.

This module provides a dialog window for configuring the 'Drop Nickname / Reset Device'
action in the VSCP protocol. It allows setting flags for reset, factory defaults,
and idle state, as well as a delay timer.

@file device_provisioner.py
@copyright SPDX-FileCopyrightText: Copyright 2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import os
from typing import Callable
import customtkinter as ctk


class DeviceProvisioner(ctk.CTkToplevel): # pylint: disable=too-many-instance-attributes
    """
    A dialog window for setting parameters for the Drop Nickname / Reset Device command.
    """

    def __init__(self, parent: ctk.CTk, node_id: int, callback: Callable):
        # pylint: disable=line-too-long
        """
        Initialize the DeviceProvisioner dialog.

        Args:
            parent: The parent widget/window.
            node_id: The ID of the VSCP node being targeted.
            callback: Function to call upon confirmation.
                      Signature: (node_id, reset, defaults, idle, wait_time)
        """
        super().__init__(parent)
        self.callback = callback
        self.node_id = node_id

        self.title("Drop nickname-ID / Reset Device")

        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icon_path = os.path.join(icon_dir, 'vscp_logo.ico')
        self.after(250, lambda: self.iconbitmap(icon_path))

        width = 280
        height = 235

        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (width / 2))
        y = int(app_window.winfo_rooty() + (app_window.winfo_height() / 2) - (height / 2))

        self.geometry(f'{width}x{height}+{x}+{y}')
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # --- Layout ---
        self.main_frame = ctk.CTkFrame(self, fg_color='transparent')
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Header
        self.lbl_info = ctk.CTkLabel(self.main_frame, text=f"Target Node ID: 0x{node_id:02X}", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_info.pack(pady=(10, 5))

        # Options (Flags)
        self.var_reset = ctk.BooleanVar(value=False)
        self.cb_reset = ctk.CTkCheckBox(self.main_frame, text="Reset Device (Keep Nickname)", variable=self.var_reset)
        self.cb_reset.pack(pady=(5, 0), anchor="w", padx=30)

        self.var_defaults = ctk.BooleanVar(value=False)
        self.cb_defaults = ctk.CTkCheckBox(self.main_frame, text="Restore Factory Defaults", variable=self.var_defaults)
        self.cb_defaults.pack(pady=(5, 0), anchor="w", padx=30)

        self.var_idle = ctk.BooleanVar(value=False)
        self.cb_idle = ctk.CTkCheckBox(self.main_frame, text="Go to Idle/Stop State", variable=self.var_idle)
        self.cb_idle.pack(pady=(5, 0), anchor="w", padx=30)

        # Wait Time Input
        self.frame_wait = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_wait.pack(pady=(5, 10), fill="x", padx=30)

        self.lbl_wait = ctk.CTkLabel(self.frame_wait, text="Wait Time (0-255s):")
        self.lbl_wait.pack(side="left")

        vcmd = (self.register(self._validate_wait_time), '%P')
        self.entry_wait = ctk.CTkEntry(self.frame_wait, width=60, validate="key", validatecommand=vcmd)
        self.entry_wait.pack(side="left", padx=(10, 0))
        self.entry_wait.insert(0, "0")

        # Buttons
        self.frame_buttons = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_buttons.pack(side="bottom", fill="x", pady=(10, 20), padx=20)

        self.btn_cancel = ctk.CTkButton(self.frame_buttons, text="Cancel", fg_color="transparent", border_width=1,
                                        width=100, text_color=("gray10", "#DCE4EE"), command=self.destroy)
        self.btn_cancel.pack(side="left", expand=True, padx=5)

        self.btn_execute = ctk.CTkButton(self.frame_buttons, text="Execute", width=100, command=self._on_execute)
        self.btn_execute.pack(side="right", expand=True, padx=5)


    def _validate_wait_time(self, new_value: str) -> bool:
        """
        Validates the wait time entry.
        Allows only digits and ensures the value is within 0-255 (byte range).
        """
        if new_value == "":
            return True
        if not new_value.isdigit():
            return False

        value = int(new_value)
        return 0 <= value <= 255


    def _on_execute(self):
        """Collects data and triggers the callback."""
        try:
            wait_time_str = self.entry_wait.get()
            wait_time = int(wait_time_str) if wait_time_str else 0
            wait_time = max(0, min(255, wait_time))

            self.callback(
                self.node_id,
                self.var_reset.get(),
                self.var_defaults.get(),
                self.var_idle.get(),
                wait_time
            )
            self.destroy()
        except ValueError:
            # Should be prevented by validation, but safe fallback
            pass
