"""
Custom Treeview module.

Provides a wrapper around the Tkinter Treeview widget with custom styling and
CustomTkinter integration (scrollbars).
"""
# pylint: disable=line-too-long, too-many-ancestors, too-many-instance-attributes

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

    def __init__(self, master: any, header=None, items=[], xscroll=True, yscroll=True): # pylint: disable=dangerous-default-value, too-many-arguments
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
        super().__init__(self.parent)

        self.bg_color = self.parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkFrame']['fg_color'])
        self.text_color = self.parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkLabel']['text_color'])
        self.selected_color = self.parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkButton']['fg_color'])

        self.tree_style = ttk.Style(self)
        self.tree_style.theme_use('default')

        self.im_open = Image.open(ICON_PATH)
        self.im_close = self.im_open.rotate(90)
        self.im_empty = Image.new('RGBA', (15, 15), '#00000000')

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
                anchor = self.header[idx + 1][4]
                self.treeview.heading(column=f'{item}', text=f'{self.header[idx + 1][1]}', anchor=anchor)
                w = self.header[idx + 1][2]
                mw = self.header[idx + 1][3]
                anchor = self.header[idx + 1][5]
                self.treeview.column(column=f'{item}', width=w, minwidth=mw, stretch=False, anchor=anchor)
            self.treeview.heading(column='#0', text=f'{self.header[0][1]}', anchor=self.header[0][4])
            self.treeview.column(column='#0', width=self.header[0][2], minwidth=self.header[0][3], stretch=False, anchor=self.header[0][5])
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


    def delete_selected_items(self):
        """Remove currently selected items from the treeview."""
        selected_rows = self.treeview.selection()
        for row in selected_rows:
            self.treeview.delete(row)
