# pylint: disable=line-too-long, missing-module-docstring, missing-class-docstring, missing-function-docstring

import os
import ctypes
import datetime
import platform
import customtkinter as ctk
from .menu import Menu
from .panels import AppFrame
from .status import StatusFrame


class Application(ctk.CTk): # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__()
        self.width = 1552
        self.height = 700
        self.version = '0.8'

        current_path = os.path.dirname(os.path.realpath(__file__))
        icon_dir = os.path.join(current_path, 'icons')
        icon_path = os.path.join(icon_dir, 'vscp_logo.ico')
        font_dir = os.path.join(current_path, 'fonts')
        font_path = os.path.join(font_dir, 'UbuntuMono-R.ttf')
        ctk.FontManager.load_font(font_path)


        if platform.system() == 'Windows':
            appid = 'MProVSCPToolBox'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)

        self._set_appearance_mode('system')
        self.iconbitmap(icon_path)
        self.title('VSCP ToolBox v' + self.version)

        x = int((self.winfo_screenwidth() / 2) - (self.width / 2))
        y = int((0.95 * (self.winfo_screenheight() / 2)) - (self.height / 2))
        self.geometry(f'{self.width}x{self.height}+{x}+{y}')

        self.minsize(width=self.width, height=self.height)
        self.resizable(width=False, height=True)

        self.menu = Menu(self)
        self.app = AppFrame(self)
        self.status_bar = StatusFrame(self)


    def message_dispatcher(self, msg) -> None:
        self.app.right.messages.insert(self._prepare_data_to_show(msg))
        # self.app.left.neighbourhood.scan_frame.check_node(msg['nickName'])


    def _prepare_data_to_show(self, msg) -> list:
        node_id = f"0x{msg['nickName']:02X}"
        if msg['isHardCoded'] is True:
            node_id = '►' + node_id + '◄'
        data = [{'values': [
                            str(datetime.datetime.fromtimestamp(msg['timestamp']).time()),
                            msg['dir'],
                            node_id,
                            msg['priority']['name'],
                            msg['class']['name'],
                            msg['type']['name'],
                            ' '.join(f'0x{val:02X}' for val in msg['data']) if 0 != msg['dataLen'] else ''
                          ]
               }]
        return data


app = Application()
