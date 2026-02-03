"""
Custom Treeview module.

Provides a wrapper around the Tkinter Treeview widget with custom styling and
CustomTkinter integration (scrollbars).

@file treeview.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""
# pylint: disable=line-too-long, too-many-ancestors, too-many-instance-attributes, too-many-positional-arguments

import os
import string
import random
from tkinter import ttk
import customtkinter as ctk
from PIL import Image, ImageTk

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
ICON_DIR = os.path.join(CURRENT_PATH, 'icons')
ICON_PATH = os.path.join(ICON_DIR, 'arrow.png')
# {
#     # 'close': (os.path.join(ICON_DIR, 'close_black.png'), os.path.join(ICON_DIR, 'close_white.png')),
#     # 'images': list(os.path.join(ICON_DIR, f'image{i}.jpg') for i in range(1, 4)),
#     # 'eye1': (os.path.join(ICON_DIR, 'eye1_black.png'), os.path.join(ICON_DIR, 'eye1_white.png')),
#     # 'eye2': (os.path.join(ICON_DIR, 'eye2_black.png'), os.path.join(ICON_DIR, 'eye2_white.png')),
#     # 'info': os.path.join(ICON_DIR, 'info.png'),
#     # 'warning': os.path.join(ICON_DIR, 'warning.png'),
#     # 'error': os.path.join(ICON_DIR, 'error.png'),
#     # 'left': os.path.join(ICON_DIR, 'left.png'),
#     # 'right': os.path.join(ICON_DIR, 'right.png'),
#     # 'warning2': os.path.join(ICON_DIR, 'warning2.png'),
#     # 'loader': os.path.join(ICON_DIR, 'loader.gif'),
#     # 'icon': os.path.join(ICON_DIR, 'icon.png'),
#     'arrow': os.path.join(ICON_DIR, 'arrow.png'),
#     # 'image': os.path.join(ICON_DIR, 'image.png'),
# }

class CTkTreeview(ctk.CTkFrame):
    """
    Custom Treeview widget with integrated scrollbars and custom styles.
    """

    def __init__(self, master: any, header=None, items=[], xscroll=True, yscroll=True): # type: ignore # pylint: disable=dangerous-default-value, too-many-arguments, too-many-statements
        """
        Initialize the CTkTreeview.

        Args:
            master: The parent widget.
            header: List of tuples defining columns (id, text, width, minwidth, anchor, cell_anchor).
            items: Initial list of items to insert.
            xscroll: Boolean to enable horizontal scrollbar.
            yscroll: Boolean to enable vertical scrollbar.
        """
        self.parent = master
        self.header = header
        self.items = items
        self.xscroll = xscroll
        self.yscroll = yscroll
        self.entry_popup = None
        self.editable_columns = None  # List of editable column keys
        self.edit_callback = None # Callback function for validation
        self.permission_callback = None # Callback function for edit permission
        self._hidden_items = [] # List to store hidden items: (item_id, parent_id, index)
        self._modified_cells = set() # Set to store (item_id, column_key) of modified cells
        super().__init__(self.parent)

        self.bg_color = self.parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkFrame']['fg_color'])
        self.text_color = self.parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkLabel']['text_color'])
        self.selected_color = self.parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkButton']['fg_color'])

        self.tree_style = ttk.Style(self)
        self.tree_style.theme_use('default')

        # Robust image loading: create transparent placeholder if file missing
        try:
            self.im_open = Image.open(ICON_PATH)
        except (FileNotFoundError, OSError):
            # Fallback: create a simple 15x15 transparent image or a colored square
            self.im_open = Image.new('RGBA', (15, 15), (0, 0, 0, 0)) # Transparent # type: ignore
            # Optional: Draw a simple shape if you want visibility without file
            # from PIL import ImageDraw
            # draw = ImageDraw.Draw(self.im_open)
            # draw.polygon([(0,0), (0,15), (15,7)], fill="gray")

        self.im_close = self.im_open.rotate(90)
        self.im_empty = Image.new('RGBA', (15, 15), '#00000000') # type: ignore

        self.img_open = ImageTk.PhotoImage(self.im_open, name='img_open', size=(15, 15))
        self.img_close = ImageTk.PhotoImage(self.im_close, name='img_close', size=(15, 15))
        self.img_empty = ImageTk.PhotoImage(self.im_empty, name='img_empty', size=(15, 15))

        self.element_name_random = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))
        self.element_name = 'Treeitem.' + self.element_name_random

        self.tree_style.element_create(self.element_name,
                                       'image', 'img_close', ('user1', '!user2', 'img_open'), ('user2', 'img_empty'),
                                       sticky='w', width=15, height=15)

        self.tree_style.layout('Treeview.Item',
                               [('Treeitem.padding',
                                 {'sticky': 'nsew',
                                  'children': [(self.element_name, {'side': 'left', 'sticky': 'nsew'}),
                                               ('Treeitem.image', {'side': 'left', 'sticky': 'nsew'}),
                                               ('Treeitem.focus',
                                                {'side': 'left',
                                                 'sticky': 'nsew',
                                                 'children': [
                                                     ('Treeitem.text', {'side': 'left', 'sticky': 'nsew'})]})]})]
                               )

        self.tree_style.configure('Treeview', background=self.bg_color, foreground=self.text_color,
                                  fieldbackground=self.bg_color,
                                  borderwidth=0, font=('', 10))
        self.tree_style.map('Treeview', background=[('selected', self.bg_color)],
                            foreground=[('selected', self.selected_color)])

        self.treeview = ttk.Treeview(self)
        self.treeview.pack(padx=5, pady=5, fill='both', expand=True)

        if self.yscroll is True:
            self.treeview_yscroll = ctk.CTkScrollbar(self.treeview, command=self.treeview.yview, width=16, bg_color=self.bg_color)
            self.treeview_yscroll.pack(side='right', fill='y')
            self.treeview.configure(yscrollcommand=self.treeview_yscroll.set)

        if self.xscroll is True:
            self.treeview_xscroll = ctk.CTkScrollbar(self.treeview, command=self.treeview.xview, height=16, bg_color=self.bg_color)
            self.treeview_xscroll.pack(side='bottom', fill='x')
            self.treeview.configure(xscrollcommand=self.treeview_xscroll.set)

        self.col_keys = self._get_header_keys(self.header)
        if self.col_keys is not None:
            self.treeview['columns'] = self.col_keys
            for idx, item in enumerate(self.treeview['columns']):
                anchor = self.header[idx + 1][4] # type: ignore
                self.treeview.heading(column=f'{item}', text=f'{self.header[idx + 1][1]}', anchor=anchor) # type: ignore
                w = self.header[idx + 1][2] # type: ignore
                mw = self.header[idx + 1][3] # type: ignore
                anchor = self.header[idx + 1][5] # type: ignore
                self.treeview.column(column=f'{item}', width=w, minwidth=mw, stretch=False, anchor=anchor)
            self.treeview.heading(column='#0', text=f'{self.header[0][1]}', anchor=self.header[0][4]) # type: ignore
            self.treeview.column(column='#0', width=self.header[0][2], minwidth=self.header[0][3], stretch=False, anchor=self.header[0][5]) # type: ignore
        self.insert_items(self.items)


    def _get_header_keys(self, items):
        """
        Extract column keys from the header definition.

        Args:
            items: Header definition list.

        Returns:
            list: List of column keys or None.
        """
        result = None
        if isinstance(items, list) and len(items) > 1:
            result = []
            for idx, item in enumerate(items):
                if isinstance(item, (tuple, list)):
                    if idx > 0:
                        result.append(item[0])
        return result


    def insert_items(self, items, parent=''):
        """
        Recursive method to insert items into the treeview.

        Args:
            items: List of dictionaries representing rows and children.
            parent: The parent item ID (default is root).
        """
        for item in items:
            if isinstance(item, dict):
                text = item['text'] if 'text' in item else ''
                values = item['values'] if 'values' in item else []
                row = self.treeview.insert(parent, 'end', text=text, values=values)
                if 'child' in item:
                    self.insert_items(item['child'], row)
                self.treeview.see(self.treeview.get_children()[-1])


    def delete_all_items(self):
        """Remove all items from the treeview."""
        self.treeview.delete(*self.treeview.get_children())
        self._hidden_items.clear()
        self._modified_cells.clear()


    def delete_selected_items(self):
        """Remove currently selected items from the treeview."""
        selected_rows = self.treeview.selection()
        for row in selected_rows:
            self.treeview.delete(row)
            # Remove from modified cells tracking if present
            self._modified_cells = {cell for cell in self._modified_cells if cell[0] != row}


    def set_item_style(self, item_id, bg_color=None, fg_color=None, font=None):
        """
        Set style for a specific row/item.

        Args:
            item_id: The ID of the item to style.
            bg_color: Background color (hex string or color name).
            fg_color: Text/Foreground color.
            font: Font tuple (name, size, weight).
        """
        tag_name = f"style_{item_id}"
        kw = {}
        if bg_color:
            kw['background'] = bg_color
        if fg_color:
            kw['foreground'] = fg_color
        if font:
            kw['font'] = font

        if kw:
            self.treeview.tag_configure(tag_name, **kw)
            # Apply tag to item (preserving existing tags if any)
            current_tags = list(self.treeview.item(item_id, "tags"))
            if tag_name not in current_tags:
                current_tags.append(tag_name)
                self.treeview.item(item_id, tags=current_tags)


    def enable_cell_editing(self, columns=None, edit_callback=None, permission_callback=None):
        """
        Enable editing of cells on double-click.

        Args:
            columns: A list of column keys (strings) allowed to be edited.
                     Use '#0' for the main tree column.
                     If None (default), all columns are editable.
            edit_callback: A function to be called on confirmation (validation).
                           Signature: callback(row_id, col_key, old_value, new_value, row_data)
                           Should return:
                             - True: accept change
                             - False: reject change
                             - string: accept change and replace with string value
            permission_callback: A function to be called before editing starts to check permission.
                                 Signature: callback(row_id, col_key, current_value, row_data)
                                 Should return:
                                   - True: Allow editing
                                   - False: Prevent editing
        """
        self.editable_columns = columns
        self.edit_callback = edit_callback
        self.permission_callback = permission_callback
        self.treeview.bind("<Double-Button-1>", self._on_double_click)


    def _get_row_data(self, row_id):
        """Helper to retrieve all data for a specific row ID as a dictionary."""
        row_values = self.treeview.item(row_id, "values")
        row_text = self.treeview.item(row_id, "text")
        row_data = {'#0': row_text}
        if self.col_keys:
            for i, key in enumerate(self.col_keys):
                if i < len(row_values):
                    row_data[key] = row_values[i]
                else:
                    row_data[key] = ""
        return row_data


    def _on_double_click(self, event): # pylint: disable=too-many-return-statements, too-many-branches, inconsistent-return-statements
        """Handle double-click to spawn entry widget."""
        region = self.treeview.identify("region", event.x, event.y)
        # Allow editing only in cells or the text part of the tree hierarchy
        if region not in ("cell", "tree"):
            return

        # If in 'tree' region (column #0), ensure we clicked the text, not the icon/arrow
        if region == "tree":
            elem = self.treeview.identify_element(event.x, event.y)
            if elem != "text":
                return

        column = self.treeview.identify_column(event.x)
        row_id = self.treeview.identify_row(event.y)

        if not row_id:
            return

        # Calculate column index and key
        if column == '#0':
            col_idx = -1
            current_key = '#0'
        else:
            col_idx = int(column[1:]) - 1
            if self.col_keys and col_idx < len(self.col_keys):
                current_key = self.col_keys[col_idx]
            else:
                current_key = None

        # Check if editing is restricted to specific columns
        if self.editable_columns is not None:
            if current_key not in self.editable_columns:
                return

        bbox = self.treeview.bbox(row_id, column)
        if not bbox:
            return

        if col_idx == -1:
            current_value = self.treeview.item(row_id, "text")
        else:
            values = self.treeview.item(row_id, "values")
            current_value = values[col_idx] if values else ""

        # Check permission callback if defined
        if self.permission_callback:
            row_data = self._get_row_data(row_id)
            if not self.permission_callback(row_id, current_key, str(current_value), row_data):
                return

        self.entry_popup = ctk.CTkEntry(
            self.treeview,
            width=bbox[2],
            height=bbox[3],
            fg_color=self.bg_color,
            bg_color=self.bg_color, # Explicitly matching parent bg to avoid artifacts
            text_color=self.text_color,
            corner_radius=5
        )
        self.entry_popup.place(x=bbox[0], y=bbox[1])
        self.entry_popup.insert(0, str(current_value))
        self.entry_popup.focus()
        # Bind events
        self.entry_popup.bind("<Return>", lambda e: self._on_edit_confirm(row_id, col_idx))
        self.entry_popup.bind("<FocusOut>", lambda e: self._on_edit_cancel())
        self.entry_popup.bind("<Escape>", lambda e: self._on_edit_cancel())

        return "break" # Prevent default double-click behavior (like expansion)


    def _on_edit_confirm(self, row_id, col_idx): # pylint: disable=too-many-branches
        """Save edited value back to treeview with optional validation."""
        new_value = self.entry_popup.get() # type: ignore

        # Determine current column key
        if col_idx == -1:
            col_key = '#0'
            old_value = self.treeview.item(row_id, "text")
        else:
            if self.col_keys and col_idx < len(self.col_keys):
                col_key = self.col_keys[col_idx]
            else:
                col_key = f'#{col_idx + 1}' # Fallback
            values = list(self.treeview.item(row_id, "values"))
            # Ensure values list is long enough
            while len(values) <= col_idx:
                values.append("")
            old_value = values[col_idx]

        # Prepare row_data for validator
        row_data = self._get_row_data(row_id)

        # Validation callback
        if self.edit_callback:
            result = self.edit_callback(row_id, col_key, old_value, new_value, row_data)

            if result is False:
                # Rejected
                self._on_edit_cancel()
                return
            if isinstance(result, str):
                # Accepted with modified value
                new_value = result
            # else: True -> accept as is

        # Apply change
        if col_idx == -1:
            self.treeview.item(row_id, text=new_value)
        else:
            values = list(self.treeview.item(row_id, "values"))
            while len(values) <= col_idx:
                values.append("")
            values[col_idx] = new_value
            self.treeview.item(row_id, values=values)

        # Track modification if value changed
        if str(new_value) != str(old_value):
            if col_key:
                self._modified_cells.add((row_id, col_key))

        self._on_edit_cancel()


    def _on_edit_cancel(self):
        """Destroy entry widget."""
        if self.entry_popup:
            self.entry_popup.destroy()
            self.entry_popup = None


    def filter_view(self, condition_func):
        """
        Apply a filter to the treeview items.

        Rows that do not satisfy the condition_func will be hidden (detached).
        This method first restores all previously hidden items to ensure
        the filter is applied to the full dataset.

        Args:
            condition_func: A function that takes (text, values) and returns bool.
                            True = Show row, False = Hide row.
        """
        # First, ensure we work on the full dataset
        self.clear_filters()

        # Retrieve all items recursively to check against the filter
        # We need to collect IDs first, then process, to avoid issues while modifying the tree
        def get_all_items(parent=""):
            items = []
            children = self.treeview.get_children(parent)
            for child in children:
                items.append(child)
                items.extend(get_all_items(child))
            return items

        all_items = get_all_items()
        items_to_hide = []

        for item_id in all_items:
            values = self.treeview.item(item_id, "values")
            text = self.treeview.item(item_id, "text")

            if not condition_func(text, values):
                # Store necessary info to restore later
                parent = self.treeview.parent(item_id)
                index = self.treeview.index(item_id)
                items_to_hide.append((item_id, parent, index))

        # Detach items (hide them)
        for item_data in items_to_hide:
            item_id = item_data[0]
            # Verify item still exists (wasn't detached as part of a parent detach)
            if self.treeview.exists(item_id):
                self.treeview.detach(item_id)
                self._hidden_items.append(item_data)


    def clear_filters(self):
        """
        Clear active filters and restore all hidden items.
        """
        if not self._hidden_items:
            return

        # Sort hidden items by index to attempt maintaining relative order upon restoration
        # Sorting by index helps when restoring multiple items to the same parent
        self._hidden_items.sort(key=lambda x: x[2])

        for item_id, parent, index in self._hidden_items:
            if self.treeview.exists(item_id):
                try:
                    # 'parent' might store an ID. If parent was also hidden and not yet restored,
                    # this might fail or attach to root. However, since we iterate strictly,
                    # we rely on the user/logic ensuring hierarchy integrity or we just re-attach.
                    # If the parent is detached, we can't attach to it easily until it's back.
                    # But since we detached strictly based on the filter, if parent matched filter, it's there.
                    # If parent didn't match, it's in the list too.
                    # Simple restore:
                    if not self.treeview.exists(parent) and parent != '':
                        # If parent is gone (shouldn't happen if we manage list correctly), attach to root?
                        # Or skip? For now, standard attempt.
                        pass
                    self.treeview.move(item_id, parent, index)
                except: # pylint: disable=bare-except
                    pass

        self._hidden_items.clear()


    def get_modified_cells(self):
        """
        Get a list of cells modified by the user.

        Returns:
            list: A list of tuples (row_id, column_key) indicating modified cells.
        """
        return list(self._modified_cells)


    def clear_modified_cells(self):
        """
        Clear the list of modified cells.
        Typically called after synchronizing data with an external source.
        """
        self._modified_cells.clear()


    def is_cell_modified(self, row_id, col_key):
        """
        Check if a specific cell has been modified.

        Args:
            row_id: The ID of the row.
            col_key: The key of the column.

        Returns:
            bool: True if modified, False otherwise.
        """
        return (row_id, col_key) in self._modified_cells
