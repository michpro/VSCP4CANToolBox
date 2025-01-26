# pylint: disable=line-too-long, missing-module-docstring, missing-class-docstring, missing-function-docstring
# pylint: disable=too-many-ancestors


import os
import pprint # TODO remove
import customtkinter as ctk
import vscp
from .treeview import CTkTreeview


def new_tag_config(self, tagName, **kwargs): # pylint: disable=invalid-name
    return self._textbox.tag_config(tagName, **kwargs) # pylint: disable=protected-access


# workaround for banning 'font' parameter in the 'tag_config' function
ctk.CTkTextbox.tag_config = new_tag_config


class NodeConfiguration: # pylint: disable=too-many-instance-attributes, too-few-public-methods
    def __init__(self, parent, node_id: int, guid: str):
        super().__init__()
        self.window = ctk.CTkToplevel(parent)
        self.width = 1050
        self.height = 650
        self.parent = parent
        self.node_id = node_id

        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icon_path = os.path.join(icon_dir, 'vscp_logo.ico')

        x = int((self.window.winfo_screenwidth() / 2) - (self.width / 2))
        y = int((0.95 * (self.window.winfo_screenheight() / 2)) - (self.height / 2))
        self.window.title(f'VSCP ToolBox - Node 0x{self.node_id:02X} GUID: {guid} Configuration')
        self.window.geometry(f'{self.width}x{self.height}+{x}+{y}')
        self.window.minsize(width=self.width, height=self.height)
        self.window.resizable(width=False, height=True)
        self.window.protocol('WM_DELETE_WINDOW', self._window_exit)
        self.window.after(250, lambda: self.window.iconbitmap(icon_path)) # show icon workaround

        self.config_panel = ctk.CTkFrame(self.window, corner_radius=0)
        self.config_panel.pack(fill='both', expand=True)

        self.config = ConfigPanel(self.config_panel)

        self.info_panel = ctk.CTkFrame(self.config_panel, height=150)
        self.info_panel.pack(padx=5, pady=(0, 5), side='top', anchor='s', fill='both', expand=False)

        self.info = InfoPanel(self.info_panel)
        self.info.display({**vscp.mdf.get_module_info(), **vscp.mdf.get_boot_algorithm()})


    def bring_to_front(self):
        self.window.attributes('-topmost', True)
        self.window.focus_force()
        self.window.after(800, lambda: self.window.attributes('-topmost', False))


    def _window_exit(self):
        self.parent.close_node_configuration()


class InfoPanel(ctk.CTkFrame):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(self.parent)

        font = ctk.CTkFont(family='TkDefaultFont', size=15)
        bold_font = ctk.CTkFont(family='TkDefaultFont', size=15, weight='bold')
        self.module_info = ctk.CTkTextbox(self.parent, font=font, border_spacing=1, fg_color=self._fg_color)
        self.module_info.pack(padx=(5, 5), pady=(5, 5), side='top', anchor='nw', fill='both', expand=True)
        self.module_info.bind("<Button-1>", 'break')
        self.module_info.configure(state='disabled')
        self.module_info.tag_config('bold', font=bold_font)


    def display(self, data: dict) -> None:
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
    def __init__(self, parent):
        super().__init__(parent)

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

        self.registers = RegistersTab(self.widget.tab(self.tabs_names[0]))


class RegistersTab(ctk.CTkFrame):
    def __init__(self, parent):
        self.parent = parent
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
        # self.registers.treeview.bind('<Double-Button-1>', self.item_deselect)
        # self.registers.treeview.bind('<Button-3>', lambda event: self._show_menu(event, self.dropdown))
        # self.registers.treeview.bind('<<TreeviewSelect>>', self._parse_msg_data)

        font = ctk.CTkFont(family='TkDefaultFont', size=15)
        bold_font = ctk.CTkFont(family='TkDefaultFont', size=15, weight='bold')
        self.registers_info = ctk.CTkTextbox(self.widget, font=font, width=250, border_spacing=1, fg_color=self._fg_color)
        self.registers_info.pack(padx=(5, 0), pady=0, side='right', anchor='ne', fill='y', expand=False)
        self.registers_info.bind("<Button-1>", 'break')
        self.registers_info.configure(state='disabled')
        self.registers_info.tag_config('bold', font=bold_font)

        self.registers_data = vscp.mdf.get_registers_info()
        self._insert_registers_data()

        # pp = pprint.PrettyPrinter(indent=2, width=160) # TODO remove
        # pp.pprint(self.registers_data)


    def _insert_registers_data(self):
        result = []
        for page, registers in self.registers_data.items():
            child = []
            for register, data in registers.items():
                row = {'text': f'0x{register:02X}', 'values': [data['access'], data['value'], data['to_sync'], data['name']]}
                child.append(row)
            text = f'Page {page:d}' if 0 <= page else 'Standard regs'
            entry = {'text': text, 'child': child}
            result.append(entry)
        if result:
            self.registers.insert_items(result)
