# pylint: disable=line-too-long, too-many-ancestors, too-many-instance-attributes
# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import phy
import vscp
import gui
from .common import call_set_scan_widget_state
from .popup import CTkFloatingWindow

class StatusFrame(ctk.CTkFrame): # pylint: disable=too-few-public-methods
    def __init__(self, parent):
        super().__init__(parent)

        elements_fg_color = parent._apply_appearance_mode(ctk.ThemeManager.theme['CTkFrame']['fg_color'])
        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icons = {'on':  (os.path.join(icon_dir, 'on_blue.png'),  os.path.join(icon_dir, 'on_green.png')),
                 'off': (os.path.join(icon_dir, 'off_gray.png'), os.path.join(icon_dir, 'off_red.png')),
                }

        widget_height = 26
        elements_pady = (2, 2)
        elements_height = widget_height - sum(list(elements_pady))

        self.widget = ctk.CTkFrame(parent, corner_radius=0, height=widget_height)
        self.widget.pack(side='top', anchor='s', fill='both', expand=False)

        self.progress = ctk.CTkProgressBar(self.widget, width=250, height=elements_height, border_width=2,
                                           determinate_speed=0.5)
        self.progress.pack(padx=(3, 0), pady=elements_pady, side='left', anchor='nw', fill='y', expand=False)
        self.progress.set(1)
        vscp.add_scan_progress_observer(self.update_progress)
        btn_width = 42
        btn_height = elements_height
        btn_set = 0
        self.img_on = ImageTk.PhotoImage(Image.open(icons['on'][btn_set]).resize((btn_width, btn_height)))
        self.img_off = ImageTk.PhotoImage(Image.open(icons['off'][btn_set]).resize((btn_width, btn_height)))
        self.phy_connect_is_on = False
        self.phy_connect = tk.Button(self.widget, background=elements_fg_color, activebackground=elements_fg_color,
                                     bd=0, width=btn_width, height=btn_height, image=self.img_off,
                                     command=self._phy_connect_switch)
        self.phy_connect.pack(padx=2, pady=elements_pady, side='right', anchor='ne', fill='y')

        self.phy_bitrate_var = ctk.StringVar(value=phy.driver.default_bitrate_key)
        self.phy_bitrate = ctk.CTkComboBox(self.widget, width=90, height=elements_height, fg_color=elements_fg_color,
                                           values=phy.driver.bitrates.keys(), variable=self.phy_bitrate_var,
                                           state='readonly')
        self.phy_bitrate.pack(padx=2, pady=elements_pady, side='right', anchor='ne', fill='y')

        self.phy_channel_var = ctk.StringVar(value=phy.driver.channel)
        self.phy_channel = ctk.CTkComboBox(self.widget, width=90, height=elements_height, fg_color=elements_fg_color,
                                           values=phy.driver.channels.keys(), variable=self.phy_channel_var,
                                           state='readonly')
        self.phy_channel.pack(padx=2, pady=elements_pady, side='right', anchor='ne', fill='y')

        self.phy_interface_var = ctk.StringVar(value=phy.driver.interface)
        self.phy_interface = ctk.CTkComboBox(self.widget, width=90, height=elements_height, fg_color=elements_fg_color,
                                             values=phy.driver.interfaces.keys(), variable=self.phy_interface_var,
                                             state='readonly', command=self._phy_interface_selected)
        self.phy_interface.pack(padx=2, pady=elements_pady, side='right', anchor='ne', fill='y')
        self.phy_interface.bind('<Button-3>', lambda event: self._show_search_menu(event, self.dropdown))

        self.dropdown = CTkFloatingWindow(self.widget)
        dropdown_bt_scan = ctk.CTkButton(self.dropdown.frame, border_spacing=2, corner_radius=0,
                                         text="Search for Interfaces", command=self._phy_search_interfaces)
        dropdown_bt_scan.pack(expand=True, fill="x", padx=0, pady=0)

        if not phy.driver.interfaces:
            self.phy_connect.configure(state='disabled')


    def _phy_channels_configure(self):
        self.phy_channel.configure(values=phy.driver.channels.keys())
        self.phy_channel.set(phy.driver.channel)


    def _phy_interface_selected(self, value):
        phy.driver.find_interface_channels(phy.driver.interfaces[value])
        self._phy_channels_configure()


    def _phy_search_interfaces(self):
        phy.driver.find_interfaces()
        if phy.driver.interfaces:
            self.phy_interface.configure(values=phy.driver.interfaces)
            self.phy_interface.set(phy.driver.interface)
            self._phy_interface_selected(phy.driver.interface)
            self.phy_connect.configure(state='normal')


    def _phy_connect_switch(self):
        if self.phy_connect_is_on:
            phy.driver.shutdown()
            img = self.img_off
            state = 'enable'
            call_set_scan_widget_state('disabled')
        else:
            channel_data = phy.driver.channels[self.phy_channel.get()]
            phy.driver.configure(interface=phy.driver.interfaces[self.phy_interface.get()],
                                 channel=channel_data['channel'],
                                 bus=channel_data['bus'],
                                 address=channel_data['address'],
                                 bitrate=phy.driver.bitrates[self.phy_bitrate.get()])
            phy.driver.initialize([gui.app.message_dispatcher, vscp.message.feeder])
            img = self.img_on
            state = 'disabled'
            call_set_scan_widget_state('normal')
        self._phy_iface_state(state)
        self.phy_connect.configure(image=img)
        self.phy_connect_is_on = not self.phy_connect_is_on


    def _phy_iface_state(self, state: str):
        _state = 'readonly' if 'enable' == state.lower() else 'disabled'
        self.phy_bitrate.configure(state=_state)
        self.phy_channel.configure(state=_state)
        self.phy_interface.configure(state=_state)


    def _show_search_menu(self, event, menu):
        try:
            if 'disabled' != self.phy_interface.cget('state'):
                menu.popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


    def update_progress(self, val):
        self.progress.set(val)
