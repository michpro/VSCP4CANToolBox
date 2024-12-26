# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-ancestors

import tk_async_execute as tae
import customtkinter as ctk
import vscp
from .treeview import CTkTreeview
from .common import add_set_state_callback, call_set_scan_widget_state,     \
                    add_neighbours_handle, neighbours_handle
# from .popup import CTkFloatingWindow

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

        header = [('node', 'Node', 75, 75, 'center', 'w'),
                  ('description', '', 356, 356, 'center', 'w'),
                 ]
        # data = [{'text': '►0xAA◄',
        #          'child': [{'text': 'GUID:', 'values': ['FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:FF:01']}, 
        #                    {'text': 'MDF:', 'values': ['vscp.local/mdf/mdf_file.xml']},
        #                    ]},
        #         {'text': '0x0A',
        #          'child': [{'text': 'GUID:', 'values': ['AA:AA:AA:AA:AA:AA:AA:AA:AA:AA:AA:AA:AA:AA:AA:AA']}, 
        #                    {'text': 'MDF:', 'values': ['vscp.local/mdf/mdf_file.xml']}]}
        #        ]
        self.widget = ctk.CTkFrame(parent, fg_color='transparent')
        self.widget.pack(padx=0, pady=5, side='top', anchor='nw', fill='both', expand=True)
        # self.neighbours = CTkTreeview(self.widget, header, data, xscroll=False)
        self.neighbours = CTkTreeview(self.widget, header, xscroll=False)
        self.neighbours.pack(padx=0, pady=0, fill='both', expand=True)
        self.neighbours.treeview.bind('<Double-Button-1>', self.item_deselect)
        # print(len(self.neighbours.treeview.get_children()))
        # self.neighbours.delete_all_items()
        # print(len(self.neighbours.treeview.get_children()))
        # for item in self.neighbours.treeview.get_children():
        #     print(self.neighbours.treeview.delete(item))


    def insert(self, row_data):
        self.neighbours.insert_items(row_data)


    def item_deselect(self, event):
        selected_rows = self.neighbours.treeview.selection()
        row_clicked = self.neighbours.treeview.identify('row', event.x, event.y)
        index = selected_rows.index(row_clicked) if row_clicked in selected_rows else -1
        if -1 < index:
            self.neighbours.treeview.selection_remove(selected_rows[index])


    def delete_all_items(self) -> None:
        for item in self.neighbours.treeview.get_children():
            self.neighbours.treeview.delete(item)
