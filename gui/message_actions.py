# pylint: disable=too-many-lines
"""
VSCP Message Actions Module.

This module provides a UI window for configuring and applying automated actions.
Users can define specific VSCP events to be sent manually, periodically, or
in response to other incoming VSCP events on the bus.

@file message_actions.py
@copyright SPDX-FileCopyrightText: Copyright 2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

import os
import json
import uuid
import re
from tkinter import filedialog
import customtkinter as ctk
import vscp
from .common import set_app_icon
from .tooltip import ToolTip


class MessageActions(ctk.CTkToplevel): # pylint: disable=too-many-instance-attributes
    """
    Control window for configuring VSCP message actions.

    Allows defining VSCP events (target events) and rules for when they should
    be transmitted (Manual, Periodic, or Reactive to another event).
    """

    def __init__(self, parent): # pylint: disable=too-many-statements
        # pylint: disable=line-too-long
        """Initialize the actions configuration window."""
        super().__init__(parent)

        self.rx_param_map = {}

        # Window setup
        self.title("Actions Configuration")
        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_path = os.path.join(current_path, 'icons', 'vscp_logo.ico')
        if os.path.exists(icon_path):
            self.after(250, lambda: set_app_icon(self, icon_path))

        width = 1400
        height = 760

        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (width / 2))
        y = int(app_window.winfo_rooty() + (app_window.winfo_height() / 2) - (height / 2))

        self.geometry(f'{width}x{height}+{x}+{y}')
        self.resizable(False, False)

        # Hide window on close
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.withdraw()

        # Active actions storage
        self.actions = []
        self.target_param_entries = []

        # --- Layout Configuration ---
        self.grid_columnconfigure(0, weight=0, minsize=500) # Left panel width
        self.grid_columnconfigure(1, weight=1) # Right panel expands
        self.grid_rowconfigure(0, weight=1) # Main content area expands

        # ==========================================
        # LEFT PANEL: ACTION BUILDER
        # ==========================================
        self.frame_builder = ctk.CTkFrame(self)
        self.frame_builder.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frame_builder.grid_columnconfigure(1, weight=1)

        # Reset all row weights to 0 so components don't randomly expand
        for i in range(12):
            self.frame_builder.grid_rowconfigure(i, weight=0)

        # Row 10 is an empty spacer that pushes row 11 (bottom buttons) exactly to the bottom
        self.frame_builder.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(self.frame_builder, text="Action Builder", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(2, 5))

        # --- Target Event Definition ---
        ctk.CTkLabel(self.frame_builder, text="1. Event to Send", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 2))

        # Target Node ID (Origin Simulator)
        ctk.CTkLabel(self.frame_builder, text="Origin Node ID:", width=158, anchor="w").grid(row=2, column=0, sticky="w", padx=(10, 5), pady=1)
        self.var_target_node = ctk.StringVar(value="* DEFAULT *")
        self.var_target_node.trace_add("write", lambda *args, v=self.var_target_node, mv=255: self._apply_number_validation(v, mv, "* DEFAULT *"))
        self.target_node_entry = ctk.CTkEntry(self.frame_builder, textvariable=self.var_target_node)
        self.target_node_entry.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=1)
        self.target_node_entry.bind("<FocusIn>", lambda e, w=self.target_node_entry: self._on_focus_in_any(e, w, "* DEFAULT *"))
        self.target_node_entry.bind("<FocusOut>", lambda e, w=self.target_node_entry: self._on_focus_out_any(e, w, "* DEFAULT *"))

        # Target Priority
        ctk.CTkLabel(self.frame_builder, text="Priority:", width=158, anchor="w").grid(row=3, column=0, sticky="w", padx=(10, 5), pady=1)
        priorities = [vscp.dictionary.priority_name(i) for i in range(8)]
        self.target_prio_combo = ctk.CTkComboBox(self.frame_builder, values=priorities)
        self.target_prio_combo.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=1)
        self.target_prio_combo.set(vscp.dictionary.priority_name(3)) # Default: Normal high

        # Target Class
        ctk.CTkLabel(self.frame_builder, text="Class:", width=158, anchor="w").grid(row=4, column=0, sticky="w", padx=(10, 5), pady=1)
        self.all_classes = sorted([f"{c['class']}" for c in vscp.dictionary.get()])
        self.target_class_combo = ctk.CTkComboBox(self.frame_builder, values=self.all_classes, command=self._on_target_class_change)
        self.target_class_combo.grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=1)

        # Target Type
        ctk.CTkLabel(self.frame_builder, text="Type:", width=158, anchor="w").grid(row=5, column=0, sticky="w", padx=(10, 5), pady=1)
        self.target_type_combo = ctk.CTkComboBox(self.frame_builder, values=["Select Class first"], command=self._on_target_type_change)
        self.target_type_combo.grid(row=5, column=1, sticky="ew", padx=(0, 10), pady=1)

        # Dynamic Payload Frame wrapped in a strict-height frame (grid_propagate=False stops it from expanding)
        self.target_payload_wrapper = ctk.CTkFrame(self.frame_builder, height=180, fg_color="transparent")
        self.target_payload_wrapper.grid_propagate(False)
        self.target_payload_wrapper.grid(row=6, column=0, columnspan=2, sticky="ew", padx=0, pady=(2, 5))
        self.target_payload_wrapper.grid_columnconfigure(0, weight=1)
        self.target_payload_wrapper.grid_rowconfigure(0, weight=1)

        self.target_payload_frame = ctk.CTkScrollableFrame(self.target_payload_wrapper, label_text="Payload Parameters")
        self.target_payload_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=0)

        # Initialize combo boxes state
        if self.all_classes:
            self.target_class_combo.set(self.all_classes[0])
            self._on_target_class_change(self.all_classes[0])

        # --- Trigger Definition ---
        ctk.CTkLabel(self.frame_builder, text="2. Trigger Condition", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 2))

        self.trigger_mode = ctk.StringVar(value="Manual")
        self.trigger_seg_btn = ctk.CTkSegmentedButton(self.frame_builder, values=["Manual", "Periodic", "Reactive"], variable=self.trigger_mode, command=self._on_trigger_mode_change)
        self.trigger_seg_btn.grid(row=8, column=0, columnspan=2, sticky="ew", padx=10, pady=2)

        # Dynamic Trigger Frame
        self.trigger_frame = ctk.CTkFrame(self.frame_builder, fg_color="transparent")
        self.trigger_frame.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=0, pady=(0, 2))
        self.trigger_frame.grid_columnconfigure(1, weight=1)

        # Will be populated by _on_trigger_mode_change
        self.trigger_widgets = {}
        self._on_trigger_mode_change("Manual")

        # Bottom Buttons (Inside Builder Frame)
        self.frame_left_ops = ctk.CTkFrame(self.frame_builder, fg_color="transparent")
        self.frame_left_ops.grid(row=11, column=0, columnspan=2, sticky="ew", padx=5, pady=(2, 10))
        self.frame_left_ops.grid_columnconfigure(0, weight=1)

        self.btn_add_action = ctk.CTkButton(self.frame_left_ops, text="Add Action", command=self._add_action, fg_color="green", height=32)
        self.btn_add_action.grid(row=0, column=0, sticky="ew", padx=5)


        # ==========================================
        # RIGHT PANEL: ACTION LIST
        # ==========================================
        self.frame_list = ctk.CTkFrame(self)
        self.frame_list.grid(row=0, column=1, sticky="nsew", padx=(0, 5), pady=5)
        self.frame_list.grid_columnconfigure(0, weight=1)

        # Row 1 (scrollable area) expands to push row 2 (bottom buttons) down
        self.frame_list.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_list, text="Active Actions", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, pady=(5, 5))

        self.scroll_actions = ctk.CTkScrollableFrame(self.frame_list)
        self.scroll_actions.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))

        # Bottom Buttons (Inside List Frame)
        self.frame_right_ops = ctk.CTkFrame(self.frame_list, fg_color="transparent")
        self.frame_right_ops.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 10))
        self.frame_right_ops.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(self.frame_right_ops, text="Load Actions", command=self._load_actions, height=32).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(self.frame_right_ops, text="Save Actions", command=self._save_actions, height=32).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(self.frame_right_ops, text="Clear All", command=self._clear_all_actions, fg_color="#C0392B", height=32).grid(row=0, column=2, padx=5, sticky="ew")
        # pylint: enable=line-too-long


    # --- Input Validation / Trace Factory ---

    def _apply_number_validation(self, var, max_val, placeholder='* ANY *'): # pylint: disable=too-many-branches
        """Active interactive string validator logic ensuring limits and proper Hex format."""
        s = var.get()
        if not s or s == placeholder:
            return
        if s.lower() == '0x':
            if s != '0x':
                var.set('0x')
            return
        try:
            if s.lower().startswith('0x'):
                # Extract clean hex part and re-append '0x'
                clean = '0x' + re.sub(r'[^0-9A-Fa-f]', '', s[2:])
                if clean == '0x':
                    if s != '0x':
                        var.set('0x')
                    return
                val = int(clean, 16)
                val = min(val, max_val)
                # Enforce uppercase hex representation
                new_s = '0x' + hex(val)[2:].upper()
                if s != new_s:
                    var.set(new_s)
            else:
                # Extract clean decimal part
                clean = re.sub(r'[^0-9]', '', s)
                if not clean:
                    if s != '':
                        var.set('')
                    return
                val = int(clean, 10)
                val = min(val, max_val)
                new_s = str(val)
                if s != new_s:
                    var.set(new_s)
        except Exception: # pylint: disable=broad-except
            pass
        # pylint: enable=line-too-long


    def _on_focus_in_any(self, _event, entry, placeholder="* ANY *"):
        """Clear placeholder on focus."""
        if entry.get() == placeholder:
            entry.delete(0, "end")


    def _on_focus_out_any(self, _event, entry, placeholder="* ANY *"):
        """Restore placeholder if empty on focus lost."""
        if not entry.get().strip():
            entry.insert(0, placeholder)


    def _update_target_rx_combos(self): # pylint: disable=too-many-branches
        """Updates available RX parameters across all target dynamic combos."""
        if not hasattr(self, 'target_param_entries') or not hasattr(self, 'trigger_mode'):
            return

        mode = self.trigger_mode.get()
        options = []

        # Populate specific named parameters if Reactive trigger is fully selected
        if mode == "Reactive" and hasattr(self, 'react_param_entries') and self.react_param_entries:
            for item in self.react_param_entries:
                # Use decoded friendly name generated during react_type_change
                p_name = item.get('friendly_name', item['def']['name'])
                opt_str = f"{p_name}"

                # Prevent dictionary key collision if VSCP def has duplicate param names
                original_opt_str = opt_str
                counter = 1
                while opt_str in options:
                    opt_str = f"{original_opt_str} ({counter})"
                    counter += 1

                options.append(opt_str)
                self.rx_param_map[opt_str] = {'offset': item['offset'], 'length': item['def']['length']} # pylint: disable=line-too-long
        else:
            # Fallback to generic byte indices if Any/* Any * is selected or non-reactive mode
            for i in range(8):
                opt_str = f"Byte {i}"
                options.append(opt_str)
                self.rx_param_map[opt_str] = {'offset': i, 'length': 1}

        if not options:
            options = ["Byte 0"]
            self.rx_param_map["Byte 0"] = {'offset': 0, 'length': 1}

        for t_item in self.target_param_entries:
            # Manage mode availability based on trigger mode (No 'From RX' if not Reactive)
            if 'combo_mode' in t_item:
                if mode == "Reactive":
                    t_item['combo_mode'].configure(state="normal", values=["Static", "From RX"])
                else:
                    t_item['mode_var'].set("Static")
                    t_item['combo_mode'].configure(values=["Static"], state="disabled")
                    # Explicitly reflect 'Static' view since set() might not fire the toggle callback # pylint: disable=line-too-long
                    t_item['dyn_frame'].pack_forget()
                    t_item['static_entry'].pack(fill="x", expand=True)

            if 'rx_combo' in t_item:
                current_val = t_item['rx_combo'].get()
                t_item['rx_combo'].configure(values=options)
                if current_val not in options:
                    t_item['rx_combo'].set(options[0])


    # --- UI Callbacks ---

    def _on_target_class_change(self, selected_class):
        """Update Target Type combo based on selected Class."""
        types_list = vscp.dictionary.class_types(selected_class)
        if types_list:
            type_names = sorted([t['type'] for t in types_list])
            self.target_type_combo.configure(values=type_names)
            self.target_type_combo.set(type_names[0])
            self._on_target_type_change(type_names[0])
        else:
            self.target_type_combo.configure(values=["N/A"])
            self.target_type_combo.set("N/A")
            self._on_target_type_change("N/A")


    def _on_target_type_change(self, _): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Generate input fields for event payload based on dictionary definition."""
        # Clear existing entries
        for widget in self.target_payload_frame.winfo_children():
            widget.destroy()
        self.target_param_entries.clear()

        class_name = self.target_class_combo.get()
        type_name = self.target_type_combo.get()

        if type_name == "N/A":
            return

        params = vscp.dictionary.get_event_parameters(class_name, type_name)

        if not params:
            ctk.CTkLabel(self.target_payload_frame, text="No payload parameters required.", text_color="gray").pack(pady=10) # pylint: disable=line-too-long
            self._update_target_rx_combos()
            return

        # Fetch underlying original VSCP parameter names (description) from dictionary
        class_id = vscp.dictionary.class_id(class_name)
        type_id = vscp.dictionary.type_id(class_id, type_name)
        data_descr = vscp.dictionary._get_data_description(class_id, type_id) # pylint: disable=protected-access
        dlc_def = data_descr.get('dlc', {})
        sorted_keys = sorted(dlc_def.keys())

        for i, param in enumerate(params):
            frame = ctk.CTkFrame(self.target_payload_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)

            param_name = param['name']
            if i < len(sorted_keys):
                orig_key = sorted_keys[i]
                param_name = dlc_def[orig_key].get('d', param_name)

            dtype = param['type']
            lbl = ctk.CTkLabel(frame, text=f"{param_name}:", width=158, anchor="w")
            lbl.grid(row=0, column=0, sticky="w", padx=(0, 5))

            var_mode = ctk.StringVar(value="Static")
            combo_mode = ctk.CTkComboBox(frame, values=["Static", "From RX"], variable=var_mode, width=90) # pylint: disable=line-too-long
            combo_mode.grid(row=0, column=1, sticky="w", padx=(0, 5))

            container = ctk.CTkFrame(frame, fg_color="transparent")
            container.grid(row=0, column=2, sticky="ew", padx=(0, 15))
            frame.grid_columnconfigure(2, weight=1)

            # Smart placeholder based on type
            pl_text = f"Length: {param['length']} byte(s)"
            if 'int' in dtype:
                max_v = (2**(8*param['length'])) - 1
                pl_text = f"e.g. 0-{max_v} or 0x{max_v:X}"
            elif dtype in ('ascii', 'utf8'):
                pl_text = f"e.g. text (max {param['length']} chars)"
            elif dtype in ('float', 'double'):
                pl_text = "e.g. 12.34"
            elif dtype in ('onoffst', 'bool'):
                pl_text = "e.g. 0 (Off) or 1 (On)"

            # ---- Static Mode Configuration ----
            static_var = ctk.StringVar()
            if 'int' in dtype:
                max_v = (2**(8*param['length'])) - 1
                static_var.trace_add("write", lambda *args, v=static_var, mv=max_v: self._apply_number_validation(v, mv)) # pylint: disable=line-too-long
            elif dtype in ('onoffst', 'bool'):
                static_var.trace_add("write", lambda *args, v=static_var, mv=1: self._apply_number_validation(v, mv)) # pylint: disable=line-too-long

            static_entry = ctk.CTkEntry(container, textvariable=static_var, placeholder_text=pl_text) # pylint: disable=line-too-long
            static_entry.pack(fill="x", expand=True)

            # ---- Dynamic Mode Configuration ----
            dyn_frame = ctk.CTkFrame(container, fg_color="transparent")
            rx_combo = ctk.CTkComboBox(dyn_frame, values=["Byte 0"], width=95)
            rx_combo.pack(side="left", padx=(0, 5))

            ctk.CTkLabel(dyn_frame, text="Offset:").pack(side="left", padx=(0, 2))
            offset_var = ctk.StringVar(value="0")
            offset_entry = ctk.CTkEntry(dyn_frame, textvariable=offset_var, width=60)
            offset_entry.pack(side="left", fill="x", expand=True)

            # Dynamic toggle logic to hide/show respective frames based on Mode
            def toggle_mode(choice, s_entry=static_entry, d_frame=dyn_frame):
                if choice == "Static":
                    d_frame.pack_forget()
                    s_entry.pack(fill="x", expand=True)
                else:
                    s_entry.pack_forget()
                    d_frame.pack(fill="x", expand=True)

            combo_mode.configure(command=toggle_mode)

            # Store references
            self.target_param_entries.append({
                'mode_var': var_mode,
                'combo_mode': combo_mode,
                'static_entry': static_entry,
                'dyn_frame': dyn_frame,
                'rx_combo': rx_combo,
                'offset_entry': offset_entry,
                'def': param
            })

            # Add tooltip with constraints if available
            constraint = param.get('constraint')
            if constraint:
                if isinstance(constraint, dict) and 'min' in constraint:
                    ToolTip(static_entry, f"Min: {constraint['min']}, Max: {constraint['max']}")
                elif isinstance(constraint, list):
                    options = ", ".join([f"{k}:{v}" for k, v in constraint])
                    ToolTip(static_entry, f"Options: {options}")

        # Keep context synchronized for dynamic parameters
        self._update_target_rx_combos()


    def _on_react_type_change(self, selected_type): # pylint: disable=too-many-locals
        """Generate input fields for reactive payload based on dictionary definition."""
        if not hasattr(self, 'react_payload_frame') or not self.react_payload_frame.winfo_exists():
            return

        for widget in self.react_payload_frame.winfo_children():
            widget.destroy()
        self.react_param_entries.clear()

        class_name = self.trigger_widgets['class'].get()
        if class_name == "* ANY *" or selected_type == "* ANY *":
            ctk.CTkLabel(self.react_payload_frame, text="Select Class and Type to filter by payload.", text_color="gray").pack(pady=5) # pylint: disable=line-too-long
            self._update_target_rx_combos()
            return

        params = vscp.dictionary.get_event_parameters(class_name, selected_type)
        if not params:
            ctk.CTkLabel(self.react_payload_frame, text="No payload parameters for this event.", text_color="gray").pack(pady=5) # pylint: disable=line-too-long
            self._update_target_rx_combos()
            return

        class_id = vscp.dictionary.class_id(class_name)
        type_id = vscp.dictionary.type_id(class_id, selected_type)
        data_descr = vscp.dictionary._get_data_description(class_id, type_id) # pylint: disable=protected-access
        dlc_def = data_descr.get('dlc', {})
        sorted_keys = sorted(dlc_def.keys())

        current_offset = 0
        for i, param in enumerate(params):
            frame = ctk.CTkFrame(self.react_payload_frame, fg_color="transparent")
            frame.pack(fill="x", pady=1)
            frame.grid_columnconfigure(1, weight=1)

            param_name = param['name']
            if i < len(sorted_keys):
                orig_key = sorted_keys[i]
                param_name = dlc_def[orig_key].get('d', param_name)

            dtype = param['type']
            # inner label pad = 0px outer + 5px wrapper + 5px frame padding = 10px visual offset
            lbl = ctk.CTkLabel(frame, text=f"{param_name}:", width=158, anchor="w")
            lbl.grid(row=0, column=0, sticky="w", padx=(0, 5))

            pl_text = "* ANY *"
            var = ctk.StringVar(value=pl_text)

            if 'int' in dtype:
                max_v = (2**(8*param['length'])) - 1
                var.trace_add("write", lambda *args, v=var, mv=max_v: self._apply_number_validation(v, mv)) # pylint: disable=line-too-long
            elif dtype in ('onoffst', 'bool'):
                var.trace_add("write", lambda *args, v=var, mv=1: self._apply_number_validation(v, mv)) # pylint: disable=line-too-long

            entry = ctk.CTkEntry(frame, textvariable=var)
            entry.grid(row=0, column=1, sticky="ew", padx=(0, 15)) # 15 to adjust for inner scrollbar # pylint: disable=line-too-long

            entry.bind("<FocusIn>", lambda e, w=entry: self._on_focus_in_any(e, w))
            entry.bind("<FocusOut>", lambda e, w=entry: self._on_focus_out_any(e, w))

            self.react_param_entries.append({
                'entry': entry,
                'def': param,
                'offset': current_offset,
                'friendly_name': param_name
            })

            current_offset += param['length']

            constraint = param.get('constraint')
            if constraint:
                if isinstance(constraint, dict) and 'min' in constraint:
                    ToolTip(entry, f"Min: {constraint['min']}, Max: {constraint['max']}")
                elif isinstance(constraint, list):
                    options = ", ".join([f"{k}:{v}" for k, v in constraint])
                    ToolTip(entry, f"Options: {options}")

        self._update_target_rx_combos()


    def _on_trigger_mode_change(self, mode): # pylint: disable=too-many-statements
        # pylint: disable=line-too-long
        """Switch trigger configuration UI based on selected mode."""
        for widget in self.trigger_frame.winfo_children():
            widget.destroy()
        self.trigger_widgets.clear()

        # Reset row weights so only the correct element expands
        for i in range(10):
            self.trigger_frame.grid_rowconfigure(i, weight=0)

        width_outer = 158

        if mode == "Manual":
            ctk.CTkLabel(self.trigger_frame, text="Action will be triggered manually via the 'Execute' button.", text_color="gray").grid(row=0, column=0, pady=40, padx=10)

        elif mode == "Periodic":
            ctk.CTkLabel(self.trigger_frame, text="Interval (ms):", width=width_outer, anchor="w").grid(row=0, column=0, sticky="w", pady=(20, 5), padx=(10, 5))
            var_int = ctk.StringVar(value="1000")
            var_int.trace_add("write", lambda *args, v=var_int, mv=86400000: self._apply_number_validation(v, mv, "1000"))
            entry = ctk.CTkEntry(self.trigger_frame, textvariable=var_int, placeholder_text="e.g. 1000")
            entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(20, 5))
            entry.bind("<FocusIn>", lambda e, w=entry: self._on_focus_in_any(e, w, "1000"))
            entry.bind("<FocusOut>", lambda e, w=entry: self._on_focus_out_any(e, w, "1000"))
            self.trigger_widgets['interval'] = entry

        elif mode == "Reactive":
            # 0. Execution Delay Simulation
            ctk.CTkLabel(self.trigger_frame, text="Delay (ms):", width=width_outer, anchor="w").grid(row=0, column=0, sticky="w", pady=1, padx=(11, 5))
            var_delay = ctk.StringVar(value="0")
            var_delay.trace_add("write", lambda *args, v=var_delay, mv=86400000: self._apply_number_validation(v, mv, "0"))
            entry_delay = ctk.CTkEntry(self.trigger_frame, textvariable=var_delay)
            entry_delay.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=1)
            entry_delay.bind("<FocusIn>", lambda e, w=entry_delay: self._on_focus_in_any(e, w, "0"))
            entry_delay.bind("<FocusOut>", lambda e, w=entry_delay: self._on_focus_out_any(e, w, "0"))
            self.trigger_widgets['delay'] = entry_delay

            # 1. Node ID
            ctk.CTkLabel(self.trigger_frame, text="Node ID:", width=width_outer, anchor="w").grid(row=1, column=0, sticky="w", pady=1, padx=(11, 5))
            var_node = ctk.StringVar(value="* ANY *")
            var_node.trace_add("write", lambda *args, v=var_node, mv=255: self._apply_number_validation(v, mv))
            entry_node = ctk.CTkEntry(self.trigger_frame, textvariable=var_node)
            entry_node.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=1)
            entry_node.bind("<FocusIn>", lambda e, w=entry_node: self._on_focus_in_any(e, w))
            entry_node.bind("<FocusOut>", lambda e, w=entry_node: self._on_focus_out_any(e, w))
            self.trigger_widgets['node'] = entry_node

            # 2. Trigger Class
            ctk.CTkLabel(self.trigger_frame, text="Incoming Class:", width=width_outer, anchor="w").grid(row=2, column=0, sticky="w", pady=1, padx=(11, 5))
            classes = ["* ANY *"] + self.all_classes
            combo_cls = ctk.CTkComboBox(self.trigger_frame, values=classes)
            combo_cls.grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=1)
            self.trigger_widgets['class'] = combo_cls

            # 3. Trigger Type
            ctk.CTkLabel(self.trigger_frame, text="Incoming Type:", width=width_outer, anchor="w").grid(row=3, column=0, sticky="w", pady=1, padx=(11, 5))
            combo_typ = ctk.CTkComboBox(self.trigger_frame, values=["* ANY *"])
            combo_typ.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=1)
            self.trigger_widgets['type'] = combo_typ

            # 4. Scrollable Frame for Payload Matching Parameters (Strict height wrapping)
            self.react_payload_wrapper = ctk.CTkFrame(self.trigger_frame, height=132, fg_color="transparent")
            self.react_payload_wrapper.grid_propagate(False)
            self.react_payload_wrapper.grid(row=4, column=0, columnspan=2, sticky="ew", padx=0, pady=(2, 2))
            self.react_payload_wrapper.grid_columnconfigure(0, weight=1)
            self.react_payload_wrapper.grid_rowconfigure(0, weight=1)

            self.react_payload_frame = ctk.CTkScrollableFrame(self.react_payload_wrapper)
            self.react_payload_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=0)

            self.react_param_entries = []

            # Link class change to update type
            def _update_react_types(selected_cls):
                if selected_cls == "* ANY *":
                    combo_typ.configure(values=["* ANY *"])
                    combo_typ.set("* ANY *")
                else:
                    t_list = vscp.dictionary.class_types(selected_cls)
                    if t_list:
                        names = ["* ANY *"] + sorted([t['type'] for t in t_list])
                        combo_typ.configure(values=names)
                    else:
                        combo_typ.configure(values=["* ANY *"])
                    combo_typ.set("* ANY *")
                self._on_react_type_change(combo_typ.get())

            combo_cls.configure(command=_update_react_types)
            combo_typ.configure(command=self._on_react_type_change)
            self._current_react_update_func = _update_react_types # Save reference for Edit mode

            # Initial UI generation for "* ANY *"
            self._on_react_type_change("* ANY *")

        self._update_target_rx_combos()


    # --- Action Logic ---

    def _parse_int_input(self, val_str, placeholder="* ANY *"):
        """Helper to parse user input safely to int, handling dec and hex."""
        val_str = val_str.strip()
        if not val_str or val_str == placeholder:
            return None
        try:
            return int(val_str, 0)
        except ValueError:
            return None


    def _add_action(self): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """Extract data from UI and create a new action object."""
        # 1. Gather Target Event Data
        target_class = self.target_class_combo.get()
        target_type = self.target_type_combo.get()
        target_prio = self.target_prio_combo.get()
        target_node = self._parse_int_input(self.var_target_node.get(), "* DEFAULT *")

        if not target_class or target_type == "N/A":
            return

        # Parse user inputs based on parameter definition (Supports both Static & RX derived logic)
        raw_args = []
        for item in self.target_param_entries:
            mode = item['mode_var'].get()
            t_def = item['def']['type']

            if mode == "From RX":
                rx_opt = item['rx_combo'].get()
                rx_info = getattr(self, 'rx_param_map', {}).get(rx_opt, {'offset': 0, 'length': 1})
                offset_val = self._parse_int_input(item['offset_entry'].get(), "0") or 0

                raw_args.append({
                    'type': 'dynamic',
                    'rx_offset': rx_info['offset'],
                    'rx_length': rx_info['length'],
                    'val_offset': offset_val,
                    'rx_opt_name': rx_opt,
                    'target_type': t_def
                })
            else:
                val_str = item['static_entry'].get()
                # Simple conversion based on expected VSCP dictionary type
                if t_def in ('float', 'double'):
                    try:
                        raw_args.append(float(val_str) if val_str else 0.0)
                    except ValueError:
                        raw_args.append(0.0)
                elif t_def in ('ascii', 'utf8'):
                    raw_args.append(val_str)
                else: # assume int/hex/uint/raw/boolean
                    try:
                        raw_args.append(int(val_str, 0) if val_str else 0)
                    except ValueError:
                        raw_args.append(0)

        # 2. Gather Trigger Data
        mode = self.trigger_mode.get()
        trigger_cfg = {}

        if mode == "Periodic":
            try:
                interval = int(self.trigger_widgets['interval'].get())
                trigger_cfg['interval'] = max(100, interval) # Min 100ms
            except ValueError:
                trigger_cfg['interval'] = 1000

        elif mode == "Reactive":
            cls_val = self.trigger_widgets['class'].get()
            typ_val = self.trigger_widgets['type'].get()

            trigger_cfg['class'] = cls_val if cls_val != "* ANY *" else None
            trigger_cfg['type'] = typ_val if typ_val != "* ANY *" else None
            trigger_cfg['node'] = self._parse_int_input(self.trigger_widgets['node'].get())
            trigger_cfg['delay'] = self._parse_int_input(self.trigger_widgets['delay'].get(), "0") or 0 # pylint: disable=line-too-long

            # Dynamic payload matching configuration
            react_args = []
            payload_matchers = []
            if hasattr(self, 'react_param_entries'):
                for item in self.react_param_entries:
                    val_str = item['entry'].get()
                    react_args.append(val_str)

                    val = self._parse_int_input(val_str)
                    if val is not None:
                        payload_matchers.append({
                            'offset': item['offset'],
                            'length': item['def']['length'],
                            'value': val
                        })

            trigger_cfg['args'] = react_args
            trigger_cfg['payload_match'] = payload_matchers

        action = {
            'id': str(uuid.uuid4()),
            'target': {
                'nickname': target_node,
                'priority': target_prio,
                'class': target_class,
                'type': target_type,
                'args': raw_args
            },
            'trigger_type': mode,
            'trigger_cfg': trigger_cfg,
            'paused': False
        }

        self.actions.append(action)
        self._render_action_list()

        if mode == "Periodic":
            self._schedule_periodic(action['id'])


    def _edit_action(self, action_id): # pylint: disable=too-many-branches, too-many-statements
        """Loads action details back into the Builder and removes it from the list."""
        action = next((a for a in self.actions if a['id'] == action_id), None)
        if not action:
            return

        tgt = action['target']
        mode = action['trigger_type']
        cfg = action['trigger_cfg']

        def _restore_any(widget, val, placeholder="* ANY *"):
            widget.delete(0, 'end')
            widget.insert(0, f"0x{val:02X}" if val is not None else placeholder)

        # 1. Populate Trigger Settings FIRST so RX Combos resolve dynamically correctly
        self.trigger_mode.set(mode)
        self._on_trigger_mode_change(mode)

        if mode == "Periodic":
            self.trigger_widgets['interval'].delete(0, 'end')
            self.trigger_widgets['interval'].insert(0, str(cfg.get('interval', 1000)))
        elif mode == "Reactive":
            cls_val = cfg.get('class') or "* ANY *"
            self.trigger_widgets['class'].set(cls_val)
            if hasattr(self, '_current_react_update_func'):
                self._current_react_update_func(cls_val)

            type_val = cfg.get('type') or "* ANY *"
            self.trigger_widgets['type'].set(type_val)
            self._on_react_type_change(type_val)

            _restore_any(self.trigger_widgets['node'], cfg.get('node'))

            # Restore delay
            self.trigger_widgets['delay'].delete(0, 'end')
            self.trigger_widgets['delay'].insert(0, str(cfg.get('delay', 0)))

            # Restore dynamic payload parameters
            for i, arg in enumerate(cfg.get('args', [])):
                if i < len(self.react_param_entries):
                    entry = self.react_param_entries[i]['entry']
                    entry.delete(0, 'end')
                    entry.insert(0, arg)

        # 2. Populate Target Settings
        _restore_any(self.target_node_entry, tgt.get('nickname'), "* DEFAULT *")
        self.target_prio_combo.set(tgt['priority'])
        self.target_class_combo.set(tgt['class'])
        self._on_target_class_change(tgt['class'])
        self.target_type_combo.set(tgt['type'])
        self._on_target_type_change(tgt['type'])

        # Refill payload parameter entries & resolve modes (Static / Dynamic)
        for i, arg in enumerate(tgt['args']):
            if i < len(self.target_param_entries):
                item = self.target_param_entries[i]
                t_def = item['def']['type']

                if isinstance(arg, dict) and arg.get('type') == 'dynamic':
                    item['mode_var'].set("From RX")
                    item['static_entry'].pack_forget()
                    item['dyn_frame'].pack(fill="x", expand=True)

                    item['rx_combo'].set(arg.get('rx_opt_name', "Byte 0"))
                    item['offset_entry'].delete(0, 'end')
                    item['offset_entry'].insert(0, str(arg.get('val_offset', 0)))
                else:
                    item['mode_var'].set("Static")
                    item['dyn_frame'].pack_forget()
                    item['static_entry'].pack(fill="x", expand=True)

                    entry = item['static_entry']
                    entry.delete(0, 'end')
                    if 'int' in t_def and not ('float' in t_def or 'double' in t_def):
                        # Restore as hex visual format if it relies on hex, or pure integer
                        if 'hex' in t_def and not isinstance(arg, dict):
                            entry.insert(0, f"0x{int(arg):X}")
                        else:
                            entry.insert(0, str(arg))
                    else:
                        entry.insert(0, str(arg))

        # 3. Delete the old action from active list
        self._delete_action(action_id)


    def _execute_action(self, action_id, rx_data_bytes=None):
        """Generates raw payload and sends the VSCP event."""
        action = next((a for a in self.actions if a['id'] == action_id), None)
        if not action or action['paused']:
            return

        tgt = action['target']
        resolved_args = []

        for arg in tgt['args']:
            # Evaluate dynamically mapped RX arguments vs Static configs
            if isinstance(arg, dict) and arg.get('type') == 'dynamic':
                rx_val = 0
                if rx_data_bytes is not None:
                    rx_off = arg.get('rx_offset', 0)
                    rx_len = arg.get('rx_length', 1)
                    if len(rx_data_bytes) >= rx_off + rx_len:
                        val_bytes = bytes(rx_data_bytes[rx_off : rx_off + rx_len])
                        rx_val = int.from_bytes(val_bytes, 'big')

                final_val = rx_val + arg.get('val_offset', 0)
                t_def = arg.get('target_type', '')

                if 'float' in t_def or 'double' in t_def:
                    resolved_args.append(float(final_val))
                else:
                    # By standard ensure that base negative values don't break VSCP packing logic unless intended # pylint: disable=line-too-long
                    resolved_args.append(max(0, int(final_val)))
            else:
                resolved_args.append(arg)

        payload = vscp.dictionary.construct_data(tgt['class'], tgt['type'], *resolved_args)

        tgt_node = tgt.get('nickname')
        if tgt_node is not None:
            vscp.send_vscp_event(tgt['priority'], tgt['class'], tgt['type'], payload, nickname=tgt_node) # pylint: disable=line-too-long
        else:
            vscp.send_vscp_event(tgt['priority'], tgt['class'], tgt['type'], payload)


    def _schedule_periodic(self, action_id):
        """Self-rescheduling loop for periodic actions."""
        action = next((a for a in self.actions if a['id'] == action_id), None)
        # Stop loop if action deleted
        if not action:
            return

        # Execute if not paused
        if not action['paused']:
            self._execute_action(action_id)

        # Schedule next run
        interval = action['trigger_cfg'].get('interval', 1000)
        self.after(interval, lambda aid=action_id: self._schedule_periodic(aid))


    def process_incoming_message(self, values): # pylint: disable=too-many-locals, too-many-branches
        """
        Evaluate reactive actions against incoming messages.
        `values` is expected to be [timestamp, dir, id_hex, prio, class, type, data_str]
        """
        # We only care about RX messages (incoming)
        if len(values) < 7 or values[1] != 'RX':
            return

        msg_node = int(values[2], 16) if isinstance(values[2], str) else values[2]
        msg_class = values[4]
        msg_type = values[5]

        # Parse data bytes from string "0x01 0x02 ..."
        data_bytes = []
        if isinstance(values[6], str):
            try:
                data_bytes = [int(x, 16) for x in values[6].split() if x.startswith('0x')]
            except ValueError:
                pass

        for action in self.actions:
            if action['trigger_type'] != 'Reactive' or action['paused']:
                continue

            cfg = action['trigger_cfg']

            # Check Class
            if cfg['class'] is not None and cfg['class'] != msg_class:
                continue

            # Check Type
            if cfg['type'] is not None and cfg['type'] != msg_type:
                continue

            # Check Node
            if cfg['node'] is not None and cfg['node'] != msg_node:
                continue

            # Check Data Filters dynamically based on lengths and offsets
            match = True
            payload_matchers = cfg.get('payload_match', [])

            for m in payload_matchers:
                offset = m['offset']
                length = m['length']
                expected_val = m['value']

                # Verify message is long enough
                if len(data_bytes) < offset + length:
                    match = False
                    break

                # Extract bytes and convert to integer value for comparison
                val_bytes = bytes(data_bytes[offset : offset + length])
                val_int = int.from_bytes(val_bytes, 'big')

                if val_int != expected_val:
                    match = False
                    break

            if match:
                delay = cfg.get('delay', 0)
                if delay > 0:
                    self.after(delay, lambda aid=action['id'], db=data_bytes: self._execute_action(aid, rx_data_bytes=db)) # pylint: disable=line-too-long
                else:
                    self._execute_action(action['id'], rx_data_bytes=data_bytes)


    # --- Action List Management ---

    def _toggle_pause(self, action_id):
        action = next((a for a in self.actions if a['id'] == action_id), None)
        if action:
            action['paused'] = not action['paused']
            self._render_action_list()


    def _delete_action(self, action_id):
        self.actions = [a for a in self.actions if a['id'] != action_id]
        self._render_action_list()


    def _move_action(self, action_id, direction):
        idx = next((i for i, a in enumerate(self.actions) if a['id'] == action_id), None)
        if idx is None:
            return

        new_idx = idx + direction
        if 0 <= new_idx < len(self.actions):
            # Swap items
            self.actions[idx], self.actions[new_idx] = self.actions[new_idx], self.actions[idx]
            self._render_action_list()


    def _clear_all_actions(self):
        self.actions.clear()
        self._render_action_list()


    def _render_action_list(self): # pylint: disable=too-many-locals
        """Rebuild the active actions UI list."""
        for widget in self.scroll_actions.winfo_children():
            widget.destroy()

        if not self.actions:
            ctk.CTkLabel(self.scroll_actions, text="No active actions.", text_color="gray").pack(pady=20) # pylint: disable=line-too-long
            return

        for idx, action in enumerate(self.actions):
            frame = ctk.CTkFrame(self.scroll_actions, border_width=1)
            frame.pack(fill="x", pady=2, padx=2)
            frame.grid_columnconfigure(0, weight=1)

            # Description Text
            status = "[PAUSED] " if action['paused'] else ""

            tgt_node = action['target'].get('nickname')
            if tgt_node is not None:
                target_desc = f"SEND: {action['target']['class']} / {action['target']['type']} [Origin: 0x{tgt_node:02X}]" # pylint: disable=line-too-long
            else:
                target_desc = f"SEND: {action['target']['class']} / {action['target']['type']}"

            if action['trigger_type'] == 'Manual':
                trig_desc = "TRIGGER: Manual"
            elif action['trigger_type'] == 'Periodic':
                trig_desc = f"TRIGGER: Every {action['trigger_cfg']['interval']} ms"
            else:
                c = action['trigger_cfg']['class'] or 'ANY'
                t = action['trigger_cfg']['type'] or 'ANY'
                delay = action['trigger_cfg'].get('delay', 0)
                d_str = f" [Delay: {delay}ms]" if delay > 0 else ""
                trig_desc = f"TRIGGER: RX -> {c} / {t}{d_str}"

            lbl = ctk.CTkLabel(frame, text=f"{status}Action #{idx+1} | {trig_desc}\n{target_desc}", anchor="w", justify="left") # pylint: disable=line-too-long
            lbl.grid(row=0, column=0, rowspan=2, sticky="w", padx=10, pady=5)

            # Double-click text to edit without needing an explicit button
            lbl.bind("<Double-Button-1>", lambda e, aid=action['id']: self._edit_action(aid))
            ToolTip(lbl, "Double-click to Edit this action")

            # If paused, gray out text
            if action['paused']:
                lbl.configure(text_color="gray")

            # Buttons Container
            btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
            btn_frame.grid(row=0, column=1, rowspan=2, sticky="e", padx=5, pady=5)

            # Hierarchy Movement buttons
            # pylint: disable=line-too-long
            ctk.CTkButton(btn_frame, text="↑", width=30, command=lambda aid=action['id']: self._move_action(aid, -1), fg_color="#7F8C8D").pack(side="left", padx=2)
            ctk.CTkButton(btn_frame, text="↓", width=30, command=lambda aid=action['id']: self._move_action(aid, 1), fg_color="#7F8C8D").pack(side="left", padx=(2, 10))

            # Allow manual execute for testing any rule
            ctk.CTkButton(btn_frame, text="Execute", width=60, command=lambda aid=action['id']: self._execute_action(aid), fg_color="#2980B9").pack(side="left", padx=2)

            pause_txt = "Resume" if action['paused'] else "Pause"
            pause_col = "gray" if action['paused'] else "#D35400"
            ctk.CTkButton(btn_frame, text=pause_txt, width=60, command=lambda aid=action['id']: self._toggle_pause(aid), fg_color=pause_col).pack(side="left", padx=2)

            ctk.CTkButton(btn_frame, text="Del", width=40, command=lambda aid=action['id']: self._delete_action(aid), fg_color="#C0392B").pack(side="left", padx=2)
            # pylint: enable=line-too-long


    # --- File I/O ---

    def _save_actions(self):
        if not self.actions:
            return
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Save Actions") # pylint: disable=line-too-long
        if not filename:
            return
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.actions, f, indent=4)
        except Exception as e: # pylint: disable=broad-except
            print(f"Error saving actions: {e}")


    def _load_actions(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], title="Load Actions") # pylint: disable=line-too-long
        if not filename:
            return
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, list):
                # Assign new UUIDs to avoid conflicts and restart periodic loops safely
                for action in data:
                    action['id'] = str(uuid.uuid4())
                    self.actions.append(action)
                    if action['trigger_type'] == 'Periodic':
                        self._schedule_periodic(action['id'])

                self._render_action_list()
        except Exception as e: # pylint: disable=broad-except
            print(f"Error loading actions: {e}")
