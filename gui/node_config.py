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


import os
import customtkinter as ctk
import vscp
from .tab_registers import RegistersTab


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

        app_window = parent.winfo_toplevel()
        x = int(app_window.winfo_rootx() + (app_window.winfo_width() / 2) - (self.width / 2))
        y = int((0.95 * (app_window.winfo_rooty() + (app_window.winfo_height() / 2))) - (self.height / 2)) # pylint: disable=line-too-long

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


class InfoPanel(ctk.CTkFrame): # pylint: disable=too-many-ancestors
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
        temp_fg_color = tuple(self._fg_color) if isinstance(self._fg_color, list) else self._fg_color # pylint: disable=line-too-long
        self.module_info = ctk.CTkTextbox(self.parent, font=font, border_spacing=1, fg_color=temp_fg_color) # pylint: disable=line-too-long
        self.module_info.pack(padx=(5, 5), pady=(5, 5), side='top', anchor='nw', fill='both', expand=True) # pylint: disable=line-too-long
        self.module_info.bind("<Button-1>", lambda e: 'break')
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
                    {'algorithm':   ['Bootloader Algorithm',    '',     vscp.dictionary.convert_blalgo]}, # pylint: disable=line-too-long
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
                    info = str(val) if key[data_key][2] is None else key[data_key][2]([int(val)], None) # pylint: disable=line-too-long
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
