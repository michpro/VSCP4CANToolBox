# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# pylint: disable=line-too-long, too-many-ancestors

import os
import csv
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from vscp import dictionary
from .treeview import CTkTreeview
from .common import add_event_info_handle, event_info_handle
from .popup import CTkFloatingWindow


class Messages(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

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


    def _parse_msg_data(self, _):
        values = []
        selected_rows = self.messages.treeview.selection()
        if 1 == len(selected_rows):
            values = self.messages.treeview.item(selected_rows[0])['values']
        event_info_handle().display(values)


    def insert(self, row_data):
        self.messages.insert_items(row_data)


    def item_deselect(self, event):
        selected_rows = self.messages.treeview.selection()
        row_clicked = self.messages.treeview.identify('row', event.x, event.y)
        index = selected_rows.index(row_clicked) if row_clicked in selected_rows else -1
        if -1 < index:
            self.messages.treeview.selection_remove(selected_rows[index])


    def _clear_all_items(self):
        self.messages.treeview.delete(*self.messages.treeview.get_children())


    def _clear_selected_items(self):
        selected_rows = self.messages.treeview.selection()
        for row in selected_rows:
            self.messages.treeview.delete(row)


    def _save_log(self):
        filetypes = [('CSV Log File', '*.csv')]
        fname = ctk.filedialog.asksaveasfilename(confirmoverwrite=True, initialfile='vscp_log',
                                                 filetypes=filetypes, defaultextension=filetypes)
        if fname:
            with open(fname, "w", newline='', encoding='UTF-8') as log_file:
                csvwriter = csv.writer(log_file, delimiter=',')
                for row_id in self.messages.treeview.get_children():
                    row = self.messages.treeview.item(row_id)['values']
                    csvwriter.writerow(row)
        else:
            CTkMessagebox(title='Error', message='No Log file name !!!', icon='cancel')


    def _show_menu(self, event, menu):
        try:
            state = 'normal' if 0 != len(self.messages.treeview.get_children()) else 'disabled'
            self.dropdown_bt_clear_all.configure(state=state)
            self.dropdown_bt_save_log.configure(state=state)
            state = 'normal' if 0 != len(self.messages.treeview.selection()) else 'disabled'
            self.dropdown_bt_clear_selected.configure(state=state)
            menu.popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


class EventInfo(ctk.CTkFrame): # pylint: disable=too-few-public-methods
    def __init__(self, parent):
        self.parent = parent
        super().__init__(self.parent)

        font = ctk.CTkFont(family='Ubuntu Mono', size=16)
        self.event_info = ctk.CTkTextbox(self.parent, font=font, border_spacing=1, width=480, fg_color=self._fg_color)
        self.event_info.pack(padx=(5, 0), pady=(5, 5), side='top', anchor='nw', fill='y', expand=False)
        self.event_info.bind("<Button-1>", 'break')
        self.event_info.configure(state='disabled')


    def display(self, data: list) -> None:
        self.event_info.configure(state='normal')
        self.event_info.delete('1.0', 'end')
        if 0 != len(data):
            descr_len = 18
            class_id = dictionary.class_id(data[4])
            type_id = dictionary.type_id(class_id, data[5])
            dlc = [int(val, 0) for val in data[6].split()]
            info = dictionary.parse_data(class_id, type_id, dlc)
            val = ''
            for idx, item in enumerate(info):
                val += item[0].ljust(descr_len)[:descr_len] if 0 != idx else item[0] + (os.linesep * 2)
                if 0 != idx:
                    val += item[1] + os.linesep
            self.event_info.insert('end', val)
        self.event_info.configure(state='disabled')


class RightPanel(ctk.CTkFrame): # pylint: disable=too-few-public-methods
    def __init__(self, parent):
        self.parent = parent
        super().__init__(self.parent)

        self.widget = ctk.CTkFrame(self.parent, corner_radius=0)
        self.widget.pack(fill='both', expand=True)

        self.messages = Messages(self.widget)

        self.info_panel = ctk.CTkFrame(self.widget, height=150)
        self.info_panel.pack(padx=(2, 6), pady=(1, 5), side='top', anchor='s', fill='both', expand=False)

        self.info = EventInfo(self.info_panel)
        add_event_info_handle(self.info)
