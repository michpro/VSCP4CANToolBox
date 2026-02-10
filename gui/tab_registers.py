"""
Registers Tab Module.

This module provides the `RegistersTab` class for the Node Configuration window.
It handles displaying, reading, and writing VSCP registers using a Treeview.

@file tab_registers.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""
# pylint: disable=too-many-lines


import customtkinter as ctk
import tk_async_execute as tae
import vscp
from gui.common import update_progress
from .info_widget import ScrollableInfoTable
from .treeview import CTkTreeview
from .tooltip import ToolTip
from .popup import CTkFloatingWindow


class RegistersTab(ctk.CTkFrame): # pylint: disable=too-many-instance-attributes, too-many-ancestors
    """
    Tab for viewing and editing VSCP registers.

    Displays register data in a treeview and shows detailed information about
    the selected register in a side panel using a rich text table.
    """

    def __init__(self, parent, node_id: int):
        # pylint: disable=line-too-long
        """
        Initializes the RegistersTab.

        Sets up the treeview columns, layout, and loads register definitions
        from the VSCP MDF.

        Args:
            parent: The parent widget (tab).
            node_id: The ID of the node to read registers from.
        """
        self.parent = parent
        self.node_id = node_id
        self.selected_row_id = ''
        super().__init__(self.parent)

        self.widget = ctk.CTkFrame(parent, fg_color='transparent')
        self.widget.pack(padx=0, pady=0, side='top', anchor='nw', fill='both', expand=True)

        header = [('address',   'Page:Offset',  105, 105, 'center', 'center'),
                  ('access',    'Access',       45,  45,  'center', 'center'),
                  ('value',     'Value',        45,  45,  'center', 'center'),
                  ('toSync',    'To Sync',      45,  45,  'center', 'center'),
                  ('name',      '  Name',       505, 505, 'w',      'w'),
                  ]
        self.registers = CTkTreeview(self.widget, header, xscroll=False)
        self.registers.pack(side='left', padx=0, pady=0, fill='both', expand=True)

        self.registers.enable_cell_editing(columns=['value'],
                                           edit_callback=self._on_cell_edit,
                                           permission_callback=self._can_edit_cell,
                                           input_validation=self._validate_input)

        self.registers.treeview.bind('<<TreeviewSelect>>', self._update_registers_info)
        self.registers.treeview.bind('<Button-3>', lambda event: self._show_menu(event, self.dropdown))
        self.registers.treeview.bind('<Button-1>', self._on_treeview_click)

        # --- Context Menu (Popup) ---
        # Using self.widget.winfo_toplevel() as master to ensure correct parenting on the Toplevel window
        self.dropdown = CTkFloatingWindow(self.widget.winfo_toplevel(), width=220)

        self.dropdown_bt_read_all = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                  text="Read all registers", command=self._bt_read_all_registers)
        self.dropdown_bt_read_all.pack(expand=True, fill="x", padx=0, pady=0)

        self.dropdown_bt_read_selected = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                       text="Read selected registers", command=self._bt_read_selected_registers)
        self.dropdown_bt_read_selected.pack(expand=True, fill="x", padx=0, pady=0)

        self.dropdown_bt_write_selected = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                        text="Write selected registers", command=self._bt_write_selected_registers)
        self.dropdown_bt_write_selected.pack(expand=True, fill="x", padx=0, pady=0)

        self.dropdown_bt_write_all = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                   text="Write all registers", command=self._bt_write_all_registers)
        self.dropdown_bt_write_all.pack(expand=True, fill="x", padx=0, pady=0)
        # ----------------------------

        # --- Info Panel ---
        temp_fg_color = tuple(self._fg_color) if isinstance(self._fg_color, list) else self._fg_color
        self.container_bg_color = temp_fg_color  # Store for dynamic widgets background inheritance

        self.info_container = ctk.CTkFrame(self.widget, width=350, fg_color=temp_fg_color)
        self.info_container.pack(padx=(5, 0), pady=0, side='right', anchor='ne', fill='y', expand=False)
        self.info_container.grid_propagate(False)

        # Use Grid layout for info_container to handle dynamic resizing properly
        self.info_container.grid_columnconfigure(0, weight=1)
        self.info_container.grid_rowconfigure(0, weight=1) # Row 0: Registers Info (expands)
        self.info_container.grid_rowconfigure(1, weight=0) # Row 1: Dynamic Widgets (shrinks)

        self.registers_info = ScrollableInfoTable(
            self.info_container,
            data={},
            col1_width=110, # Fixed width for labels column
            font_size=11,
            fg_color=temp_fg_color
        )
        self.registers_info.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.dynamic_frame = ctk.CTkFrame(self.info_container, fg_color="transparent")

        # Start async read of real register values
        tae.async_execute(self._prepare_registers_data(), wait=False, visible=False, pop_up=False, callback=None, master=self)
        # pylint: enable=line-too-long


    def _insert_registers_data(self):
        """
        Populates the register treeview with data.

        Iterates through the register data structure (organized by page and register address)
        and inserts rows into the treeview.
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
            self.registers.insert_items(result)


    def _on_treeview_click(self, event):
        """
        Handles click events on the treeview to deselect items if clicked on empty space.
        """
        if not self.registers.treeview.identify_row(event.y):
            self.registers.treeview.selection_remove(self.registers.treeview.selection())
            self._update_registers_info(None)


    async def _execute_read_registers(self, registers_map: dict, start_progress: float = 0.0) -> None: # pylint: disable=line-too-long, too-many-locals, too-many-branches, too-many-statements
        """
        Helper method to execute read operations for a provided map of registers.
        Handles node probing, chunking, reading from VSCP, and UI updates.

        Args:
            registers_map (dict): A dictionary where keys are page numbers (int)
                                  and values are lists of register addresses (int) to read.
            start_progress (float): Initial progress bar value (0.0 to 1.0).
        """
        vscp.set_async_work(True)
        update_progress(start_progress)

        if not registers_map:
            vscp.set_async_work(False)
            update_progress(1.0)
            return

        # 1. Check if node is online
        found_node = await vscp.probe_node(self.node_id)
        if found_node is None:
            vscp.set_async_work(False)
            update_progress(1.0)
            return

        # 2. Calculate total chunks for progress bar
        sorted_pages = sorted(registers_map.keys())
        total_chunks = 0

        for page in sorted_pages:
            addresses = sorted(registers_map[page])
            if not addresses:
                continue

            # Group contiguous registers into chunks (max size 4)
            current_chunk_len = 1
            current_reg = addresses[0]
            current_page_chunks = 1

            for addr in addresses[1:]:
                if addr == current_reg + 1 and current_chunk_len < 4:
                    current_chunk_len += 1
                    current_reg = addr
                else:
                    current_page_chunks += 1
                    current_chunk_len = 1
                    current_reg = addr
            total_chunks += current_page_chunks

        # Calculate progress step
        step = (0.9 - start_progress) / total_chunks if total_chunks > 0 else 0
        progress = start_progress + (0.1 if start_progress == 0 else 0)
        update_progress(progress)

        # 3. Read registers page by page
        for page in sorted_pages:
            addresses = sorted(registers_map[page])
            if not addresses:
                continue

            chunks = []
            current_chunk = [addresses[0]]

            for addr in addresses[1:]:
                if addr == current_chunk[-1] + 1 and len(current_chunk) < 4:
                    current_chunk.append(addr)
                else:
                    chunks.append(current_chunk)
                    current_chunk = [addr]
            chunks.append(current_chunk)

            vscp_page = 0 if page < 0 else page

            for chunk in chunks:
                start_reg = chunk[0]
                count = len(chunk)

                values = await vscp.extended_page_read_register(self.node_id, vscp_page, start_reg, count) # pylint: disable=line-too-long

                if values:
                    for idx, val in enumerate(values):
                        reg_addr = start_reg + idx
                        hex_value = f'0x{val:02X}'

                        if reg_addr in self.registers_data[page]:
                            self.registers_data[page][reg_addr]['value'] = hex_value
                            self.registers_data[page][reg_addr]['to_sync'] = vscp.mdf.sync_read

                        self._update_treeview_value(page, reg_addr, hex_value, set_sync=vscp.mdf.sync_read) # pylint: disable=line-too-long

                progress += step
                update_progress(progress)

        vscp.set_async_work(False)
        update_progress(1.0)


    async def _execute_write_registers(self, registers_map: dict) -> None: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Helper method to execute write operations for a provided map of registers.
        Handles node probing, chunking, writing to VSCP, verification, and UI updates.

        Args:
            registers_map (dict): A dictionary where keys are page numbers (int)
                                  and values are dictionaries mapping address (int) to value (int).
        """
        vscp.set_async_work(True)
        update_progress(0.0)

        if not registers_map:
            vscp.set_async_work(False)
            update_progress(1.0)
            return

        # 1. Check if node is online
        found_node = await vscp.probe_node(self.node_id)
        if found_node is None:
            vscp.set_async_work(False)
            update_progress(1.0)
            return

        # 2. Calculate total chunks for progress bar
        sorted_pages = sorted(registers_map.keys())
        total_chunks = 0

        for page in sorted_pages:
            addresses = sorted(registers_map[page].keys())
            if not addresses:
                continue

            current_len = 1
            current_prev = addresses[0]
            current_page_chunks = 1

            for addr in addresses[1:]:
                if addr == current_prev + 1 and current_len < 4:
                    current_len += 1
                else:
                    current_page_chunks += 1
                    current_len = 1
                current_prev = addr
            total_chunks += current_page_chunks

        step = 0.9 / total_chunks if total_chunks > 0 else 0
        progress = 0.1
        update_progress(progress)

        # 3. Write registers page by page
        for page in sorted_pages:
            addresses = sorted(registers_map[page].keys())
            if not addresses:
                continue

            # Grouping Logic into separate write operations
            write_ops = []
            curr_op_start = addresses[0]
            curr_op_vals = [registers_map[page][curr_op_start]]

            for addr in addresses[1:]:
                if addr == curr_op_start + len(curr_op_vals) and len(curr_op_vals) < 4:
                    curr_op_vals.append(registers_map[page][addr])
                else:
                    write_ops.append((curr_op_start, curr_op_vals))
                    curr_op_start = addr
                    curr_op_vals = [registers_map[page][addr]]
            write_ops.append((curr_op_start, curr_op_vals))

            vscp_page = 0 if page < 0 else page

            for start_reg, values in write_ops:
                returned_values = await vscp.extended_page_write_register(self.node_id, vscp_page, start_reg, values) # pylint: disable=line-too-long

                if returned_values:
                    # Update local data and UI with verified values
                    for idx, val in enumerate(returned_values):
                        reg_addr = start_reg + idx
                        hex_value = f'0x{val:02X}'

                        if reg_addr in self.registers_data[page]:
                            self.registers_data[page][reg_addr]['value'] = hex_value
                            self.registers_data[page][reg_addr]['to_sync'] = vscp.mdf.sync_read

                        self._update_treeview_value(page, reg_addr, hex_value, set_sync=vscp.mdf.sync_read) # pylint: disable=line-too-long
                progress += step
                update_progress(progress)

        vscp.set_async_work(False)
        update_progress(1.0)


    async def _read_all_registers(self, start_progress: float = 0.0) -> None:
        """
        Reads all registers defined in the MDF.
        Prepares the registers map and delegates to _execute_read_registers.
        """
        # Prepare map of all registers: {page: [list_of_addresses]}
        registers_to_read = {}
        for page, regs in self.registers_data.items():
            if regs:
                registers_to_read[page] = list(regs.keys())

        await self._execute_read_registers(registers_to_read, start_progress)


    async def _read_selected_registers(self):
        """
        Reads only the registers currently selected in the Treeview.
        Prepares the registers map and delegates to _execute_read_registers.
        """
        selection = self.registers.treeview.selection()
        registers_to_read = {}

        for item_id in selection:
            parent_id = self.registers.treeview.parent(item_id)
            if not parent_id:
                continue

            parent_text = self.registers.treeview.item(parent_id, 'text')
            if 'Page' in parent_text:
                try:
                    page = int(parent_text.split(' ')[1])
                except IndexError:
                    continue
            else:
                page = -1 # Standard regs

            item_text = self.registers.treeview.item(item_id, 'text')
            try:
                addr = int(item_text, 16)
            except ValueError:
                continue

            if page not in registers_to_read:
                registers_to_read[page] = []
            registers_to_read[page].append(addr)

        await self._execute_read_registers(registers_to_read)


    async def _write_selected_registers(self):
        """
        Writes registers currently selected in the Treeview that are marked for sync.
        Prepares the registers map and delegates to _execute_write_registers.
        """
        selection = self.registers.treeview.selection()
        registers_to_write = {}

        for item_id in selection:
            parent_id = self.registers.treeview.parent(item_id)
            if not parent_id:
                continue

            parent_text = self.registers.treeview.item(parent_id, 'text')
            if 'Page' in parent_text:
                try:
                    page = int(parent_text.split(' ')[1])
                except IndexError:
                    continue
            else:
                page = -1 # Standard regs

            item_text = self.registers.treeview.item(item_id, 'text')
            try:
                addr = int(item_text, 16)
            except ValueError:
                continue

            if page in self.registers_data and addr in self.registers_data[page]:
                reg_data = self.registers_data[page][addr]
                if reg_data.get('to_sync') == vscp.mdf.sync_write:
                    try:
                        val_int = int(reg_data['value'], 16)
                        if page not in registers_to_write:
                            registers_to_write[page] = {}
                        registers_to_write[page][addr] = val_int
                    except (ValueError, TypeError):
                        pass

        await self._execute_write_registers(registers_to_write)


    async def _write_all_registers(self):
        """
        Writes all registers marked for sync in the entire register map.
        Prepares the registers map and delegates to _execute_write_registers.
        """
        registers_to_write = {}

        for page, regs in self.registers_data.items():
            for addr, data in regs.items():
                if data.get('to_sync') == vscp.mdf.sync_write:
                    try:
                        val_int = int(data['value'], 16)
                        if page not in registers_to_write:
                            registers_to_write[page] = {}
                        registers_to_write[page][addr] = val_int
                    except (ValueError, TypeError):
                        pass

        await self._execute_write_registers(registers_to_write)


    async def _prepare_registers_data(self):
        """
        Initializes register data from MDF and triggers the first read from device.
        """
        update_progress(0.0)
        vscp.set_async_work(True)
        update_progress(0.05)

        self.registers_data = vscp.mdf.get_registers_info()
        self._insert_registers_data()

        progress = 0.1
        update_progress(progress)

        # Async work flag will be managed inside _read_all_registers,
        # but we keep it True above to prevent user interaction during MDF load
        await self._read_all_registers(start_progress=progress)


    def _update_treeview_value(self, page, reg_addr, hex_value, set_sync=None):
        """
        Updates a specific register value in the Treeview.

        Args:
            page (int): The register page.
            reg_addr (int): The register address.
            hex_value (str): The new value formatted as a hex string.
            set_sync (str): If not None, sets the 'toSync' column to this value.
        """
        page_text = f'Page {page:d}' if page >= 0 else 'Standard regs'
        reg_text = f'0x{reg_addr:02X}'
        is_updated = False

        for page_item in self.registers.treeview.get_children():
            if is_updated:
                break
            if self.registers.treeview.item(page_item, "text") == page_text:
                for reg_item in self.registers.treeview.get_children(page_item):
                    if self.registers.treeview.item(reg_item, "text") == reg_text:
                        self.registers.treeview.set(reg_item, column='value', value=hex_value)

                        if set_sync is not None:
                            self.registers.treeview.set(reg_item, column='toSync', value=set_sync)

                        is_updated = True
                        break


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
        result = False
        if col_key == 'value':
            access_rights = str(row_data.get('access', '')).lower()
            if 'w' in access_rights:
                result = True
        return result


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
                            # Just check if it's valid hex
                            int(input_str, 16)
                            result = True
                        except ValueError:
                            result = False
            else:
                result = False
        return result


    def _on_cell_edit(self, row_id, _col_key, _old_val, _new_val, _row_data): # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        """
        Callback executed after a cell has been edited.
        Validates the input value and limits.

        Args:
            row_id (str): The ID of the edited row.
            col_key (str): The key of the edited column.
            old_val (any): The previous value.
            new_val (any): The new value set in the cell.
            row_data (dict): Dictionary of all values in the row.
        """
        result = False
        try: # pylint: disable=too-many-nested-blocks
            # 1. Retrieve info about Page and Register
            parent_id = self.registers.treeview.parent(row_id)
            if parent_id:
                parent_text = self.registers.treeview.item(parent_id, 'text')
                if 'Page' in parent_text:
                    page = int(parent_text.split(' ')[1])
                else:
                    page = -1 # Standard regs

                reg_text = self.registers.treeview.item(row_id, 'text')
                reg_addr = int(reg_text, 16)

                # 2. Determine limits (min/max OR valuelist)
                min_val = 0x00
                max_val = 0xFF
                allowed_values = None # Will be a set if valuelist exists

                reg_info = {}
                if page in self.registers_data and reg_addr in self.registers_data[page]:
                    reg_info = self.registers_data[page][reg_addr]

                    # Check for valuelist override
                    if 'valuelist' in reg_info and reg_info['valuelist']:
                        allowed_values = set()
                        raw_vl = reg_info['valuelist']
                        # Parse valuelist similar to _create_dynamic_widgets logic
                        if isinstance(raw_vl, dict):
                            for k in raw_vl.keys():
                                try:
                                    allowed_values.add(int(str(k), 0))
                                except (ValueError, TypeError):
                                    pass
                        elif isinstance(raw_vl, list):
                            for idx, item in enumerate(raw_vl):
                                if isinstance(item, dict):
                                    val = item.get('value')
                                    if val is not None:
                                        try:
                                            allowed_values.add(int(str(val), 0))
                                        except (ValueError, TypeError):
                                            pass
                                else:
                                    # Simple list item, index is the value
                                    allowed_values.add(idx)
                    else:
                        # Fallback to Min/Max if no valuelist

                        # Calculate width limit first
                        width_limit = 0xFF
                        if 'width' in reg_info and reg_info['width'] is not None:
                            try:
                                w_val = int(str(reg_info['width']), 0)
                                if 0 <= w_val < 8:
                                    width_limit = (1 << w_val) - 1
                            except (ValueError, TypeError):
                                pass

                        if 'min' in reg_info and reg_info['min'] is not None:
                            try:
                                min_val = int(str(reg_info['min']), 0)
                            except (ValueError, TypeError):
                                pass

                        if 'max' in reg_info and reg_info['max'] is not None:
                            try:
                                max_val = int(str(reg_info['max']), 0)
                            except (ValueError, TypeError):
                                pass

                        # Apply width limit to upper bound
                        max_val = min(max_val, width_limit)

                # 3. Validate input value
                input_str = str(_new_val).strip()
                if input_str and input_str.lower().startswith('0x'):
                    val_int = None
                    try:
                        val_int = int(input_str, 16)

                        is_valid = False
                        if allowed_values is not None:
                            # If valuelist exists, value must be in list AND within byte range
                            if val_int in allowed_values and 0x00 <= val_int <= 0xFF:
                                is_valid = True
                        else:
                            # Standard Min/Max check
                            if min_val <= val_int <= max_val:
                                is_valid = True

                        if is_valid:
                            # 5. Update Value and Sync Marker
                            formatted_hex = f'0x{val_int:02X}'

                            self.registers.treeview.set(row_id, column='value', value=formatted_hex)
                            value_changed = True
                            try:
                                if int(str(_old_val), 16) == val_int:
                                    value_changed = False
                            except (ValueError, TypeError):
                                pass

                            if value_changed:
                                self.registers.treeview.set(row_id, column='toSync', value=vscp.mdf.sync_write) # pylint: disable=line-too-long
                                if reg_info:
                                    reg_info['value'] = formatted_hex
                                    reg_info['to_sync'] = vscp.mdf.sync_write

                                # Refresh info panel if current selection matches edited cell
                                # This handles immediate update of the right panel when treeview changes # pylint: disable=line-too-long
                                if row_id == self.registers.treeview.focus():
                                    self._update_registers_info(None)

                            result = formatted_hex
                    except ValueError:
                        pass # result remains False
        except Exception: # pylint: disable=broad-except
            pass # result remains False

        return result


    def _update_registers_info(self, _): # pylint: disable=too-many-branches, too-many-locals
        """
        Updates the information widget based on the selected register.

        Retrieves details for the selected item in the treeview and updates
        the ScrollableInfoTable with properly formatted data.

        Args:
            _: The event object (unused).
        """
        def format_hex(value):
            """Helper to safely format a value to HEX string. Returns None if value is missing."""
            if value is None or value == "":
                return None
            try:
                # Handle int or string input (e.g. "0x10" or 16)
                if isinstance(value, str):
                    val_int = int(value, 0) # Handles "0x" prefix automatically
                else:
                    val_int = int(value)
                return f"0x{val_int:02X}"
            except (ValueError, TypeError):
                return str(value)

        self.registers_info.update_data({})
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self.dynamic_frame.grid_remove()

        try:
            item = self.registers.treeview.focus()
            item_dict = self.registers.treeview.item(item)
            parent_id = self.registers.treeview.parent(item)

            if parent_id:
                parent_text = self.registers.treeview.item(parent_id, 'text')

                if 'Page' in parent_text:
                    page = int(parent_text.split(' ')[1])
                else:
                    page = -1 # Standard regs

                register = int(item_dict['text'], 16)
                data = self.registers_data[page][register]

                # Prepare rows
                rows = [
                    ("<b>Page</b>:", str(page) if page >= 0 else "0"),
                    ("<b>Register</b>:", f"0x{register:02X}")
                ]

                if data.get('access'):
                    rows.append(("<b>Access</b>:", str(data.get('access'))))

                if data.get('width') is not None:
                    rows.append(("<b>Width</b>:", str(data.get('width'))))

                if (min_val := format_hex(data.get('min'))) is not None:
                    rows.append(("<b>Min value</b>:", min_val))

                if (max_val := format_hex(data.get('max'))) is not None:
                    rows.append(("<b>Max value</b>:", max_val))

                if (default_val := format_hex(data.get('default'))) is not None:
                    rows.append(("<b>Default value</b>:", default_val))

                if (curr_val := format_hex(data.get('value'))) is not None:
                    rows.append(("<b>Value</b>:", curr_val))

                # Prepare dictionary for ScrollableInfoTable
                table_data = {
                    "header": '<b>' + data.get('name', '') + '</b>',
                    "rows": rows,
                    "footer": data.get('description', '')
                }

                self.registers_info.update_data(table_data)

                # --- Create Dynamic Widgets (ComboBox/CheckBoxes) ---
                self._create_dynamic_widgets(data, page, register)

        except (ValueError, KeyError, IndexError):
            pass


    def _create_dynamic_widgets(self, data, page, register): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Creates dynamic widgets (ComboBox for valuelist, CheckBoxes for bits)
        based on the register data.

        Args:
            data (dict): The data dictionary for the specific register from MDF.
            page (int): The page number of the register.
            register (int): The address of the register.
        """
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        self.dynamic_frame.grid_remove()

        current_val_int = 0
        try:
            current_val_int = int(str(data.get('value', '0')), 0)
        except (ValueError, TypeError):
            pass

        has_dynamic_content = False

        # 1. Valuelist (ComboBox)
        if 'valuelist' in data and data['valuelist']:
            # Assume valuelist is a dict {val: {'name': '...', 'description': '...'}}
            # or map where we can extract name and value.
            values_map = {} # Name -> Value
            name_desc_map = {} # Name -> Description
            combo_values = []

            current_selection = ""

            # Prepare iterable items to handle both dict and list
            raw_valuelist = data['valuelist']
            valuelist_items = []

            if isinstance(raw_valuelist, dict):
                valuelist_items = raw_valuelist.items()
            elif isinstance(raw_valuelist, list):
                # If list, we assume it contains dicts with 'value' key,
                # or we treat index as value if simple strings.
                for idx, item in enumerate(raw_valuelist):
                    if isinstance(item, dict):
                        # Try to get explicit value, else skip or use index?
                        val = item.get('value')
                        if val is not None:
                            valuelist_items.append((val, item))
                    else:
                        # Assume simple list of names corresponding to 0, 1, 2...
                        valuelist_items.append((idx, {'name': str(item)}))

            for val_key, val_data in valuelist_items:
                try:
                    val_int = int(str(val_key), 0)

                    # Handle if val_data is just a string (name) or a dict
                    if isinstance(val_data, dict):
                        name = val_data.get('name', str(val_int))
                        desc = val_data.get('description', '')
                    else:
                        name = str(val_data)
                        desc = ''

                    values_map[name] = val_int
                    name_desc_map[name] = desc
                    combo_values.append(name)

                    if val_int == current_val_int:
                        current_selection = name
                except (ValueError, TypeError):
                    continue

            if combo_values:
                # Callback for ComboBox
                def on_combo_change(choice):
                    if choice in values_map:
                        new_val = values_map[choice]
                        self._update_register_value_from_widget(page, register, new_val)

                combobox = ctk.CTkComboBox(self.dynamic_frame,
                                           values=combo_values,
                                           command=on_combo_change,
                                           state="readonly",
                                           width=330,
                                           bg_color=self.container_bg_color,
                                           fg_color=self.container_bg_color)
                combobox.pack(side='top', fill='x', padx=5, pady=5)

                if current_selection:
                    combobox.set(current_selection)
                    if current_selection in name_desc_map and name_desc_map[current_selection]:
                        ToolTip(combobox, name_desc_map[current_selection])
                elif combo_values:
                    combobox.set(combo_values[0]) # Default first if no match

                has_dynamic_content = True

        # 2. Bits (CheckBoxes)
        elif 'bits' in data and data['bits']:
            width = 8
            if data.get('width'):
                try:
                    width = int(data['width'])
                except (ValueError, TypeError):
                    pass

            # Normalize bits to dictionary {index: info} to handle lists and dicts
            bits_map = {}
            raw_bits = data['bits']

            if isinstance(raw_bits, dict):
                for k, v in raw_bits.items():
                    try:
                        bits_map[int(k)] = v
                    except (ValueError, TypeError):
                        pass
            elif isinstance(raw_bits, list):
                for idx, item in enumerate(raw_bits):
                    # Assume list index corresponds to bit index
                    bits_map[idx] = item

            # Create checkboxes from MSB (width-1) down to LSB (0)
            for i in range(width - 1, -1, -1):
                # Lookup in normalized map (handles int keys from normalization)
                bit_info = bits_map.get(i)

                if bit_info:
                    # Handle if bit_info is just a string or dict
                    if isinstance(bit_info, dict):
                        name = bit_info.get('name', f'Bit {i}')
                        desc = bit_info.get('description', '')
                    else:
                        name = str(bit_info)
                        desc = ''

                    is_checked = (current_val_int >> i) & 1

                    chk_var = ctk.IntVar(value=is_checked)

                    def on_chk_cmd(var=chk_var, bit_idx=i):
                        new_bit_val = var.get()
                        try:
                            curr = int(str(self.registers_data[page][register].get('value', '0')), 0) # pylint: disable=line-too-long
                        except: # pylint: disable=bare-except
                            curr = 0

                        if new_bit_val:
                            new_reg_val = curr | (1 << bit_idx)
                        else:
                            new_reg_val = curr & ~(1 << bit_idx)

                        self._update_register_value_from_widget(page, register, new_reg_val)

                    chk = ctk.CTkCheckBox(self.dynamic_frame, text=name,
                                          variable=chk_var,
                                          command=on_chk_cmd,
                                          onvalue=1, offvalue=0,
                                          bg_color=self.container_bg_color)
                    chk.pack(side='top', anchor='w', padx=5, pady=(1, (1 if i > 0 else 5)))

                    if desc:
                        ToolTip(chk, desc)

                    has_dynamic_content = True

        # Only pack the frame if there is content
        if has_dynamic_content:
            self.dynamic_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)


    def _update_register_value_from_widget(self, page, register, new_int_value):
        """
        Updates the register value from a dynamic widget interaction.
        Updates internal data, treeview, and the info panel.
        """
        hex_val = f'0x{new_int_value:02X}'

        # 1. Update internal data
        if page in self.registers_data and register in self.registers_data[page]:
            self.registers_data[page][register]['value'] = hex_val
            self.registers_data[page][register]['to_sync'] = vscp.mdf.sync_write

        # 2. Update Treeview
        self._update_treeview_value(page, register, hex_val, set_sync=vscp.mdf.sync_write)

        # 3. Refresh Info Panel Text (specifically the "Value" field)
        # Re-fetch data for panel
        data = self.registers_data[page][register]

        # Helper format (duplicate logic, could be method)
        def format_hex(value):
            if value is None or value == "":
                return None
            try:
                if isinstance(value, str):
                    val_int = int(value, 0)
                else:
                    val_int = int(value)
                return f"0x{val_int:02X}"
            except: # pylint: disable=bare-except
                return str(value)

        rows = [
            ("Page:", str(page)),
            ("Register:", f"0x{register:02X}")
        ]
        if data.get('access'):
            rows.append(("Access:", str(data.get('access'))))
        if data.get('width') is not None:
            rows.append(("Width:", str(data.get('width'))))
        if (min_val := format_hex(data.get('min'))) is not None:
            rows.append(("Min:", min_val))
        if (max_val := format_hex(data.get('max'))) is not None:
            rows.append(("Max:", max_val))
        if (default_val := format_hex(data.get('default'))) is not None:
            rows.append(("Default val.:", default_val))
        if (curr_val := format_hex(data.get('value'))) is not None:
            rows.append(("Value:", curr_val))

        table_data = {
            "header": data.get('name', ''),
            "rows": rows,
            "footer": data.get('description', '')
        }
        self.registers_info.update_data(table_data)


    def _show_menu(self, event, menu): # pylint: disable=too-many-locals, too-many-branches
        """
        Display the context menu on right-click.

        Args:
            event: The mouse event triggering the menu.
            menu: The menu widget to display.
        """
        self.selected_row_id = self.registers.treeview.identify('row', event.x, event.y)

        # Cleanup any existing menu state
        self._close_popup()

        selection = self.registers.treeview.selection()

        # Filter selection to include only registers (items that have a parent)
        selected_registers = [item for item in selection if self.registers.treeview.parent(item)]

        # 1. Read all registers - always active
        self.dropdown_bt_read_all.configure(state='normal')

        # 2. Read selected registers - active only if actual registers are selected
        state_read_sel = 'normal' if len(selected_registers) > 0 else 'disabled'
        self.dropdown_bt_read_selected.configure(state=state_read_sel)

        # --- Check Modification Status via registers_data ---
        any_modified = False
        selected_modified = False

        # Check globally modified
        for page_data in self.registers_data.values():
            for reg_data in page_data.values():
                if reg_data.get('to_sync') == vscp.mdf.sync_write:
                    any_modified = True
                    break
            if any_modified:
                break

        # Check selected modified
        if selected_registers:
            for item_id in selected_registers:
                parent_id = self.registers.treeview.parent(item_id)
                if not parent_id:
                    continue

                parent_text = self.registers.treeview.item(parent_id, 'text')
                # Parse Page
                if 'Page' in parent_text:
                    try:
                        page = int(parent_text.split(' ')[1])
                    except IndexError:
                        continue
                else:
                    page = -1

                item_text = self.registers.treeview.item(item_id, 'text')
                try:
                    addr = int(item_text, 16)
                    if page in self.registers_data and addr in self.registers_data[page]:
                        if self.registers_data[page][addr].get('to_sync') == vscp.mdf.sync_write:
                            selected_modified = True
                            break
                except ValueError:
                    continue

        # 3. Write all registers - active only if any register is modified
        state_write_all = 'normal' if any_modified else 'disabled'
        self.dropdown_bt_write_all.configure(state=state_write_all)

        # 4. Write selected registers - active only if any selected register is modified
        state_write_sel = 'normal' if selected_modified else 'disabled'
        self.dropdown_bt_write_selected.configure(state=state_write_sel)

        if '' != self.selected_row_id:
            menu.popup(event.x_root, event.y_root)
            # Bind click event to parent window to handle "click outside"
            self._click_bind_id = self.widget.winfo_toplevel().bind("<Button-1>", self._close_popup, "+") # pylint: disable=line-too-long


    def _close_popup(self, event=None):
        """
        Close the popup menu and unbind click event.
        Checks if click was inside the popup before closing.
        """
        if event:
            # If click occurred inside the dropdown frame, do not close
            try:
                if str(event.widget).startswith(str(self.dropdown.frame)):
                    return
            except AttributeError:
                pass

        try:
            self.dropdown.withdraw()
        except AttributeError:
            pass

        try:
            self.dropdown.grab_release()
        except AttributeError:
            pass

        if hasattr(self, '_click_bind_id'):
            try:
                self.widget.winfo_toplevel().unbind("<Button-1>", self._click_bind_id)
            except Exception: # pylint: disable=broad-exception-caught
                pass
            del self._click_bind_id


    def _bt_read_all_registers(self):
        """Callback for 'Read all registers'."""
        self._close_popup()
        tae.async_execute(self._read_all_registers(), wait=False, visible=False, pop_up=False, callback=None, master=self) # pylint: disable=line-too-long


    def _bt_read_selected_registers(self):
        """Callback for 'Read selected registers'."""
        self._close_popup()
        tae.async_execute(self._read_selected_registers(), wait=False, visible=False, pop_up=False, callback=None, master=self) # pylint: disable=line-too-long


    def _bt_write_selected_registers(self):
        """Callback for 'Write selected registers'."""
        self._close_popup()
        tae.async_execute(self._write_selected_registers(), wait=False, visible=False, pop_up=False, callback=None, master=self) # pylint: disable=line-too-long


    def _bt_write_all_registers(self):
        """Callback for 'Write all registers'."""
        self._close_popup()
        tae.async_execute(self._write_all_registers(), wait=False, visible=False, pop_up=False, callback=None, master=self) # pylint: disable=line-too-long
