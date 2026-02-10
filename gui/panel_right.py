"""
Right panel module for the VSCP application.

This module handles the right-side panel of the GUI, which primarily consists
of the VSCP message logger (treeview) and the detailed event information display.

@file panel_right.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import os
import csv
from typing import Any, cast
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import vscp
from vscp import dictionary
from .treeview import CTkTreeview
from .common import add_event_info_handle, event_info_handle
from .popup import CTkFloatingWindow
from .message_filters import MessageFilters


class Messages(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    Widget displaying VSCP messages in a treeview.

    Provides a log view of incoming/outgoing messages with columns for timestamp,
    direction, node ID, priority, class, type, and data. Includes a context menu
    for clearing items or saving the log to a CSV file.
    """

    def __init__(self, parent):
        # pylint: disable=line-too-long
        """
        Initialize the Messages widget.

        Args:
            parent: The parent widget associated with this frame.
        """
        super().__init__(parent)

        # Header structure: (id, text, width, minwidth, anchor, cell_anchor)
        header = [('', '', 0, 0, 'center', 'w'),
                  ('timestamp', 'Time', 105, 105, 'center', 'w'),
                  ('dir', 'DIR', 25, 25, 'center', 'center'),
                  ('id', 'NodeID', 65, 65, 'center', 'center'),
                  ('priority', 'Priority', 80, 80, 'center', 'center'),
                  ('class', 'VSCP Class', 205, 205, 'center', 'w'),
                  ('type', 'VSCP Type', 290, 290, 'center', 'w'),
                  ('data', 'Data', 280, 280, 'center', 'w')
                 ]
        self.widget = ctk.CTkFrame(parent, fg_color='transparent')
        self.widget.pack(padx=(0, 4), pady=4, fill='both', expand=True)
        self.messages = CTkTreeview(self.widget, header, xscroll=False)
        self.messages.pack(padx=2, pady=2, fill='both', expand=True)
        self.messages.treeview.bind('<Double-Button-1>', self.item_deselect)
        self.messages.treeview.bind('<Button-3>', lambda event: self._show_menu(event, self.dropdown))
        self.messages.treeview.bind('<<TreeviewSelect>>', self._parse_msg_data)
        self.dropdown = CTkFloatingWindow(self.widget)
        self.dropdown_bt_clear_all = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                   text="Clear all items", command=self._clear_all_items)
        self.dropdown_bt_clear_all.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_clear_selected = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                        text="Clear selected items", command=self._clear_selected_items)
        self.dropdown_bt_clear_selected.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_save_log = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                  text="Save log to file", command=self._save_log)
        self.dropdown_bt_save_log.pack(expand=True, fill="x", padx=0, pady=0)
        vscp.add_node_id_observer(self.update_node_id)
        # pylint: enable=line-too-long


    def _parse_msg_data(self, _):
        """
        Callback triggered when a treeview row is selected.

        Extracts data from the selected row and sends it to the event info
        handler for decoding and display.
        """
        values = []
        selected_rows = self.messages.treeview.selection()
        if 1 == len(selected_rows):
            values = self.messages.treeview.item(selected_rows[0])['values']
        handle = event_info_handle()
        if hasattr(handle, 'display'):
            cast(Any, handle).display(values)


    def insert(self, row_data):
        """
        Insert new message rows into the treeview.

        Args:
            row_data: A list of values representing the message data to display.
        """
        self.messages.insert_items(row_data)


    def update_node_id(self, old_id, new_id):
        """
        Update the displayed NodeID in the message list.

        Args:
            old_id (int): The old Node ID.
            new_id (int): The new Node ID.
        """
        old_id_str = f"0x{old_id:02X}"
        new_id_str = f"0x{new_id:02X}"
        for item in self.messages.treeview.get_children():
            values = list(self.messages.treeview.item(item, 'values'))
            if len(values) > 2 and values[2] == old_id_str:
                values[2] = new_id_str
                self.messages.treeview.item(item, values=values)


    def item_deselect(self, event):
        """
        Handle double-click events to deselect a row.

        Args:
            event: The mouse event triggering the action.
        """
        selected_rows = self.messages.treeview.selection()
        row_clicked = self.messages.treeview.identify('row', event.x, event.y)
        index = selected_rows.index(row_clicked) if row_clicked in selected_rows else -1
        if -1 < index:
            self.messages.treeview.selection_remove(selected_rows[index])


    def _clear_all_items(self):
        """Clear all messages from the log."""
        self.messages.treeview.delete(*self.messages.treeview.get_children())


    def _clear_selected_items(self):
        """Delete only the currently selected messages from the log."""
        selected_rows = self.messages.treeview.selection()
        for row in selected_rows:
            self.messages.treeview.delete(row)


    def _save_log(self):
        """
        Open a save file dialog and export the current log to a CSV file.
        """
        filetypes = [('CSV Log File', '*.csv')]
        fname = ctk.filedialog.asksaveasfilename(confirmoverwrite=True, initialfile='vscp_log',
                                                 filetypes=filetypes, defaultextension='.csv')
        if fname:
            with open(fname, "w", newline='', encoding='UTF-8') as log_file:
                csvwriter = csv.writer(log_file, delimiter=',')
                for row_id in self.messages.treeview.get_children():
                    row = self.messages.treeview.item(row_id)['values']
                    csvwriter.writerow(row)
        else:
            CTkMessagebox(title='Error', message='No Log file name !!!', icon='cancel')


    def _show_menu(self, event, menu):
        """
        Display the context menu (Clear/Save) at the mouse position.

        Enables or disables menu items based on whether there are items
        in the list or items selected.

        Args:
            event: The mouse event.
            menu: The menu widget to display.
        """
        try:
            state = 'normal' if 0 != len(self.messages.treeview.get_children()) else 'disabled'
            self.dropdown_bt_clear_all.configure(state=state)
            self.dropdown_bt_save_log.configure(state=state)
            state = 'normal' if 0 != len(self.messages.treeview.selection()) else 'disabled'
            self.dropdown_bt_clear_selected.configure(state=state)
            menu.popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


class EventInfo(ctk.CTkFrame): # pylint: disable=too-few-public-methods, too-many-ancestors
    """
    Widget for displaying detailed information about a selected VSCP event.

    It parses raw event data using the VSCP dictionary and displays it in a
    text box.
    """

    def __init__(self, parent):
        # pylint: disable=line-too-long
        """
        Initialize the EventInfo widget.

        Args:
            parent: The parent widget associated with this frame.
        """
        self.parent = parent
        super().__init__(self.parent)

        font = ctk.CTkFont(family='Ubuntu Mono', size=16)
        temp_fg_color = tuple(self._fg_color) if isinstance(self._fg_color, list) else self._fg_color
        self.event_info_box = ctk.CTkTextbox(self.parent, font=font, border_spacing=1, width=480, fg_color=temp_fg_color)
        self.event_info_box.pack(padx=(5, 5), pady=(5, 5), side='top', anchor='nw', fill='both', expand=True)
        self.event_info_box.bind("<Button-1>", lambda e: 'break')
        self.event_info_box.configure(state='disabled')
        # pylint: enable=line-too-long


    def display(self, data: list) -> None:
        # pylint: disable=line-too-long
        """
        Decode and display the provided event data.

        Parses the Class, Type, and Data bytes to generate a human-readable
        description of the event.

        Args:
            data: A list containing raw message fields (timestamp, dir, id, priority, class, type, data).
        """
        # pylint: enable=line-too-long
        self.event_info_box.configure(state='normal')
        self.event_info_box.delete('1.0', 'end')
        if 0 != len(data):
            descr_len = 18
            class_id = dictionary.class_id(data[4])
            type_id = dictionary.type_id(class_id, data[5])
            dlc = [int(val, 0) for val in data[6].split()]
            info = dictionary.parse_data(class_id, type_id, dlc)
            val = ''
            for idx, item in enumerate(info):
                val += item[0].ljust(descr_len)[:descr_len] if 0 != idx else item[0] + (os.linesep * 2) # pylint: disable=line-too-long
                if 0 != idx:
                    val += item[1] + os.linesep
            self.event_info_box.insert('end', val)
        self.event_info_box.configure(state='disabled')


class RightPanel(ctk.CTkFrame): # pylint: disable=too-few-public-methods, too-many-ancestors
    """
    Main container for the right panel of the application.

    Holds the Messages widget (the log list), the EventInfo widget (the detail view),
    and the MessageFilters widget.
    """

    def __init__(self, parent):
        """
        Initialize the RightPanel.

        Args:
            parent: The parent widget associated with this frame.
        """
        self.parent = parent
        super().__init__(self.parent)

        self.widget = ctk.CTkFrame(self.parent, corner_radius=0)
        self.widget.pack(fill='both', expand=True)

        self.messages = Messages(self.widget)

        self.bottom_container = ctk.CTkFrame(self.widget, height=150, fg_color="transparent")
        self.bottom_container.pack_propagate(False)
        self.bottom_container.pack(side='top', fill='x', expand=False, padx=(2, 5), pady=(0, 10))

        self.info_panel = ctk.CTkFrame(self.bottom_container)
        self.info_panel.pack(side='left', fill='both', expand=True, padx=0)

        self.filter_panel = ctk.CTkFrame(self.bottom_container)
        self.filter_panel.pack(side='left', fill='both', expand=True, padx=(5, 0))

        self.info = EventInfo(self.info_panel)
        add_event_info_handle(self.info)

        # Initialize the filter configuration window (hidden by default)
        self.filters_window = MessageFilters(self, self.messages.messages)

        # pylint: disable=line-too-long
        ctk.CTkLabel(self.filter_panel, text="Filters:", anchor="w").pack(side="left", fill="x", padx=(15, 5), pady=5, anchor="n")
        ctk.CTkButton(self.filter_panel, text="Configure", width=120, command=self.filters_window.deiconify).pack(side="left", padx=0, pady=5, anchor="n")
        ctk.CTkButton(self.filter_panel, text="Apply", width=120, command=self.filters_window.apply_filter, fg_color="green").pack(side="left", padx=(3, 0), pady=5, anchor="n")
        ctk.CTkButton(self.filter_panel, text="Clear", width=120, command=self.filters_window.clear_filter, fg_color="gray").pack(side="left", padx=(3, 0), pady=5, anchor="n")
        ctk.CTkButton(self.filter_panel, text="Hide All", width=120, command=self.filters_window.block_all, fg_color="#C0392B").pack(side="left", padx=(3, 0), pady=5, anchor="n")
        # pylint: enable=line-too-long
