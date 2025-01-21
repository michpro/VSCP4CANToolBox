# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import os
import pprint # TODO remove
import customtkinter as ctk
import vscp

class NodeConfiguration:
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

        self.mdf = vscp.mdf.get()['vscp']['module']
        # pp = pprint.PrettyPrinter(indent=4) # TODO remove
        # pp.pprint(self.mdf)
        # print(self.mdf['description'])
        # print(self.mdf['vscp']['module']['registers'])


    def _window_exit(self):
        self.parent.close_node_configuration()
