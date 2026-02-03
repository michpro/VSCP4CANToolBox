"""
Node Configuration Module.

This module provides the `NodeConfiguration` class, which creates a separate window
(Toplevel) for configuring a specific VSCP node. It allows viewing module information,
register details in a treeview, and potentially modifying settings (currently primarily
viewing capabilities implemented).

@file node_config.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

# pylint: disable=line-too-long, too-many-ancestors


import os
import pprint # TODO remove
import customtkinter as ctk
import tk_async_execute as tae
import vscp
from gui.common import update_progress
from .treeview import CTkTreeview


def new_tag_config(self, tagName, **kwargs): # pylint: disable=invalid-name
    """
    Workaround wrapper for the internal Textbox tag_config method.

    Allows configuring tags in CTkTextbox, bypassing some limitations or
    parameter handling in customtkinter's wrapper.

    Args:
        self: The CTkTextbox instance.
        tagName (str): The name of the tag.
        **kwargs: Configuration options for the tag.

    Returns:
        The result of the underlying Tkinter text widget's tag_config call.
    """
    return self._textbox.tag_config(tagName, **kwargs) # pylint: disable=protected-access


# workaround for banning 'font' parameter in the 'tag_config' function
ctk.CTkTextbox.tag_config = new_tag_config


class NodeConfiguration: # pylint: disable=too-many-instance-attributes, too-few-public-methods
    """
    Manages the Node Configuration window.

    Displays a Toplevel window showing registers for a specific node ID and GUID.
    Includes an info panel with module details and a tabbed configuration panel
    (currently focused on registers).
    """

    def __init__(self, parent, node_id: int, guid: str):
        """
        Initializes the NodeConfiguration window.

        Sets up the window layout, panels (ConfigPanel, InfoPanel), and window
        properties like geometry and title. Loads module info using VSCP MDF utilities.

        Args:
            parent: The parent widget (Application instance).
            node_id (int): The nickname ID of the node to configure.
            guid (str): The GUID of the node as a string.
        """
        super().__init__()
        self.window = ctk.CTkToplevel(parent)
        self.width = 1050
        self.height = 650
        self.parent = parent
        self.node_id = node_id

        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icon_path = os.path.join(icon_dir, 'vscp_logo.ico')

        # Get application window geometry
        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (self.width / 2))
        y = int((0.95 * (app_window.winfo_rooty() + (app_window.winfo_height() / 2))) - (self.height / 2))

        self.window.title(f'VSCP ToolBox - Node 0x{self.node_id:02X} GUID: {guid} Configuration')
        self.window.geometry(f'{self.width}x{self.height}+{x}+{y}')
        self.window.minsize(width=self.width, height=self.height)
        self.window.maxsize(width=self.width, height=self.window.winfo_screenheight() - 80)
        self.window.resizable(width=False, height=True)
        self.window.protocol('WM_DELETE_WINDOW', self._window_exit)
        self.window.after(250, lambda: self.window.iconbitmap(icon_path)) # show icon workaround
        self.window.bind("<Configure>", lambda e: self._check_maximize())

        self.config_panel = ctk.CTkFrame(self.window, corner_radius=0)
        self.config_panel.pack(fill='both', expand=True)

        self.config = ConfigPanel(self.config_panel, self.node_id)

        self.info_panel = ctk.CTkFrame(self.config_panel, height=150)
        self.info_panel.pack(padx=5, pady=(0, 5), side='top', anchor='s', fill='both', expand=False)

        self.info = InfoPanel(self.info_panel)
        self.info.display({**vscp.mdf.get_module_info(), **vscp.mdf.get_boot_algorithm()})


    def bring_to_front(self):
        """
        Brings the configuration window to the front.

        Temporarily sets the 'topmost' attribute to force the window above others,
        then releases it. Used when re-opening an already existing config window.
        """
        self.window.attributes('-topmost', True)
        self.window.focus_force()
        self.window.after(800, lambda: self.window.attributes('-topmost', False))


    def _check_maximize(self):
        """
        Prevents the window from being maximized (zoomed).

        If the user attempts to maximize the window, this method forces it back
        to the 'normal' state to maintain the fixed layout dimensions.
        """
        if self.window.state() == 'zoomed':
            self.window.state('normal')


    def _window_exit(self):
        """
        Handles the window close event.

        Notifies the parent application to perform cleanup before closing.
        """
        self.parent.close_node_configuration()


class InfoPanel(ctk.CTkFrame):
    """
    Displays module information at the bottom of the config window.

    Shows details like Name, Model, Version, VSCP Level, etc., extracted from
    the Module Description File (MDF).
    """

    def __init__(self, parent):
        """
        Initializes the InfoPanel.

        Args:
            parent: The parent widget.
        """
        self.parent = parent
        super().__init__(self.parent)

        font = ctk.CTkFont(family='TkDefaultFont', size=15)
        bold_font = ctk.CTkFont(family='TkDefaultFont', size=15, weight='bold')
        self.module_info = ctk.CTkTextbox(self.parent, font=font, border_spacing=1, fg_color=self._fg_color) # type: ignore
        self.module_info.pack(padx=(5, 5), pady=(5, 5), side='top', anchor='nw', fill='both', expand=True)
        self.module_info.bind("<Button-1>", 'break') # type: ignore
        self.module_info.configure(state='disabled')
        self.module_info.tag_config('bold', font=bold_font)


    def display(self, data: dict) -> None:
        """
        Populates the text box with formatted module information.

        Iterates through defined keys, retrieving values from the provided data
        dictionary and inserting them into the text widget with styling.

        Args:
            data (dict): Dictionary containing module information.
        """
        self.module_info.configure(state='normal')
        self.module_info.delete('1.0', 'end')
        if 0 != len(data):
            keys = [{'name':        ['Name',                    'br',   None]},
                    {'model':       ['Model',                   'br',   None]},
                    {'version':     ['Version',                 'br',   None]},
                    {'level':       ['VSCP level',              '',     None]},
                    {'buffersize':  ['max VSCP event size',     '',     None]},
                    {'changed':     ['Date',                    'br',   None]},
                    {'algorithm':   ['Bootloader Algorithm',    '',     vscp.dictionary.convert_blalgo]},
                    {'blockcount':  ['Firmware memory blocks',  '',     None]},
                    {'blocksize':   ['Memory block size',       'br',   None]},
                    {'infourl':     ['Homepage',                'br',   None]},
                    {'description': ['Description',             'eof',  None]}]
            for key in keys:
                data_key = next(iter(key))
                val = data.get(data_key, None)
                if val is not None:
                    info = key[data_key][0] + ': '
                    self.module_info.insert('end', info, 'bold')
                    info = str(val) if key[data_key][2] is None else key[data_key][2]([int(val)], None)
                    info += ' '
                    if 'br' in key[data_key][1]:
                        info += os.linesep
                    elif 'eof' not in key[data_key][1]:
                        info += '| '
                    self.module_info.insert('end', info)
        self.module_info.configure(state='disabled')


class ConfigPanel(ctk.CTkFrame):
    """
    Main configuration panel containing tabs for different settings categories.

    Manages tabs like 'Registers', 'Remote Variables', 'Decision Matrix', etc.
    Currently, only the 'Registers' tab is fully initialized.
    """

    def __init__(self, parent, node_id: int):
        """
        Initializes the ConfigPanel.

        Sets up the Tabview and creates the RegisterTab. Adds placeholders for
        unimplemented tabs.

        Args:
            parent: The parent widget.
            node_id: The ID of the node being configured.
        """
        super().__init__(parent)
        self.node_id = node_id

        self.widget = ctk.CTkTabview(parent)
        self.widget.pack(padx=5, pady=(0, 5), fill='both', expand=True)

        self.tabs_names =['Registers', 'Remote Variables', 'Decision Matrix', 'Files']
        self.tabs = []
        labels = []
        for idx, tab in enumerate(self.tabs_names):
            self.tabs.append(self.widget.add(tab))
            if 0 < idx:
                labels.append(ctk.CTkLabel(self.widget.tab(tab), text='UNIMPLEMENTED',
                                           font=('TkDefaultFont', 22, 'bold'), pady=40).pack())
        self.widget.set(self.tabs_names[0])

        self.registers = RegistersTab(self.widget.tab(self.tabs_names[0]), self.node_id)


class RegistersTab(ctk.CTkFrame):
    """
    Tab for viewing and editing VSCP registers.

    Displays register data in a treeview and shows detailed information about
    the selected register in a side panel.
    """

    def __init__(self, parent, node_id: int):
        """
        Initializes the RegistersTab.

        Sets up the treeview columns and layout. Loads register definitions
        from the VSCP MDF and initiates the read of actual device values.

        Args:
            parent: The parent widget (tab).
            node_id: The ID of the node to read registers from.
        """
        self.parent = parent
        self.node_id = node_id
        self.registers = {}
        super().__init__(self.parent)

        self.widget = ctk.CTkFrame(parent, fg_color='transparent')
        self.widget.pack(padx=0, pady=0, side='top', anchor='nw', fill='both', expand=True)

        header = [('address', 'Page:Offset', 105, 105, 'center', 'center'),
                  ('access', 'Access', 45, 45, 'center', 'center'),
                  ('value', 'Value', 45, 45, 'center', 'center'),
                  ('toSync', 'To Sync', 45, 45, 'center', 'center'),
                  ('name', '  Name', 505, 505, 'w', 'w'),
                  ]
        self.registers = CTkTreeview(self.widget, header, xscroll=False)
        self.registers.pack(side='left', padx=0, pady=0, fill='both', expand=True)

        # Configure cell editing for the 'value' column
        self.registers.enable_cell_editing(columns=['value'],
                                           edit_callback=self._on_cell_edit,
                                           permission_callback=self._can_edit_cell)

        self.registers.treeview.bind('<<TreeviewSelect>>', self._update_registers_info)
        # self.registers.treeview.bind('<Double-Button-1>', self.item_deselect)
        # self.registers.treeview.bind('<Button-3>', lambda event: self._show_menu(event, self.dropdown))
        # self.registers.treeview.bind('<<TreeviewSelect>>', self._parse_msg_data)

        font = ctk.CTkFont(family='TkDefaultFont', size=15)
        bold_font = ctk.CTkFont(family='TkDefaultFont', size=15, weight='bold')
        self.registers_info = ctk.CTkTextbox(self.widget, font=font, width=250, border_spacing=1, fg_color=self._fg_color) # type: ignore
        self.registers_info.pack(padx=(5, 0), pady=0, side='right', anchor='ne', fill='y', expand=False)
        self.registers_info.bind("<Button-1>", 'break') # type: ignore
        self.registers_info.configure(state='disabled')
        self.registers_info.tag_config('bold', font=bold_font)

        # Start async read of real register values
        tae.async_execute(self._prepare_registers_data(), wait=False, visible=False, pop_up=False, callback=None, master=self)

        # pp = pprint.PrettyPrinter(indent=2, width=160) # TODO remove
        # pp.pprint(self.registers_data)


    def _insert_registers_data(self):
        """
        Populates the register treeview with data.

        Iterates through the register data structure (organized by page and register address)
        and inserts rows into the treeview. Displays address, access rights,
        current value, sync status, and name.
        """
        result = []
        for page, registers in self.registers_data.items():
            child = []
            for register, data in registers.items():
                row = {'text': f'0x{register:02X}',
                       'values': [data['access'], data['value'], data['to_sync'], data['name']]}
                child.append(row)
            text = f'Page {page:d}' if 0 <= page else 'Standard regs'
            entry = {'text': text, 'child': child}
            result.append(entry)
        if result:
            self.registers.insert_items(result) # type: ignore


    async def _prepare_registers_data(self): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Reads actual register values from the physical node.
        
        This method is run asynchronously. It first probes the node to ensure it exists.
        Then, it iterates through all registers defined in the MDF, reading them in chunks
        of maximum 4 registers to handle buffer limitations and non-contiguous addresses.
        Updated values are reflected in the UI.
        """
        update_progress(0.0)
        vscp.set_async_work(True)
        update_progress(0.05)

        self.registers_data = vscp.mdf.get_registers_info()
        self._insert_registers_data()

        progress = 0.1
        update_progress(progress)

        # 1. Check if node is online
        found_node = await vscp.probe_node(self.node_id)
        if found_node is not None:
            # 2. Iterate through pages and registers
            # Sort pages so Standard Registers (-1) come first
            sorted_pages = sorted(self.registers_data.keys())

            # Pre-calculate total chunks to determine progress step
            total_chunks = 0
            for page in sorted_pages:
                page_regs = self.registers_data[page]
                sorted_addresses = sorted(page_regs.keys())
                if not sorted_addresses:
                    continue

                # Logic to count chunks (must match generation logic below)
                current_chunk_count = 1
                current_reg = sorted_addresses[0]
                current_chunk_len = 1

                for addr in sorted_addresses[1:]:
                    if addr == current_reg + 1 and current_chunk_len < 4:
                        current_chunk_len += 1
                        current_reg = addr
                    else:
                        current_chunk_count += 1
                        current_reg = addr
                        current_chunk_len = 1
                total_chunks += current_chunk_count

            # Calculate step for remaining 0.9 progress
            step = 0.9 / total_chunks if total_chunks > 0 else 0

            for page in sorted_pages:
                page_regs = self.registers_data[page]
                sorted_addresses = sorted(page_regs.keys())
                if not sorted_addresses:
                    continue

                # Use page 0 for standard registers (which are internally -1)
                vscp_page = 0 if page < 0 else page

                # 3. Create chunks of max 4 sequential registers
                chunks = []
                current_chunk = [sorted_addresses[0]]

                for addr in sorted_addresses[1:]:
                    # If sequential and chunk size < 4, add to current chunk
                    if addr == current_chunk[-1] + 1 and len(current_chunk) < 4:
                        current_chunk.append(addr)
                    else:
                        # Start new chunk
                        chunks.append(current_chunk)
                        current_chunk = [addr]
                chunks.append(current_chunk)

                # 4. Read each chunk
                for chunk in chunks:
                    start_reg = chunk[0]
                    count = len(chunk)

                    # Read from device
                    values = await vscp.extended_page_read_register(self.node_id, vscp_page, start_reg, count)

                    if values:
                        # Update local data and UI
                        for idx, val in enumerate(values):
                            reg_addr = start_reg + idx
                            hex_value = f'0x{val:02X}'

                            # Update data source
                            if reg_addr in self.registers_data[page]:
                                self.registers_data[page][reg_addr]['value'] = hex_value

                            # Update UI
                            self._update_treeview_value(page, reg_addr, hex_value)

                    progress += step
                    update_progress(progress)

        vscp.set_async_work(False)
        update_progress(1.0)


    def _update_treeview_value(self, page, reg_addr, hex_value):
        """
        Updates a specific register value in the Treeview.

        Args:
            page (int): The register page.
            reg_addr (int): The register address.
            hex_value (str): The new value formatted as a hex string.
        """
        page_text = f'Page {page:d}' if page >= 0 else 'Standard regs'
        reg_text = f'0x{reg_addr:02X}'

        # Find the parent item (Page)
        for page_item in self.registers.treeview.get_children(): # type: ignore
            if self.registers.treeview.item(page_item, "text") == page_text: # type: ignore
                # Find the child item (Register)
                for reg_item in self.registers.treeview.get_children(page_item): # type: ignore
                    if self.registers.treeview.item(reg_item, "text") == reg_text: # type: ignore
                        # Update the 'value' column (column index 2 corresponds to 'value' key in set)
                        self.registers.treeview.set(reg_item, column='value', value=hex_value) # type: ignore
                        return


    def _can_edit_cell(self, _row_id, col_key, _current_value, row_data):
        """
        Callback to determine if a cell is editable.

        A cell is editable if it is in the 'value' column AND the 'access' column
        contains the character 'w'.

        Args:
            row_id (str): The ID of the row in the treeview.
            col_key (str): The key of the column being clicked.
            current_value (str): The current value in the cell.
            row_data (dict): Dictionary of all values in the row (keyed by column names).

        Returns:
            bool: True if editing is allowed, False otherwise.
        """
        if col_key == 'value':
            # Check access rights from row_data
            # row_data contains keys defined in header: 'address', 'access', 'value', 'toSync', 'name'
            access_rights = str(row_data.get('access', '')).lower()
            if 'w' in access_rights:
                return True
        return False


    def _on_cell_edit(self, row_id, _col_key, _old_val, _new_val, _row_data):
        """
        Callback executed after a cell has been edited.

        Updates the 'toSync' column to indicate that the value needs
        to be written to the device.

        Args:
            row_id (str): The ID of the edited row.
            col_key (str): The key of the edited column.
            old_val (any): The previous value.
            new_val (any): The new value set in the cell.
            row_data (dict): Dictionary of all values in the row.
        """
        # Change the sync symbol to 'sync_write' ('⬤')
        self.registers.treeview.set(row_id, column='toSync', value=vscp.mdf.sync_write) # type: ignore
        return True # TODO check if value is valid


    def _update_registers_info(self, _):
        """
        Updates the information textbox based on the selected register.

        Retrieves details for the selected item in the treeview and displays
        them in the side panel.

        Args:
            _: The event object (unused).
        """
        try:
            item = self.registers.treeview.focus() # type: ignore
            item_dict = self.registers.treeview.item(item) # type: ignore
            parent_id = self.registers.treeview.parent(item) # type: ignore
            self.registers_info.configure(state='normal')
            self.registers_info.delete("0.0", "end")
            if parent_id:
                parent_text = self.registers.treeview.item(parent_id, 'text') # type: ignore
                page = int(parent_text.split(' ')[1])
                register = int(item_dict['text'], 16)
                data = self.registers_data[page][register]

                self.registers_info.insert("end", data['name'] + "\n", 'bold')
                self.registers_info.insert("end", "\n")
                self.registers_info.insert("end", "Page:     " + str(page) + "\n")
                self.registers_info.insert("end", "Register: " + f"0x{register:02X} ({register})" + "\n")
                self.registers_info.insert("end", "Access:   " + data['access'] + "\n")
                self.registers_info.insert("end", "Value:    " + f"0x{data['value']:02X} ({data['value']})" + "\n")
                self.registers_info.insert("end", "\n")
                self.registers_info.insert("end", data['description'])

            self.registers_info.configure(state='disabled')
        except (ValueError, KeyError, IndexError):
            pass
