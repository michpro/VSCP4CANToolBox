"""
VSCP Message Filtering Module.

This module provides a UI window for configuring and applying filters to the
VSCP message list (treeview). It allows complex filtering where multiple rules
can be defined. Each rule defines a set of conditions (NodeID, Priority, Class, Type)
combined with AND logic. Different rules are combined with OR logic.

@file message_filters.py
@copyright SPDX-FileCopyrightText: Copyright 2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import os
import json
from tkinter import filedialog
import customtkinter as ctk
import vscp
from .tooltip import ToolTip


class MessageFilters(ctk.CTkToplevel): # pylint: disable=too-many-instance-attributes
    """
    Control window for configuring VSCP message filters.
    
    This class creates a floating window that allows building a list of filtering rules.
    Logic: Message is accepted if it matches Rule 1 OR Rule 2 OR ...
    Rule Logic: NodeID match AND Priority match AND Class match AND Type match.
    """

    def __init__(self, parent, treeview_widget): # pylint: disable=too-many-statements
        # pylint: disable=line-too-long
        """
        Initialize the filter configuration window.

        Args:
            parent: The parent widget (master).
            treeview_widget: The CTkTreeview object to apply filters to.
        """
        super().__init__(parent)
        self.treeview = treeview_widget

        # Window setup
        self.title("Filter Configuration")
        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icon_path = os.path.join(icon_dir, 'vscp_logo.ico')
        self.after(250, lambda: self.iconbitmap(icon_path))

        width = 1000
        height = 656

        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (width / 2))
        y = int(app_window.winfo_rooty() + (app_window.winfo_height() / 2) - (height / 2))

        self.geometry(f'{width}x{height}+{x}+{y}')
        self.resizable(False, False)

        # Hide window on close instead of destroying
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        self.withdraw() # Start hidden

        # Store active Rules.
        # Structure: list of dictionaries:
        # {
        #   'nodes': set of "0xXX" strings or None (for All),
        #   'priorities': set of priority name strings,
        #   'class': class name string or None (for All),
        #   'types': set of type name strings (empty set means All for that class)
        # }
        self.active_rules = []

        # --- Layout Configuration ---
        self.grid_columnconfigure(0, weight=0) # Left panel
        self.grid_columnconfigure(1, weight=1) # Right panel
        self.grid_rowconfigure(0, weight=1)    # Full height

        # --- Main Frame: Rule Builder (Left Panel) ---
        self.frame_builder = ctk.CTkFrame(self, width=470)
        self.frame_builder.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.frame_builder.grid_columnconfigure(1, weight=1)
        # Make the types list expand to fill vertical space
        self.frame_builder.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(self.frame_builder, text="Rule Builder", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(5, 5))

        # 1. Node ID Input
        ctk.CTkLabel(self.frame_builder, text="Node IDs:", anchor="w").grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")
        self.entry_node_id = ctk.CTkEntry(self.frame_builder, placeholder_text="e.g. 1, 0xFF, 5-10 (Leave empty for All)")
        self.entry_node_id.grid(row=1, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")
        ToolTip(self.entry_node_id, "List of Node IDs or ranges (e.g. 1, 0xFF, 5-10).\nLeave empty to match ANY Node ID.")

        # 2. Priority Selection
        ctk.CTkLabel(self.frame_builder, text="Priorities:", anchor="w").grid(row=2, column=0, padx=10, pady=(0, 5), sticky="nw")
        self.frame_prio_checks = ctk.CTkFrame(self.frame_builder, fg_color="transparent")
        self.frame_prio_checks.grid(row=2, column=1, padx=(0, 10), pady=(0, 5), sticky="w")

        self.priority_vars = []
        for i in range(8):
            var = ctk.IntVar(value=1) # Default checked
            self.priority_vars.append(var)
            chk = ctk.CTkCheckBox(self.frame_prio_checks, text=str(i), variable=var, width=30, height=20, border_width=2)
            chk.pack(side="left", padx=(0, 10))
            # Add tooltip
            ToolTip(chk, vscp.dictionary.priority_name(i))

        # 3. Class Selection
        ctk.CTkLabel(self.frame_builder, text="VSCP Class:", anchor="w").grid(row=3, column=0, padx=10, pady=(0, 5), sticky="w")

        self.any_class_label = "* Any Class *"
        self.all_classes = [self.any_class_label] + sorted([f"{c['class']}" for c in vscp.dictionary.get()])
        self.combo_class = ctk.CTkComboBox(self.frame_builder, values=self.all_classes, command=self._on_class_change)
        self.combo_class.grid(row=3, column=1, padx=(0, 10), pady=(0, 5), sticky="ew")
        self.combo_class.set(self.any_class_label)

        # 4. Type Selection
        ctk.CTkLabel(self.frame_builder, text="VSCP Types:", anchor="w").grid(row=4, column=0, padx=10, pady=5, sticky="nw")
        self.scroll_types = ctk.CTkScrollableFrame(self.frame_builder, label_text="Select specific types (or none for All)")
        self.scroll_types.grid(row=4, column=1, padx=(0, 10), pady=5, sticky="nsew")

        self.type_checkboxes = {} # name -> IntVar

        # 5. Add Button
        self.btn_add_rule = ctk.CTkButton(self.frame_builder, text="Add Rule to List", command=self._add_rule, fg_color="green")
        self.btn_add_rule.grid(row=5, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- Section: Active Rules List (Right Panel) ---
        self.frame_list = ctk.CTkFrame(self)
        self.frame_list.grid(row=0, column=1, sticky="nsew", padx=(0, 5), pady=5)
        self.frame_list.grid_rowconfigure(1, weight=1)
        self.frame_list.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_list, text="Active Filter Rules (OR logic)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, pady=(5, 5))

        self.txt_rules = ctk.CTkTextbox(self.frame_list, state="disabled", border_width=1)
        self.txt_rules.grid(row=1, column=0, sticky="nsew", pady=(0, 5), padx=10)

        # Control buttons container (Delete specific / Clear all)
        self.frame_list_ctrl = ctk.CTkFrame(self.frame_list, fg_color="transparent")
        self.frame_list_ctrl.grid(row=2, column=0, sticky="ew", pady=(0, 5), padx=10)

        # Delete specific rule inputs
        ctk.CTkLabel(self.frame_list_ctrl, text="Del Rule #:").pack(side="left", padx=(0, 5))
        self.entry_del_rule = ctk.CTkEntry(self.frame_list_ctrl, width=40)
        self.entry_del_rule.pack(side="left", padx=(0, 5))
        ToolTip(self.entry_del_rule, "Enter the Rule # to delete")

        self.btn_del_rule = ctk.CTkButton(self.frame_list_ctrl, text="Delete", command=self._delete_rule, width=60, fg_color="#C0392B", height=24)
        self.btn_del_rule.pack(side="left")

        self.btn_clear_rules = ctk.CTkButton(self.frame_list_ctrl, text="Clear All Rules", command=self._reset_rules, fg_color="gray", height=24)
        self.btn_clear_rules.pack(side="right")

        # File Operations (Load / Save)
        self.frame_file_ops = ctk.CTkFrame(self.frame_list, fg_color="transparent")
        self.frame_file_ops.grid(row=3, column=0, sticky="ew", pady=(0, 10), padx=10)

        self.btn_load = ctk.CTkButton(self.frame_file_ops, text="Load Rule(s)", command=self._load_rules_from_file, height=28)
        self.btn_load.pack(side="left", expand=True, padx=(0, 5), fill="x")

        self.btn_save = ctk.CTkButton(self.frame_file_ops, text="Save Rule(s)", command=self._save_rules_to_file, height=28)
        self.btn_save.pack(side="left", expand=True, padx=(5, 0), fill="x")
        # pylint: enable=line-too-long


    def _on_class_change(self, selected_class):
        """Update the types checkboxes based on selected class."""
        # Clear existing checkboxes
        for widget in self.scroll_types.winfo_children():
            widget.destroy()
        self.type_checkboxes.clear()

        if selected_class == self.any_class_label:
            lbl = ctk.CTkLabel(self.scroll_types, text="(Select a specific class to filter by types)", text_color="gray") # pylint: disable=line-too-long
            lbl.pack(pady=10)
            return

        types_list = vscp.dictionary.class_types(selected_class)
        if not types_list:
            lbl = ctk.CTkLabel(self.scroll_types, text="(No types defined for this class)", text_color="gray")# pylint: disable=line-too-long
            lbl.pack(pady=10)
            return

        # Add explicit checkboxes for types
        sorted_types = sorted([t['type'] for t in types_list])

        for t_name in sorted_types:
            var = ctk.IntVar(value=0)
            self.type_checkboxes[t_name] = var
            chk = ctk.CTkCheckBox(self.scroll_types, text=t_name, variable=var, border_width=2)
            chk.pack(anchor="w", pady=(0, 1))


    def _parse_node_ids(self, text):
        """
        Parse text input into set of hex strings '0xXX'.
        Supports single values and ranges (e.g. '1-5', '0x10-0x20').
        """
        if not text.strip():
            return None # All nodes

        ids = set()
        # Split by comma or space to separate entries
        parts = text.replace(',', ' ').split()

        for part in parts:
            if '-' in part:
                # Handle range: start-end
                try:
                    start_str, end_str = part.split('-', 1)
                    # int(x, 0) handles both '10' and '0x0A'
                    start = int(start_str, 0)
                    end = int(end_str, 0)

                    if start > end:
                        start, end = end, start

                    for val in range(start, end + 1):
                        if 0 <= val <= 255:
                            ids.add(f"0x{val:02X}")
                except ValueError:
                    pass # Ignore invalid ranges
            else:
                # Handle single value
                try:
                    val = int(part, 0)
                    if 0 <= val <= 255:
                        ids.add(f"0x{val:02X}")
                except ValueError:
                    pass

        return ids


    def _add_rule(self):
        """Build rule from UI and add to list."""
        # 1. Node IDs
        nodes = self._parse_node_ids(self.entry_node_id.get())

        # 2. Priorities
        selected_priorities = set()
        for i, var in enumerate(self.priority_vars):
            if var.get() == 1:
                selected_priorities.add(vscp.dictionary.priority_name(i))

        # 3. Class
        cls_name = self.combo_class.get()
        if cls_name == self.any_class_label:
            cls_name = None

        # 4. Types (only if class is selected)
        selected_types = set()
        if cls_name:
            selected_types = {name for name, var in self.type_checkboxes.items() if var.get() == 1}

        # Create Rule Object
        rule = {
            'nodes': nodes,
            'priorities': selected_priorities,
            'class': cls_name,
            'types': selected_types
        }

        self.active_rules.append(rule)
        self._update_rules_display()


    def _delete_rule(self):
        """Remove a specific rule by index."""
        try:
            txt = self.entry_del_rule.get().strip()
            if not txt:
                return
            idx = int(txt)
            if 1 <= idx <= len(self.active_rules):
                self.active_rules.pop(idx - 1)
                self._update_rules_display()
                self.entry_del_rule.delete(0, 'end')
        except ValueError:
            pass


    def _reset_rules(self):
        """Clear all active rules."""
        self.active_rules.clear()
        self._update_rules_display()


    def _update_rules_display(self):
        """Render active rules to the textbox."""
        self.txt_rules.configure(state="normal")
        self.txt_rules.delete("1.0", "end")

        if not self.active_rules:
            self.txt_rules.insert("end", "No active rules. (All messages allowed)\nAdd a rule above to start filtering.") # pylint: disable=line-too-long
        else:
            for i, rule in enumerate(self.active_rules):
                self.txt_rules.insert("end", f"RULE #{i+1}:\n")

                # Nodes
                nodes_str = ", ".join(sorted(list(rule['nodes']))) if rule['nodes'] else "ALL"
                self.txt_rules.insert("end", f"  • Nodes: {nodes_str}\n")

                # Priorities
                if len(rule['priorities']) == 8:
                    prio_str = "ALL"
                else:
                    prio_str = f"Selected ({len(rule['priorities'])})"
                self.txt_rules.insert("end", f"  • Priorities: {prio_str}\n")

                # Class/Types
                if rule['class']:
                    self.txt_rules.insert("end", f"  • Class: {rule['class']}\n")
                    types_str = ", ".join(sorted(list(rule['types']))) if rule['types'] else "ALL TYPES" # pylint: disable=line-too-long
                    self.txt_rules.insert("end", f"  • Types: {types_str}\n")
                else:
                    self.txt_rules.insert("end", "  • Class: ALL\n")

                self.txt_rules.insert("end", "-"*40 + "\n")

        self.txt_rules.configure(state="disabled")


    def _save_rules_to_file(self):
        """Save active rules to a JSON file."""
        if not self.active_rules:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save Filter Rules"
        )
        if not filename:
            return

        # Convert sets to lists for JSON serialization
        serializable_rules = []
        for rule in self.active_rules:
            serializable_rules.append({
                'nodes': list(rule['nodes']) if rule['nodes'] else None,
                'priorities': list(rule['priorities']),
                'class': rule['class'],
                'types': list(rule['types'])
            })

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_rules, f, indent=4)
        except Exception as e: # pylint: disable=broad-except
            print(f"Error saving rules: {e}")


    def _load_rules_from_file(self):
        """Load rules from a JSON file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Filter Rules"
        )
        if not filename:
            return

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                print("Invalid rule file format")
                return

            loaded_rules = []
            for item in data:
                # Convert lists back to sets
                rule = {
                    'nodes': set(item['nodes']) if item.get('nodes') else None,
                    'priorities': set(item.get('priorities', [])),
                    'class': item.get('class'),
                    'types': set(item.get('types', []))
                }
                loaded_rules.append(rule)

            self.active_rules = loaded_rules
            self._update_rules_display()

        except Exception as e: # pylint: disable=broad-except
            print(f"Error loading rules: {e}")


    def apply_filter(self):
        """
        Compile and apply the filter lambda based on active rules.
        """
        # Capture current rules in local scope
        rules = list(self.active_rules)

        def condition(_text, values):
            """
            Filter condition callback.
            values indices: 2=NodeID, 3=Priority, 4=Class, 5=Type
            Logic: Return True if message matches AT LEAST ONE rule.
            """
            if not rules:
                return True # No rules = allow everything

            msg_node = values[2]
            msg_prio = values[3]
            msg_class = values[4]
            msg_type = values[5]

            for rule in rules:
                # 1. Check Node ID
                if rule['nodes'] is not None:
                    if msg_node not in rule['nodes']:
                        continue # Rule mismatch, try next rule

                # 2. Check Priority
                if msg_prio not in rule['priorities']:
                    continue

                # 3. Check Class
                if rule['class'] is not None:
                    if msg_class != rule['class']:
                        continue

                    # 4. Check Type (Only if class matches)
                    if rule['types']: # If set is not empty, we require a match
                        if msg_type not in rule['types']:
                            continue

                # If we reached here, the message satisfies ALL conditions of this rule
                return True

            # Message did not match any rule
            return False

        self.treeview.filter_view(condition)


    def clear_filter(self):
        """
        Remove the filter from the treeview to show all messages.
        Does NOT clear the defined rules or UI state, allowing re-enable them.
        """
        self.treeview.clear_filters()


    def block_all(self):
        """
        Block all messages in the treeview.
        Does NOT clear the defined rules or UI state, allowing restore the previous filter.
        """
        self.treeview.filter_view(lambda t, v: False)
