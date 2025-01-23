# pylint: disable=line-too-long, missing-module-docstring, missing-class-docstring, missing-function-docstring

import os
import pprint # TODO remove
import customtkinter as ctk
import vscp

class NodeConfiguration: # pylint: disable=too-many-instance-attributes, too-few-public-methods
    def __init__(self, parent, node_id: int, guid: str):
        super().__init__()
        self.window = ctk.CTkToplevel(parent)
        self.width = 1000
        self.height = 600
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


    def _window_exit(self):
        self.parent.close_node_configuration()


class InfoPanel(ctk.CTkFrame): # pylint: disable=too-many-ancestors
    def __init__(self, parent):
        self.parent = parent
        super().__init__(self.parent)

        font = ctk.CTkFont(family='Ubuntu Mono', size=16)
        self.event_info = ctk.CTkTextbox(self.parent, font=font, border_spacing=1, fg_color=self._fg_color)
        self.event_info.pack(padx=(5, 5), pady=(5, 5), side='top', anchor='nw', fill='both', expand=True)
        self.event_info.bind("<Button-1>", 'break')
        self.event_info.configure(state='disabled')


    def display(self, data: dict) -> None:
        # pp = pprint.PrettyPrinter(indent=2, width=160) # TODO remove
        # pp.pprint(data)

        self.event_info.configure(state='normal')
        self.event_info.delete('1.0', 'end')
        if 0 != len(data): # TODO implement
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
            info = ''
            for key in keys:
                data_key = next(iter(key))
                val = data.get(data_key, None)
                if val is not None:
                    info += key[data_key][0] + ': '
                    info += str(val) if key[data_key][2] is None else key[data_key][2]([int(val)], None)
                    info += ' '
                    if 'br' in key[data_key][1]:
                        info += os.linesep
                    elif 'eof' not in key[data_key][1]:
                        info += ' |  '
            self.event_info.insert('end', info)
        self.event_info.configure(state='disabled')


class ConfigPanel(ctk.CTkFrame): # pylint: disable=too-many-ancestors
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
