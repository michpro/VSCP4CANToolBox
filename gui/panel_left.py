# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-ancestors
# pylint: disable=line-too-long

import os
import re
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
    def __init__(self, parent):
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
        tae.async_execute(vscp.send_host_datetime(), visible=False)


    def button1_cb(self): # TODO remove
        # tae.async_execute(vscp.set_nickname(0x02, 0x0A), visible=False)
        # tae.async_execute(vscp.set_nickname(0x0A, 0x02), visible=False)
        # tae.async_execute(vscp.scan(0, 20), visible=False)
        pass


class Neighbourhood(ctk.CTkFrame):
    def __init__(self, parent):
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
    def __init__(self, parent):
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
        input_str = self.min_id_var.get()
        if input_str.lower().startswith('0x'):
            self.min_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _min_id_focus_out(self, _): # TODO implement
        pass
        # self.max_range[0] = int(self.min_id_var.get(), 0)
        # print('max range', self.max_range)


    def _validate_start(self, input_str):
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
        input_str = self.max_id_var.get()
        if input_str.lower().startswith('0x'):
            self.max_id_var.set(input_str[:2].lower() + input_str[2:].upper())


    def _max_id_focus_out(self, _): # TODO implement
        pass
        # self.min_range[1] = int(self.max_id_var.get(), 0)
        # print('min range', self.min_range)


    def _validate_stop(self, input_str):
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
        tae.async_execute(self._call_scan(), visible=False)


    async def _call_scan(self):
        min_id = int(self.min_id_var.get(), 0)
        max_id = int(self.max_id_var.get(), 0)
        nodes = await vscp.scan(min_id, max_id)
        neighbours_handle().delete_all_items()
        if 0 < nodes:
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
                neighbours_handle().insert(data)


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
        self.l_min_id.configure(state=state)
        self.min_id.configure(state=state)
        self.l_max_id.configure(state=state)
        self.max_id.configure(state=state)
        self.button_scan.configure(state=state)
        # self.toggle.configure(state=state)


class Neighbours(ctk.CTkFrame):
    def __init__(self, parent):
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
        self.dropdown_bt_firmware = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                  text="Upload Firmware", command=self._firmware_upload)
        self.dropdown_bt_firmware.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_configure = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                   text="Configure Node", command=self._configure_node)
        self.dropdown_bt_configure.pack(expand=True, fill="x", padx=0, pady=0)
        self.dropdown_bt_chg_node_id = ctk.CTkButton(self.dropdown.frame, border_spacing=0, corner_radius=0,
                                                   text="Change Node ID", command=self._change_node_id)
        self.dropdown_bt_chg_node_id.pack(expand=True, fill="x", padx=0, pady=0)
        # TODO remove
        # data = []
        # for idx in range(1, 4):
        #     node_id = f"0x{idx:02X}"
        #     entry = {'text': node_id,
        #                 'child': [{'text': 'GUID:', 'values': f'FA:FA:FA:{idx:02d}'}, 
        #                           {'text': 'MDF:',  'values': f'http://vscp.local/mdf/xxx{idx}.mdf'}
        #                          ]
        #             }
        #     data.append(entry)
        # self.insert(data)


    def insert(self, row_data):
        self.neighbours.insert_items(row_data)


    def _item_deselect(self, event):
        selected_rows = self.neighbours.treeview.selection()
        row_clicked = self.neighbours.treeview.identify('row', event.x, event.y)
        index = selected_rows.index(row_clicked) if row_clicked in selected_rows else -1
        if -1 < index:
            self.neighbours.treeview.selection_remove(selected_rows[index])


    def delete_all_items(self) -> None:
        for item in self.neighbours.treeview.get_children():
            self.neighbours.treeview.delete(item)


    def _show_menu(self, event, menu):
        self.selected_row_id = self.neighbours.treeview.identify('row', event.x, event.y)
        try:
            if '' != self.selected_row_id:
                menu.popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


    def _set_menu_items_state(self, state):
        self.dropdown_bt_firmware.configure(state=state)
        self.dropdown_bt_configure.configure(state=state)
        self.dropdown_bt_chg_node_id.configure(state=state)


    def _get_node_id(self) -> int:
        parent_id = self.neighbours.treeview.parent(self.selected_row_id)
        text = self.neighbours.treeview.item(parent_id)['text'] if parent_id else   \
            self.neighbours.treeview.item(self.selected_row_id)['text']
        try:
            result = int(text, 0)
        except ValueError:
            result = -1
        return result


    def _get_mdf_link(self) -> str:
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
        title = 'Uploading new firmware'
        message = f'Are you sure you want to upload new firmware to node 0x{node_id:02X}?'
        msg = CTkMessagebox(title=title, message=message, icon='question',
                            option_1='No', option_2='Yes')
        response = msg.get()
        return 'Yes' == str(response)


    def _firmware_upload(self):
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
                        tae.async_execute(vscp.firmware_upload(node_id, fw_data), visible=False)
            else:
                CTkMessagebox(title='Error', message='Firmware file not selected!!!', icon='cancel')
        else:
            CTkMessagebox(title='Error', message='Undefined Node ID!!!', icon='cancel')


    def _get_local_mdf(self):
        CTkMessagebox(title='Info', message='Not implemented yet')
        return ''


    def _configure_node(self):
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
            mdf = self._get_local_mdf() # pylint: disable=assignment-from-none
        if mdf:
            vscp.mdf.parse(mdf)
            self.config_window = NodeConfiguration(self, node_id, guid)
            self._set_menu_items_state('disabled')
        else:
            CTkMessagebox(title='Error', message='No valid MDF file for the selected node!!!', icon='cancel')


    def _change_node_id(self):
        CTkMessagebox(title='Info', message='Not implemented yet')


    def close_node_configuration(self):
        try:
            self.config_window.window.destroy()
        except: # pylint: disable=bare-except
            pass
        finally:
            self.config_window = None
            self._set_menu_items_state('normal')
