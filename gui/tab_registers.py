"""
Registers Tab Module.

This module provides the `RegistersTab` class for the Node Configuration window.
It handles displaying, reading, and writing VSCP registers using a Treeview.

@file tab_registers.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import customtkinter as ctk
import tk_async_execute as tae
import vscp
from gui.common import update_progress
from .treeview import CTkTreeview
from .popup import CTkFloatingWindow


class RegistersTab(ctk.CTkFrame): # pylint: disable=too-many-instance-attributes, too-many-ancestors
    """
    Tab for viewing and editing VSCP registers.

    Displays register data in a treeview and shows detailed information about
    the selected register in a side panel.
    """

    def __init__(self, parent, node_id: int):
        # pylint: disable=line-too-long
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
        self.selected_row_id = ''
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

        self.registers.enable_cell_editing(columns=['value'],
                                           edit_callback=self._on_cell_edit,
                                           permission_callback=self._can_edit_cell,
                                           input_validation=self._validate_input)

        self.registers.treeview.bind('<<TreeviewSelect>>', self._update_registers_info)
        # self.registers.treeview.bind('<Double-Button-1>', self.item_deselect)
        self.registers.treeview.bind('<Button-3>', lambda event: self._show_menu(event, self.dropdown))
        # self.registers.treeview.bind('<<TreeviewSelect>>', self._parse_msg_data)

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

        font = ctk.CTkFont(family='TkDefaultFont', size=15)
        bold_font = ctk.CTkFont(family='TkDefaultFont', size=15, weight='bold')
        temp_fg_color = tuple(self._fg_color) if isinstance(self._fg_color, list) else self._fg_color
        self.registers_info = ctk.CTkTextbox(self.widget, font=font, width=250, border_spacing=1, fg_color=temp_fg_color)
        self.registers_info.pack(padx=(5, 0), pady=0, side='right', anchor='ne', fill='y', expand=False)
        self.registers_info.bind("<Button-1>", lambda e: 'break')
        self.registers_info.configure(state='disabled')
        self.registers_info.tag_config('bold', font=bold_font)

        # Start async read of real register values
        tae.async_execute(self._prepare_registers_data(), wait=False, visible=False, pop_up=False, callback=None, master=self)
        # pylint: enable=line-too-long


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
            self.registers.insert_items(result)


    async def _execute_read_registers(self, registers_map: dict, start_progress: float = 0.0) -> None: # pylint: disable=line-too-long, too-many-locals, too-many-branches, too-many-statements
        """
        Helper method to execute read operations for a provided map of registers.
        Handles node probing, chunking, reading from VSCP, and UI updates.

        Args:
            registers_map (dict): A dictionary where keys are page numbers (int)
                                  and values are lists of register addresses (int) to read.
                                  Example: {0: [1, 2, 3], 1: [0, 10]}
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

            # Logic to count chunks of contiguous registers (max size 4)
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

        # Calculate progress step (remaining progress / total chunks)
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
                                  Example: {0: {1: 0x10, 2: 0x20}}
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

            # Parse Page
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

            # Parse Page
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

            # Check sync status and add to map
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

        # Find the parent item (Page)
        for page_item in self.registers.treeview.get_children():
            if is_updated:
                break
            if self.registers.treeview.item(page_item, "text") == page_text:
                # Find the child item (Register)
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
            # Check access rights from row_data
            # row_data contains keys defined in header:
            # 'address', 'access', 'value', 'toSync', 'name'
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


    def _on_cell_edit(self, row_id, _col_key, _old_val, _new_val, _row_data): # pylint: disable=too-many-branches, too-many-statements
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

                # 2. Determine limits (min/max)
                # Default range 0x00 - 0xFF
                min_val = 0x00
                max_val = 0xFF

                reg_info = {}
                if page in self.registers_data and reg_addr in self.registers_data[page]:
                    reg_info = self.registers_data[page][reg_addr]

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
                # 3. Validate input value
                input_str = str(_new_val).strip()
                if input_str and input_str.lower().startswith('0x'):
                    val_int = None
                    try:
                        val_int = int(input_str, 16)

                        if min_val <= val_int <= max_val:
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

                            result = formatted_hex
                    except ValueError:
                        pass # result remains False
        except Exception: # pylint: disable=broad-except
            pass # result remains False

        return result


    def _update_registers_info(self, _):
        """
        Updates the information textbox based on the selected register.

        Retrieves details for the selected item in the treeview and displays
        them in the side panel.

        Args:
            _: The event object (unused).
        """
        try:
            item = self.registers.treeview.focus()
            item_dict = self.registers.treeview.item(item)
            parent_id = self.registers.treeview.parent(item)
            self.registers_info.configure(state='normal')
            self.registers_info.delete("0.0", "end")
            if parent_id:
                parent_text = self.registers.treeview.item(parent_id, 'text')
                page = int(parent_text.split(' ')[1])
                register = int(item_dict['text'], 16)
                data = self.registers_data[page][register]

                self.registers_info.insert("end", data['name'] + "\n", 'bold')
                self.registers_info.insert("end", "\n")
                self.registers_info.insert("end", "Page:     " + str(page) + "\n")
                self.registers_info.insert("end", "Register: " + f"0x{register:02X} ({register})" + "\n") # pylint: disable=line-too-long
                self.registers_info.insert("end", "Access:   " + data['access'] + "\n")
                self.registers_info.insert("end", "Value:    " + f"0x{data['value']:02X} ({data['value']})" + "\n") # pylint: disable=line-too-long
                self.registers_info.insert("end", "\n")
                self.registers_info.insert("end", data['description'])

            self.registers_info.configure(state='disabled')
        except (ValueError, KeyError, IndexError):
            pass


    def _show_menu(self, event, menu):
        """
        Display the context menu on right-click.

        Args:
            event: The mouse event triggering the menu.
            menu: The menu widget to display.
        """
        self.selected_row_id = self.registers.treeview.identify('row', event.x, event.y)

        # Cleanup any existing menu state
        self._close_popup()

        # Determine status to enable/disable specific options
        selection = self.registers.treeview.selection()

        # Filter selection to include only registers (items that have a parent)
        # Page items have no parent (parent returns '')
        selected_registers = [item for item in selection if self.registers.treeview.parent(item)]

        # 1. Read all registers - always active
        self.dropdown_bt_read_all.configure(state='normal')

        # 2. Read selected registers - active only if actual registers are selected
        state_read_sel = 'normal' if len(selected_registers) > 0 else 'disabled'
        self.dropdown_bt_read_selected.configure(state=state_read_sel)

        # 3. Write all registers - active only if any register is modified
        # Get all modified cells: list of (row_id, column_key) tuples
        modified_cells = self.registers.get_modified_cells()
        state_write_all = 'normal' if len(modified_cells) > 0 else 'disabled'
        self.dropdown_bt_write_all.configure(state=state_write_all)

        # 4. Write selected registers - active only if any selected register is modified
        # We need to check if any of the selected row IDs are present in the modified cells list
        modified_row_ids = {cell[0] for cell in modified_cells} # Extract just row IDs from (id, col) tuples # pylint: disable=line-too-long
        selected_row_ids = set(selection)

        # Intersection determines if any selected row is also modified
        is_any_selected_modified = not modified_row_ids.isdisjoint(selected_row_ids)
        state_write_sel = 'normal' if is_any_selected_modified else 'disabled'
        self.dropdown_bt_write_selected.configure(state=state_write_sel)

        if '' != self.selected_row_id:
            menu.popup(event.x_root, event.y_root)
            # Bind click event to parent window to handle "click outside"
            # Using add="+" to avoid overwriting existing bindings on the toplevel
            self._click_bind_id = self.widget.winfo_toplevel().bind("<Button-1>", self._close_popup, "+") # pylint: disable=line-too-long


    def _close_popup(self, event=None):
        """
        Close the popup menu and unbind click event.
        Checks if click was inside the popup before closing.
        """
        if event:
            # If click occurred inside the dropdown frame, do not close
            # This allows buttons inside the dropdown to function
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
