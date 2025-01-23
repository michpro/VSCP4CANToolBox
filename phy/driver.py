# pylint: disable=line-too-long, missing-module-docstring, missing-class-docstring, missing-function-docstring

import os
import platform
from can.bus import BusState
import can
import usb.core
import usb.util
import usb.backend.libusb1
import vscp

_current_path = os.path.dirname(os.path.realpath(__file__))
if platform.system() == 'Windows':
    _backend = usb.backend.libusb1.get_backend(find_library=lambda x:os.path.join(_current_path, 'libusb-1.0.dll'))
else:
    _backend = None # pylint: disable=invalid-name

class Driver: # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.notifier = None
        self.is_phy_initialized = False
        self.bus = None
        self.bitrates = {'250 kbps': 250000,
                         '125 kbps': 125000,
                         '100 kbps': 100000,
                         '83.3 kbps': 83333,
                         '50 kbps': 50000,
                        }
        self.default_bitrate_key = '100 kbps'
        self.bitrate = self.bitrates[self.default_bitrate_key]
        self.interfaces = {}
        self.interface = ''
        self.channels = {}
        self.channel = ''
        self.device_bus = None
        self.address = None
        if self.find_interfaces():
            self.find_interface_channels(self.interfaces[next(iter(self.interfaces))])


    def initialize(self, vscp_callbacks: list) -> bool:
        result = False
        if self.is_phy_initialized is False:
            try:
                self.bus = can.interface.Bus(
                    interface=self.interface,   channel=self.channel,
                    bus=self.device_bus,        address=self.address,
                    bitrate=self.bitrate,       state=BusState.ACTIVE,
                    auto_reset=True,            receive_own_messages=True
                    )
                callback = vscp.Callback(vscp_callbacks)
                self.notifier = can.Notifier(self.bus, [callback], timeout=3.0)
                self.is_phy_initialized = True
                result = True
            except  BaseException: # pylint: disable=broad-exception-caught
                pass
        return result


    def is_initialized(self) -> bool:
        return self.is_phy_initialized


    def shutdown(self):
        if self.notifier is not None:
            self.notifier.stop()
        if self.bus is not None:
            self.bus.shutdown()
        self.is_phy_initialized = False


    def configure(self, bitrate:int=0, interface:str='', channel:str='', bus:str='', address:str=''): # pylint: disable=too-many-arguments
        if interface:
            self.interface = interface
        if 0 != bitrate:
            self.bitrate = bitrate
        if channel:
            self.channel = channel
        if bus:
            self.device_bus = bus
        if address:
            self.address = address


    def find_interfaces(self) -> bool:
        result = False
        iface_list = ['pcan', 'gs_usb']#, 'slcan', 'socketcan']
        self.interfaces.clear()
        for iface in iface_list:
            match iface:
                case 'gs_usb':
                    if _backend is not None:
                        canable = usb.core.find(backend=_backend, idVendor=0x1D50, idProduct=0x606F)
                        if canable is not None:
                            self.interfaces['canable'] = iface
                case _:
                    configs = can.detect_available_configs(interfaces=iface)
                    if 0 != len(configs):
                        self.interfaces[iface.upper()] = iface
        if 0 != len(self.interfaces):
            self.interface = next(iter(self.interfaces))
            result = True
        return result


    def find_interface_channels(self, interface: str):
        result = False
        self.channels.clear()
        match interface:
            case 'pcan':
                configs = can.detect_available_configs(interfaces=interface.lower())
                if 0 != len(configs):
                    for config in configs:
                        if 'channel' in config and config['channel']:
                            channel_key = config['channel'].replace('PCAN_', '')
                            channel_data = {'channel': config['channel'], 'bus': None, 'address': None}
                            self.channels[channel_key] = channel_data
            case 'gs_usb':
                if _backend is not None:
                    configs = usb.core.find(backend=_backend, idVendor=0x1D50, idProduct=0x606F, find_all=True)
                    for config in configs:
                        try:
                            channel_key = f'CHAN_{config.address}'
                            channel_data = {'channel': config.product, 'bus': config.bus, 'address': config.address}
                            self.channels[channel_key] = channel_data
                        except ValueError:
                            pass
            case _:
                pass
        if 0 != len(self.channels):
            self.channel = next(iter(self.channels))
            result = True
        return result


driver = Driver()
