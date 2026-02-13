"""
Left panel module for the VSCP application.

This module handles the left-side panel of the GUI, including the neighbourhood
scanning functionality, node listing, and general node management actions like
firmware upload and configuration.

@file panel_left.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import os
import re
from pathlib import Path
from typing import Any, cast
import requests
import tk_async_execute as tae
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from intelhex import IntelHex
import vscp
from .treeview import CTkTreeview
from .common import add_set_state_callback, add_neighbours_handle,  \
                    neighbours_handle, call_set_filter_blocking,    \
                    set_auto_discovery
from .popup import CTkFloatingWindow
from .node_config import NodeConfiguration
from .change_node_id import ChangeNodeId
from .device_provisioner import DeviceProvisioner


class AlignedReverseCheckBox(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    Custom Checkbox widget with label on the left and checkbox on the right.
    """

    def __init__(self, master, text="Option", label_width=100, command=None, **kwargs):
        """
        Initialize the AlignedReverseCheckBox.

        Args:
            master: Parent widget.
            text: Label text.
            label_width: Fixed width for the label to ensure alignment.
            command: Callback function when toggled.
            **kwargs: Additional arguments for CTkFrame.
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.label = ctk.CTkLabel(self, text=text, width=label_width, anchor="e", cursor="hand2")
        self.label.grid(row=0, column=0, sticky="e")

        self.checkbox = ctk.CTkCheckBox(self, text="", width=24, command=command)
        self.checkbox.grid(row=0, column=1, sticky="w", padx=(5, 0))

        self.label.bind("<Button-1>", lambda e: self.checkbox.toggle())


    # Helper methods
    def get(self):
        """Return the current value of the checkbox."""
        return self.checkbox.get()


    def toggle(self):
        """Toggle the checkbox state."""
        self.checkbox.toggle()


    def select(self):
        """Select the checkbox."""
        self.checkbox.select()


    def deselect(self):
        """Deselect the checkbox."""
        self.checkbox.deselect()


    def configure(self, require_redraw=False, **kwargs):
        """
        Pass configuration to children.
        Specifically handles 'state' to enable/disable interaction for both label and checkbox.
        """
        if 'state' in kwargs:
            state = kwargs.pop('state')
            self.checkbox.configure(state=state)
            self.label.configure(state=state)
        super().configure(require_redraw=require_redraw, **kwargs)


class LeftPanel(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    """
    Main container for the left panel of the application.

    Holds the Neighbourhood widget and general command buttons.
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


    def button_cb(self):
        """Callback for the 'Send Host DateTime' button."""
        tae.async_execute(vscp.send_host_datetime(), visible=False)


class Neighbourhood(ctk.CTkFrame): # pylint: disable=too-many-ancestors
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


class ScanWidget(ctk.CTkFrame): # pylint: disable=too-many-ancestors, too-many-instance-attributes
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

        # Track external state (connection status)
        self._external_state = 'disabled'

        self.widget = ctk.CTkFrame(self.parent)
        self.widget.pack(padx=5, pady=(20, 0), anchor='nw', fill='x', expand=False)

        self.min_range = [0, 254]
        self.max_range = [0, 254]

        # Define variables first to ensure they exist for validation callbacks
        self.min_id_var = ctk.StringVar(value=f'0x{self.min_range[0]:02X}')
        self.max_id_var = ctk.StringVar(value=f'0x{self.max_range[1]:02X}')

        self.l_min_id = ctk.CTkLabel(self.widget, corner_radius=0, text='Start ID:')
        self.l_min_id.grid(row=0, column=0, sticky='w', pady=5, padx=(5, 0))

        validate_min_id = (self.register(self._validate_start), '%P')
        self.min_id = ctk.CTkEntry(self.widget, width=45, textvariable=self.min_id_var,
                                   validate="key", validatecommand=validate_min_id)
        self.min_id.bind("<KeyRelease>", self._min_id_format)
        self.min_id.grid(row=0, column=1, sticky='w', pady=5, padx=(3, 0))

        self.l_max_id = ctk.CTkLabel(self.widget, corner_radius=0, text='Stop ID:')
        self.l_max_id.grid(row=0, column=2, sticky='w', pady=5, padx=(10, 0))

        validate_max_id = (self.register(self._validate_stop), '%P')
        self.max_id = ctk.CTkEntry(self.widget, width=45, textvariable=self.max_id_var,
                                   validate="key", validatecommand=validate_max_id)
        self.max_id.bind("<KeyRelease>", self._max_id_format)
        self.max_id.grid(row=0, column=3, sticky='w', pady=5, padx=(3,0))

        self.button_scan = ctk.CTkButton(self.widget, width=50, text='Scan',
                                         command=self._button_scan_callback)
        self.button_scan.grid(row=0, column=4, sticky='w', pady=5, padx=(10, 0))

        # Push column 6 (Auto-discovery) to the far right edge of the frame
        self.widget.grid_columnconfigure(5, weight=1)

        self.auto_disc_var = ctk.StringVar(value="on")
        self.chk_auto_disc = AlignedReverseCheckBox(self.widget, text="Auto-discovery",
                                                    label_width=100,
                                                    command=self._toggle_auto_discovery)
        self.chk_auto_disc.grid(row=0, column=6, sticky='e', pady=5, padx=(10, 5))

        # Set initial visual state and global flag
        self.chk_auto_disc.select()
        set_auto_discovery(True)

        # Restore the callback mechanism to handle state changes from common.py
        add_set_state_callback(self.set_scan_widget_state)

        # Apply initial UI state
        self._update_ui_state()


    def _toggle_auto_discovery(self):
        """
        Callback for Auto-discovery checkbox.
        Updates the shared state in common module and refreshes UI.
        """
        is_enabled = self.chk_auto_disc.get() == 1
        set_auto_discovery(is_enabled)
        self._update_ui_state()


    def _update_ui_state(self):
        # pylint: disable=line-too-long
        """
        Logic to determine the state of controls based on:
        1. External connection/bus state (self._external_state)
        2. Auto-discovery checkbox state

        Rules:
        - If external state is 'disabled' (no connection/busy), controls are disabled.
        - If Auto-discovery is CHECKED, controls (Scan/Inputs) are disabled.
        - Checkbox itself generally remains enabled unless external state dictates complete lockout (e.g. busy scan).
        """
        # pylint: enable=line-too-long
        is_auto_disc = self.chk_auto_disc.get() == 1

        state_controls = 'normal'
        state_checkbox = 'normal'

        # Rule 1: Dependency on CAN adapter connection (or busy state passed from common)
        if self._external_state == 'disabled':
            state_controls = 'disabled'

        # Rule 2: If checkbox is selected -> controls disabled regardless of other conditions
        if is_auto_disc:
            state_controls = 'disabled'

        # Apply states
        self.l_min_id.configure(state=state_controls)
        self.min_id.configure(state=state_controls)
        self.l_max_id.configure(state=state_controls)
        self.max_id.configure(state=state_controls)
        self.button_scan.configure(state=state_controls)

        # Checkbox state logic
        self.chk_auto_disc.configure(state=state_checkbox)


    def set_scan_widget_state(self, state):
        # pylint: disable=line-too-long
        """
        Callback triggered by common.py to set the general widget state.
        Usually indicates if the CAN adapter is connected ('normal') or disconnected/busy ('disabled').

        Args:
            state: The state to set ('normal' or 'disabled').
        """
        # pylint: enable=line-too-long
        self._external_state = state
        self._update_ui_state()


    def _min_id_format(self, _):
        """Format the Start ID input to hex style (e.g., 0x01) on key release."""
        input_str = self.min_id_var.get()

        if not input_str.lower().startswith('0x'):
            clean_hex = ''.join(filter(lambda x: x in '0123456789abcdefABCDEF', input_str))
            new_val = f'0x{clean_hex}'
            self.min_id_var.set(new_val)
            self.min_id.icursor('end')
            return

        if input_str.lower().startswith('0x'):
            self.min_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _validate_start(self, input_str):
        """
        Validate the Start ID input.
        Returns True if input is valid, False otherwise.
        """
        if not input_str.lower().startswith('0x'):
            return False

        # Allow incomplete '0x' during editing
        if len(input_str) < 3:
            return True

        is_valid = False
        try: # pylint: disable=too-many-nested-blocks
            val = int(input_str, 16)

            # Global range check (0-254)
            if self.min_range[0] <= val <= self.min_range[1]:
                is_valid = True

                # Cross-check: Start ID must be <= Stop ID
                if hasattr(self, 'max_id_var'):
                    try:
                        current_max_str = self.max_id_var.get()
                        if len(current_max_str) > 2:
                            max_val = int(current_max_str, 16)
                            if val > max_val:
                                is_valid = False
                    except ValueError:
                        pass # Stop ID is invalid, relax constraint

        except (ValueError, Exception): # pylint: disable=broad-exception-caught
            # Fallback to prevent disabling validation permanently
            is_valid = False

        return is_valid


    def _max_id_format(self, _):
        """Format the Stop ID input to hex style (e.g., 0xFF) on key release."""
        input_str = self.max_id_var.get()

        if not input_str.lower().startswith('0x'):
            clean_hex = ''.join(filter(lambda x: x in '0123456789abcdefABCDEF', input_str))
            new_val = f'0x{clean_hex}'
            self.max_id_var.set(new_val)
            self.max_id.icursor('end')
            return

        if input_str.lower().startswith('0x'):
            self.max_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _validate_stop(self, input_str):
        """
        Validate the Stop ID input.
        Returns True if input is valid, False otherwise.
        """
        if not input_str.lower().startswith('0x'):
            return False

        # Allow incomplete '0x' during editing
        if len(input_str) < 3:
            return True

        is_valid = False
        try: # pylint: disable=too-many-nested-blocks
            val = int(input_str, 16)

            # Global range check (0-254)
            if self.max_range[0] <= val <= self.max_range[1]:
                is_valid = True

                # Cross-check: Stop ID must be >= Start ID
                if hasattr(self, 'min_id_var'):
                    try:
                        current_min_str = self.min_id_var.get()
                        if len(current_min_str) > 2:
                            min_val = int(current_min_str, 16)

                            # Check "lookahead": Is it possible to form a valid number
                            # >= min_val from this input?
                            missing_chars = 4 - len(input_str)
                            missing_chars = max(missing_chars, 0)

                            # Construct the largest possible number starting with input_str
                            potential_max_str = input_str + ('F' * missing_chars)
                            potential_max_val = int(potential_max_str, 16)

                            if potential_max_val < min_val:
                                is_valid = False
                    except ValueError:
                        pass # Start ID is invalid, relax constraint

        except (ValueError, Exception): # pylint: disable=broad-exception-caught
            is_valid = False

        return is_valid


    def _button_scan_callback(self):
        """Initiate the scan process asynchronously."""
        min_str = self.min_id_var.get()
        max_str = self.max_id_var.get()
        error_msg = None

        if len(min_str) < 3:
            error_msg = "Start ID is invalid (empty or incomplete)."
        elif len(max_str) < 3:
            error_msg = "Stop ID is invalid (empty or incomplete)."
        else:
            try:
                min_val = int(min_str, 16)
                max_val = int(max_str, 16)

                if min_val > max_val:
                    error_msg = f"Start ID (0x{min_val:02X}) cannot be greater than Stop ID (0x{max_val:02X})." # pylint: disable=line-too-long
                elif not 0 <= min_val <= 254:
                    error_msg = "Start ID must be between 0x00 and 0xFE."
                elif not 0 <= max_val <= 254:
                    error_msg = "Stop ID must be between 0x00 and 0xFE."
            except ValueError:
                error_msg = "Invalid hexadecimal format."

        if error_msg:
            CTkMessagebox(title='Error', message=error_msg, icon='cancel')
            return

        tae.async_execute(self._call_scan(), visible=False)


    async def _call_scan(self):
        """
        Perform the actual node scanning logic.

        Reads the min/max ID, calls the vscp library to scan, and populates
        the neighbours treeview with results.
        """
        try:
            min_id = int(self.min_id_var.get(), 16)
            max_id = int(self.max_id_var.get(), 16)
        except ValueError:
            return

        nodes = await vscp.scan(min_id, max_id)
        if 0 < nodes:
            handle = neighbours_handle()
            if hasattr(handle, 'reload_data'):
                cast(Any, handle).reload_data()


class Neighbours(ctk.CTkFrame): # pylint: disable=too-many-ancestors, too-many-instance-attributes
    # pylint: disable=line-too-long
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
        self.dropdown_bt_chg_node_id = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0, width=190,
                                                     text="Change Node ID", command=self._change_node_id)
        self.dropdown_bt_chg_node_id.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_configure = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0, width=190,
                                                   text="Configure Node", command=self._configure_node)
        self.dropdown_bt_configure.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_drop_id_or_reset = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0, width=190,
                                                          text="Drop Node ID / Reset Device", command=self._drop_id_or_reset)
        self.dropdown_bt_drop_id_or_reset.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_firmware = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0, width=190,
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
        Automatically blocks messages during upload and restores the filter afterwards
        using the decoupled Observer pattern via 'common'.
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

                        # Define async task to handle filter toggling and upload via Observer
                        async def _upload_task():
                            # 1. Hide all messages (Publish event: Block=True)
                            call_set_filter_blocking(True)

                            try:
                                # 2. Execute bootloader procedure
                                await vscp.firmware_upload(node_id, fw_data)
                            finally:
                                # 3. Restore filter state (Publish event: Block=False)
                                call_set_filter_blocking(False)

                        tae.async_execute(_upload_task(), visible=False)
                    except ValueError:
                        pass
            else:
                CTkMessagebox(title='Error', message='Firmware file not selected!!!', icon='cancel')
        else:
            CTkMessagebox(title='Error', message='Undefined Node ID!!!', icon='cancel')


    def _get_local_mdf(self):
        """
        Open a file dialog to select and read a local MDF file.
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
        # Handle local proxy/tunneling if applicable
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
                mdf_text = mdf.decode('utf-8') if isinstance(mdf, bytes) else str(mdf)
                vscp.mdf.parse(mdf_text)
                self._set_menu_items_state('disabled')
                self.config_window = NodeConfiguration(self, node_id, guid)
                self.config_window.bring_to_front()
            except: # pylint: disable=bare-except
                self.close_node_configuration()
                CTkMessagebox(title='Error', message='Error while parsing an MDF file!!!', icon='cancel')
        else:
            CTkMessagebox(title='Error', message='No valid MDF file for the selected node!!!', icon='cancel')


    def _drop_id_or_reset(self):
        """
        Handle dropping node ID or resetting the device.
        Opens the DeviceProvisioner dialog to configure parameters.
        """
        node_id = self._get_node_id()
        if node_id > -1:
            DeviceProvisioner(cast(ctk.CTk, self.winfo_toplevel()), node_id, self._execute_drop_reset)
        else:
            CTkMessagebox(title='Error', message='Undefined Node ID!!!', icon='cancel')


    def _execute_drop_reset(self, node_id, reset, defaults, idle, wait_time): # pylint: disable=too-many-arguments, too-many-positional-arguments
        """
        Callback to execute the Drop Nickname / Reset command asynchronously.

        Args:
            node_id (int): The target node.
            reset (bool): Keep nickname (reset only).
            defaults (bool): Restore storage to defaults.
            idle (bool): Go to idle state.
            wait_time (int): Delay before execution.
        """
        tae.async_execute(vscp.drop_nickname_reset_device(node_id, reset, defaults, idle, wait_time), visible=False)


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
            if self.config_window is not None:
                self.config_window.window.destroy()
        except: # pylint: disable=bare-except
            pass
        finally:
            self.config_window = None
            self._set_menu_items_state('normal')
