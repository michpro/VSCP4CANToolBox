"""
Left panel module for the VSCP application.

This module handles the left-side panel of the GUI, including the neighbourhood
scanning functionality, node listing, and general node management actions like
firmware upload and configuration.

@file panel_left.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""
# pylint: disable=too-many-ancestors, line-too-long

import os
import re
from pathlib import Path
import requests
import tk_async_execute as tae
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from intelhex import IntelHex
import vscp
from .treeview import CTkTreeview
from .common import add_set_state_callback, call_set_scan_widget_state,     \
                    add_neighbours_handle, neighbours_handle
from .popup import CTkFloatingWindow
from .node_config import NodeConfiguration


class LeftPanel(ctk.CTkFrame):
    """
    Main container for the left panel of the application.

    Holds the Neighbourhood widget and general command buttons (e.g., Send Host DateTime).
    """

    def __init__(self, parent):
        """
        Initialize the LeftPanel.

        Args:
            parent: The parent widget associated with this frame.
        """
        self.parent = parent
        super().__init__(self.parent)

        self.widget = ctk.CTkFrame(parent, corner_radius=0, width=468)
        self.widget.pack(side='left', anchor='nw', fill='y', expand=False)
        self.widget.pack_propagate(False)

        self.neighbourhood = Neighbourhood(self.widget)

        self.button = ctk.CTkButton(self.widget, text='Send Host DateTime',
                                    width=100, height=28, command=self.button_cb)
        self.button.pack(padx=5, pady=(5, 10), fill='x')

        # self.button1 = ctk.CTkButton(self.widget, text='test', width=100, height=28,
        #                             command=self.button1_cb)
        # self.button1.pack(padx=5, pady=(0, 10), fill='x')


    def button_cb(self):
        """Callback for the 'Send Host DateTime' button."""
        tae.async_execute(vscp.send_host_datetime(), visible=False)


    def button1_cb(self): # TODO remove
        """
        Temporary test callback.
        
        Todo:
            Remove this method before final release.
        """
        # tae.async_execute(vscp.set_nickname(0x02, 0x0A), visible=False)
        # tae.async_execute(vscp.set_nickname(0x0A, 0x02), visible=False)
        # tae.async_execute(vscp.scan(0, 20), visible=False)
        pass


class Neighbourhood(ctk.CTkFrame):
    """
    Container for the VSCP scanning tools and the node list.

    Combines the ScanWidget (inputs and scan button) and the Neighbours widget (treeview).
    """

    def __init__(self, parent):
        """
        Initialize the Neighbourhood frame.

        Args:
            parent: The parent widget associated with this frame.
        """
        self.parent = parent
        super().__init__(self.parent)

        self.widget = ctk.CTkFrame(parent)
        self.widget.pack(padx=(5, 5), pady=(5, 5), fill='both', expand=True)

        l_neighbourhood = ctk.CTkLabel(self.widget, corner_radius=0, text='Neighbourhood:')
        l_neighbourhood.pack()
        l_neighbourhood.place(x=10, y=-4)

        self.scan_frame = ScanWidget(self.widget)
        self.neighbours = Neighbours(self.widget)
        add_neighbours_handle(self.neighbours)


class ScanWidget(ctk.CTkFrame): # pylint: disable=too-many-instance-attributes
    """
    Widget containing controls for scanning VSCP nodes.

    Allows the user to define a start/stop ID range and initiate a scan.
    """

    def __init__(self, parent):
        """
        Initialize the ScanWidget.

        Args:
            parent: The parent widget associated with this frame.
        """
        self.parent = parent
        super().__init__(self.parent)
        # self.add_node_in_progress = False

        self.widget = ctk.CTkFrame(self.parent)
        self.widget.pack(padx=5, pady=(20, 0), anchor='nw', fill='x', expand=False)

        self.min_range = [0, 254]
        self.max_range = [0, 254]
        self.l_min_id = ctk.CTkLabel(self.widget, corner_radius=0, text='Start ID:')
        self.l_min_id.grid(row=0, column=0, sticky='w', pady=5, padx=(5, 0))
        validate_min_id = (self.register(self._validate_start), '%P')
        self.min_id_var = ctk.StringVar(value=f'0x{self.min_range[0]:02X}')
        self.min_id = ctk.CTkEntry(self.widget, width=45, textvariable=self.min_id_var,
                                   validate="key", validatecommand=validate_min_id)
        self.min_id.bind('<FocusOut>', self._min_id_focus_out)
        self.min_id.bind("<KeyRelease>", self._min_id_format)
        self.min_id.grid(row=0, column=1, sticky='w', pady=5, padx=(3, 0))

        self.l_max_id = ctk.CTkLabel(self.widget, corner_radius=0, text='Stop ID:')
        self.l_max_id.grid(row=0, column=2, sticky='w', pady=5, padx=(10, 0))
        validate_max_id = (self.register(self._validate_stop), '%P')
        self.max_id_var = ctk.StringVar(value=f'0x{self.max_range[1]:02X}')
        self.max_id = ctk.CTkEntry(self.widget, width=45, textvariable=self.max_id_var,
                                   validate="key", validatecommand=validate_max_id)
        self.max_id.bind('<FocusOut>', self._max_id_focus_out)
        self.max_id.bind("<KeyRelease>", self._max_id_format)
        self.max_id.grid(row=0, column=3, sticky='w', pady=5, padx=(3,0))

        self.button_scan = ctk.CTkButton(self.widget, width=50, text='Scan',
                                         command=self._button_scan_callback)
        self.button_scan.grid(row=0, column=4, sticky='w', pady=5, padx=(10, 0))
        # self.toggle_var = ctk.StringVar(value='on')
        # self.toggle = ctk.CTkSwitch(self.widget, variable=self.toggle_var,
        #                             onvalue='on', offvalue='off', text='Smart add',
        #                             command=self.toggle_cb)
        # self.toggle.grid(row=0, column=5, sticky='e', pady=5, padx=(75, 5))
        add_set_state_callback(self.set_scan_widget_state)
        call_set_scan_widget_state('disabled')


    def _min_id_format(self, _):
        """Format the Start ID input to hex style (e.g., 0x01) on key release."""
        input_str = self.min_id_var.get()
        if input_str.lower().startswith('0x'):
            self.min_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _min_id_focus_out(self, _): # TODO implement
        """
        Handle focus out event for Min ID entry.
        
        Todo:
            Implement logic to update internal state or handle validation on exit.
        """
        pass
        # self.max_range[0] = int(self.min_id_var.get(), 0)
        # print('max range', self.max_range)


    def _validate_start(self, input_str):
        """
        Validate the Start ID input.
        
        Args:
            input_str: The current string in the entry widget.
            
        Returns:
            bool: True if input is valid, False otherwise.
        """
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
                if input_str.startswith('00'):
                    result = False
                else:
                    try:
                        result = self.min_range[0] <= int(input_str) <= self.min_range[1]
                    except ValueError:
                        result = False
        return result


    def _max_id_format(self, _):
        """Format the Stop ID input to hex style (e.g., 0xFF) on key release."""
        input_str = self.max_id_var.get()
        if input_str.lower().startswith('0x'):
            self.max_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _max_id_focus_out(self, _): # TODO implement
        """
        Handle focus out event for Max ID entry.
        
        Todo:
            Implement logic to update internal state or handle validation on exit.
        """
        pass
        # self.min_range[1] = int(self.max_id_var.get(), 0)
        # print('min range', self.min_range)


    def _validate_stop(self, input_str):
        """
        Validate the Stop ID input.

        Args:
            input_str: The current string in the entry widget.

        Returns:
            bool: True if input is valid, False otherwise.
        """
        result = True
        if 0 != len(input_str):
            if input_str.lower().startswith('0x'):
                if 2 < len(input_str):
                    if input_str.startswith('0x00'):
                        result = False
                    else:
                        try:
                            result = self.max_range[0] <= int(input_str, 16) <= self.max_range[1]
                        except ValueError:
                            result = False
            else:
                if input_str.startswith('00'):
                    result = False
                else:
                    try:
                        result = self.max_range[0] <= int(input_str) <= self.max_range[1]
                    except ValueError:
                        result = False
        return result


    def _button_scan_callback(self):
        """Initiate the scan process asynchronously."""
        tae.async_execute(self._call_scan(), visible=False)


    async def _call_scan(self):
        """
        Perform the actual node scanning logic.

        Reads the min/max ID, calls the vscp library to scan, and populates
        the neighbours treeview with results.
        """
        min_id = int(self.min_id_var.get(), 0)
        max_id = int(self.max_id_var.get(), 0)
        nodes = await vscp.scan(min_id, max_id)
        if 0 < nodes:
            neighbours_handle().reload_data() # type: ignore


    # def check_node(self, node_id: int):
    #     if 'on' == self.toggle_var.get() and                   \
    #        node_id != vscp.get_this_node_nickname() and        \
    #        self.add_node_in_progress is False:
    #         self.add_node_in_progress = True
    #         tae.async_execute(self._get_new_node_data(node_id), visible=False)


    # async def _get_new_node_data(self, nickname: int) -> None:
    #     if vscp.is_node_on_list(nickname) is False:
    #         node = await vscp.get_node_info(nickname)
    #         vscp.append_node({'id': nickname})
    #     #     node_id = f"0x{node['id']:02X}"
    #     #     if node['isHardCoded'] is True:
    #     #         node_id = '►' + node_id + '◄'
    #     #     data = [{'text': node_id,
    #     #             'child': [{'text': 'GUID:', 'values': [node['guid']['str']]},
    #     #                     {'text': 'MDF:',  'values': ['http://' + node['mdf']]}
    #     #                     ]
    #     #         }]
    #     #     neighbours_handle().insert(data)
    #     self.add_node_in_progress = False


    # def toggle_cb(self): # TODO remove
    #     match self.toggle_var.get():
    #         case 'on':
    #             pass
    #         case _:
    #             pass
    #     # self.add_node_in_progress = False


    def set_scan_widget_state(self, state):
        """
        Enable or disable the scan widget controls.

        Args:
            state: The state to set ('normal' or 'disabled').
        """
        self.l_min_id.configure(state=state)
        self.min_id.configure(state=state)
        self.l_max_id.configure(state=state)
        self.max_id.configure(state=state)
        self.button_scan.configure(state=state)
        # self.toggle.configure(state=state)


class Neighbours(ctk.CTkFrame): # pylint: disable=too-many-instance-attributes
    """
    Widget displaying a treeview of discovered VSCP nodes.

    Provides a context menu (right-click) for node operations like firmware upload
    and configuration.
    """

    def __init__(self, parent):
        """
        Initialize the Neighbours widget.

        Args:
            parent: The parent widget associated with this frame.
        """
        super().__init__(parent)
        self.selected_row_id = ''
        self.parent = parent
        self.config_window = None

        header = [('node', 'Node', 75, 75, 'center', 'w'),
                  ('description', '', 356, 356, 'center', 'w'),
                 ]
        self.widget = ctk.CTkFrame(parent, fg_color='transparent')
        self.widget.pack(padx=0, pady=5, side='top', anchor='nw', fill='both', expand=True)
        self.neighbours = CTkTreeview(self.widget, header, xscroll=False)
        self.neighbours.pack(padx=0, pady=0, fill='both', expand=True)
        self.neighbours.treeview.bind('<Double-Button-1>', self._item_deselect)
        self.neighbours.treeview.bind('<Button-3>', lambda event: self._show_menu(event, self.dropdown))

        self.dropdown = CTkFloatingWindow(self.neighbours)
        self.dropdown_bt_chg_node_id = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                   text="Change Node ID", command=self._change_node_id)
        self.dropdown_bt_chg_node_id.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_configure = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                   text="Configure Node", command=self._configure_node)
        self.dropdown_bt_configure.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_firmware = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                  text="Upload Firmware", command=self._firmware_upload)
        self.dropdown_bt_firmware.pack(expand=True, fill="x", padx=0, pady=0)
        # TODO remove
        # data = []
        # for idx in range(1, 5):
        #     node_id = f"0x{idx:02X}"
        #     entry = {'text': node_id,
        #                 'child': [{'text': 'GUID:', 'values': f'FA:FA:FA:{idx:02d}'},
        #                           {'text': 'MDF:',  'values': f'http://vscp.local/mdf/xxx{idx}.mdf'}
        #                          ]
        #             }
        #     data.append(entry)
        # self.insert(data)


    def insert(self, row_data):
        """
        Insert data rows into the neighbours treeview.

        Args:
            row_data: The data structure to insert into the treeview.
        """
        self.neighbours.insert_items(row_data)


    def reload_data(self):
        """
        Reload and display the list of nodes from VSCP storage.
        
        Clears the current view, fetches nodes from the vscp module,
        formats them, and inserts them back into the treeview.
        """
        self.delete_all_items()
        data = []
        for node in vscp.get_nodes():
            node_id = f"0x{node['id']:02X}"
            if node['isHardCoded'] is True:
                node_id = '►' + node_id + '◄'
            entry = {'text': node_id,
                     'child': [{'text': 'GUID:', 'values': [node['guid']['str']]}, 
                               {'text': 'MDF:',  'values': ['http://' + node['mdf']]}
                              ]
                    }
            data.append(entry)
        if 0 != len(data):
            self.insert(data)


    def _item_deselect(self, event):
        """Handle double-click to deselect an item in the treeview."""
        selected_rows = self.neighbours.treeview.selection()
        row_clicked = self.neighbours.treeview.identify('row', event.x, event.y)
        index = selected_rows.index(row_clicked) if row_clicked in selected_rows else -1
        if -1 < index:
            self.neighbours.treeview.selection_remove(selected_rows[index])


    def delete_all_items(self) -> None:
        """Remove all items from the neighbours treeview."""
        for item in self.neighbours.treeview.get_children():
            self.neighbours.treeview.delete(item)


    def _show_menu(self, event, menu):
        """
        Display the context menu on right-click.

        Args:
            event: The mouse event triggering the menu.
            menu: The menu widget to display.
        """
        self.selected_row_id = self.neighbours.treeview.identify('row', event.x, event.y)
        try:
            if '' != self.selected_row_id:
                menu.popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


    def _set_menu_items_state(self, state):
        """
        Set the enabled/disabled state of the context menu items.

        Args:
            state: The state to set ('normal' or 'disabled').
        """
        self.dropdown_bt_firmware.configure(state=state)
        self.dropdown_bt_configure.configure(state=state)
        self.dropdown_bt_chg_node_id.configure(state=state)


    def _get_node_id(self) -> int:
        """
        Retrieve the Node ID of the currently selected row.

        Returns:
            int: The node ID, or -1 if invalid or not found.
        """
        parent_id = self.neighbours.treeview.parent(self.selected_row_id)
        text = self.neighbours.treeview.item(parent_id)['text'] if parent_id else   \
            self.neighbours.treeview.item(self.selected_row_id)['text']
        try:
            result = int(text, 0)
        except ValueError:
            result = -1
        return result


    def _get_mdf_link(self) -> str:
        """
        Retrieve the MDF link associated with the selected node.

        Returns:
            str: The URL of the MDF file.
        """
        result = ''
        parent_id = self.neighbours.treeview.parent(self.selected_row_id)
        if not parent_id:
            parent_id = self.selected_row_id
        for item in self.neighbours.treeview.get_children(item=parent_id):
            if 'MDF' in self.neighbours.treeview.item(item)['text']:
                try:
                    result = self.neighbours.treeview.item(item)['values'][0]
                    break
                except KeyError:
                    pass
        return result


    def _get_guid(self) -> str:
        """
        Retrieve the GUID of the selected node.

        Returns:
            str: The Globally Unique Identifier of the node.
        """
        result = ''
        parent_id = self.neighbours.treeview.parent(self.selected_row_id)
        if not parent_id:
            parent_id = self.selected_row_id
        for item in self.neighbours.treeview.get_children(item=parent_id):
            if 'GUID' in self.neighbours.treeview.item(item)['text']:
                try:
                    result = self.neighbours.treeview.item(item)['values'][0]
                    break
                except KeyError:
                    pass
        return result


    def _confirm_firmware_upload(self, node_id: int) -> bool:
        """
        Ask user for confirmation before uploading firmware.

        Args:
            node_id: The ID of the node to receive firmware.

        Returns:
            bool: True if confirmed, False otherwise.
        """
        title = 'Uploading new firmware'
        message = f'Are you sure you want to upload new firmware to node 0x{node_id:02X}?'
        msg = CTkMessagebox(title=title, message=message, icon='question',
                            option_1='No', option_2='Yes')
        response = msg.get()
        return 'Yes' == str(response)


    def _firmware_upload(self):
        """
        Handle the firmware upload process.

        Opens a file dialog to select the firmware file (hex/bin) and initiates
        the async upload if confirmed.
        """
        node_id = self._get_node_id()
        if -1 < node_id:
            current_path = os.getcwd()
            filetypes = (('bin files', '*.bin'), ('hex files', '*.hex'))
            fw_path = ctk.filedialog.askopenfilename(title='Select Firmware to upload',
                                                     initialdir=current_path,
                                                     filetypes=filetypes)
            if '' != fw_path:
                if self._confirm_firmware_upload(node_id) is True:
                    extension = os.path.splitext(fw_path)[1][1:].lower()
                    fw = IntelHex()
                    try:
                        fw.fromfile(fw_path, format=extension)
                        fw_data = fw.tobinarray().tolist()
                        result = True
                    except ValueError:
                        result = False
                    if result is True:
                        tae.async_execute(vscp.firmware_upload(node_id, fw_data), visible=False) # type: ignore
            else:
                CTkMessagebox(title='Error', message='Firmware file not selected!!!', icon='cancel')
        else:
            CTkMessagebox(title='Error', message='Undefined Node ID!!!', icon='cancel')


    def _get_local_mdf(self):
        """
        Open a file dialog to select and read a local MDF file.

        Returns:
            bytes: The content of the selected MDF file as bytes, or an empty string on failure.
        """
        result = ''
        node_id = self._get_node_id()
        if -1 < node_id:
            current_path = os.getcwd()
            filetypes = (('MDF files', '*.mdf'),)
            mdf_path = ctk.filedialog.askopenfilename(title=f'Select Module Description File for node 0x{node_id:02X}',
                                                    initialdir=current_path,
                                                    filetypes=filetypes)
            try:
                result = Path(mdf_path).read_bytes()
            except: # pylint: disable=bare-except
                pass
        else:
            CTkMessagebox(title='Error', message='Undefined Node ID!!!', icon='cancel')
        return result


    def _configure_node(self):
        """
        Handle node configuration.

        Fetches the MDF file (either from URL or local fallback), parses it,
        and opens the NodeConfiguration window.
        """
        node_id = self._get_node_id()
        guid = self._get_guid()
        mdf_link = self._get_mdf_link()
        if 'vscp.local' in mdf_link.lower():
            mdf_link = re.sub(re.escape('vscp.local'), 'localhost', mdf_link, flags=re.IGNORECASE)
        mdf = ''
        try:
            req = requests.get(mdf_link, timeout=5)
            if 200 == int(req.status_code):
                mdf = req.content
        except: # pylint: disable=bare-except
            pass
        if not mdf:
            mdf = self._get_local_mdf()
        if mdf:
            try:
                vscp.mdf.parse(mdf) # type: ignore
                self._set_menu_items_state('disabled')
                self.config_window = NodeConfiguration(self, node_id, guid)
                self.config_window.bring_to_front()
            except: # pylint: disable=bare-except
                CTkMessagebox(title='Error', message='Error while parsing an MDF file!!!', icon='cancel')
        else:
            CTkMessagebox(title='Error', message='No valid MDF file for the selected node!!!', icon='cancel')


    def _change_node_id(self):
        """
        Handle changing the node ID.
        """
        node_id = self._get_node_id()
        if -1 < node_id:
            ChangeNodeId(self, node_id, self._do_change_nickname)
        else:
            CTkMessagebox(title='Error', message='Undefined Node ID!!!', icon='cancel')


    def _do_change_nickname(self, old_id, new_id):
        """
        Callback to execute the nickname change asynchronously.

        Args:
            old_id (int): Current node ID.
            new_id (int): New node ID.
        """
        async def _task():
            if await vscp.set_nickname(old_id, new_id):
                vscp.update_node_id(old_id, new_id)
                self.reload_data()

        tae.async_execute(_task(), visible=False)


    def close_node_configuration(self):
        """
        Cleanup callback when the node configuration window is closed.

        Destroys the window instance and re-enables menu items.
        """
        try:
            self.config_window.window.destroy() # type: ignore
        except: # pylint: disable=bare-except
            pass
        finally:
            self.config_window = None
            self._set_menu_items_state('normal')


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

        # Center the window relative to the application window
        width = 270
        height = 130

        # Get application window geometry
        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (width / 2))
        y = int(app_window.winfo_rooty() + (app_window.winfo_height() / 2) - (height / 2))

        self.geometry(f'{width}x{height}+{x}+{y}')
        self.resizable(False, False)

        # Input Frame (Row 1)
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

        # Button Frame (Row 2)
        self.frame_buttons = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_buttons.pack(side='top', fill='both', expand=True)
        self.frame_buttons.grid_columnconfigure((0, 1), weight=1)
        self.frame_buttons.grid_rowconfigure(0, weight=1)

        self.btn_ok = ctk.CTkButton(self.frame_buttons, text="OK", width=90, command=self._on_ok)
        self.btn_ok.grid(row=0, column=0, padx=(10, 20), sticky="e")

        self.btn_cancel = ctk.CTkButton(self.frame_buttons, text="Cancel", width=90, command=self.destroy)
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

            # Check if node already exists
            if vscp.is_node_on_list(new_id):
                CTkMessagebox(title='Error', message=f'Node ID 0x{new_id:02X} already exists!', icon='cancel')
                return

            if self.callback:
                self.callback(self.current_id, new_id)
            self.destroy()
        except ValueError:
            pass
