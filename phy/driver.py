"""
CAN Bus Driver Module.

This module provides a wrapper around the python-can library to handle
CAN bus communication. It supports interface detection (specifically for
PCAN, GS_USB, and SLCAN devices), configuration, and lifecycle management
of the bus connection.

@file driver.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

import os
import platform
import serial
import serial.tools.list_ports
from can.bus import BusState
import can
import usb.core
import usb.backend.libusb1
import vscp

_current_path = os.path.dirname(os.path.realpath(__file__))

# Configure libusb backend for Windows environment
if platform.system() == 'Windows':
    _backend = usb.backend.libusb1.get_backend(find_library=lambda x:os.path.join(_current_path, 'libusb-1.0.dll')) # pylint: disable=line-too-long
else:
    _backend = None # pylint: disable=invalid-name

class Driver: # pylint: disable=too-many-instance-attributes
    """
    Manages the CAN bus driver configuration and communication.

    This class handles the initialization of the physical layer, manages
    bitrates, detects available interfaces, and sets up message notifications.
    """

    def __init__(self):
        """
        Initializes the Driver instance with default settings.

        Sets up default bitrates, clears interface lists, and attempts
        to auto-detect connected interfaces upon instantiation.
        """
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

        # Initial scan: Use fast_scan_only=True to prevent startup hangs on probing
        if self.find_interfaces():
            self.find_interface_channels(self.interfaces[next(iter(self.interfaces))], fast_scan_only=True) # pylint: disable=line-too-long


    def initialize(self, vscp_callbacks: list) -> bool:
        """
        Initializes the physical CAN bus connection.

        Connects to the configured interface/channel and starts the CAN notifier
        with the provided VSCP callbacks.

        Args:
            vscp_callbacks (list): A list of callback functions to handle incoming messages.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        result = False
        if self.is_phy_initialized is False:
            try:
                kwargs = {}
                if self.interface == 'slcan':
                    baudrate = 115200
                    # Check if specific baudrate is detected (e.g. for Lawicel 57600)
                    if self.channel in self.channels:
                        baudrate = self.channels[self.channel].get('baudrate', 115200)
                    kwargs['ttyBaudrate'] = baudrate

                self.bus = can.interface.Bus(
                    interface=self.interface,   channel=self.channel,
                    bus=self.device_bus,        address=self.address,
                    bitrate=self.bitrate,       state=BusState.ACTIVE,
                    auto_reset=True,            receive_own_messages=True,
                    **kwargs
                    )
                callback = vscp.Callback(vscp_callbacks)
                self.notifier = can.Notifier(self.bus, [callback], timeout=3.0)
                self.is_phy_initialized = True
                result = True
            except BaseException: # pylint: disable=broad-exception-caught
                pass
        return result


    def is_initialized(self) -> bool:
        """
        Checks if the driver is currently initialized.

        Returns:
            bool: True if the physical layer is initialized, False otherwise.
        """
        return self.is_phy_initialized


    def shutdown(self):
        """
        Shuts down the CAN bus connection.

        Stops the notifier and shuts down the bus interface safely.
        """
        if self.notifier is not None:
            self.notifier.stop()
        if self.bus is not None:
            self.bus.shutdown()
        self.is_phy_initialized = False


    def configure(self, bitrate: int = 0, interface: str = '', channel: str = '', bus: str = '', address: str = ''): # pylint: disable=too-many-arguments, too-many-positional-arguments, line-too-long
        # pylint: disable=line-too-long
        """
        Configures the driver parameters.

        Updates the configuration settings if provided values are not empty/zero.

        Args:
            bitrate (int, optional): The CAN bus bitrate. Defaults to 0 (no change).
            interface (str, optional): The interface name (e.g., 'pcan').
            channel (str, optional): The channel identifier.
            bus (str, optional): The bus identifier.
            address (str, optional): The device address.
        """
        # pylint: enable=line-too-long
        if interface:
            self.interface = interface
        if 0 != bitrate:
            self.bitrate = bitrate
        if channel:
            self.channel = channel

        # bus and address checks handle default "no change" signal (empty string) from caller
        if '' != bus:
            self.device_bus = bus
        if '' != address:
            self.address = address


    def find_interfaces(self) -> bool:
        """
        Scans for available and supported CAN interfaces.

        Supports detection of 'pcan', 'gs_usb' (Canable), and 'slcan' (Serial) interfaces.
        Populates the `self.interfaces` dictionary. Priority is given to native CAN interfaces.

        Returns:
            bool: True if at least one interface was found, False otherwise.
        """
        result = False
        native_ifaces = ['pcan', 'gs_usb']
        self.interfaces.clear()

        # 1. Check Native Interfaces (High Priority)
        for iface in native_ifaces:
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

        # 2. Check Serial Ports for SLCAN (Low Priority - added last)
        # We assume if serial ports exist, slcan is possible.
        com_ports = serial.tools.list_ports.comports()
        if len(com_ports) > 0:
            self.interfaces['slcan'] = 'slcan'

        if 0 != len(self.interfaces):
            # Sets default interface to the first one found (Native takes precedence due to insertion order) # pylint: disable=line-too-long
            self.interface = next(iter(self.interfaces))
            result = True
        return result


    def find_interface_channels(self, interface: str, fast_scan_only: bool = False): # pylint: disable=too-many-locals, too-many-branches
        """
        Finds available channels for a specific interface.

        Populates the `self.channels` dictionary with available channels for
        the given interface type (e.g. device IDs or COM ports).

        Args:
            interface (str): The name of the interface to scan (e.g., 'pcan', 'gs_usb', 'slcan').
            fast_scan_only (bool): If True, skips slow probing methods (e.g. opening COM ports).

        Returns:
            bool: True if at least one channel was found, False otherwise.
        """
        result = False
        self.channels.clear()
        match interface:
            case 'pcan':
                configs = can.detect_available_configs(interfaces=interface.lower())
                if 0 != len(configs):
                    for config in configs:
                        if 'channel' in config and config['channel']:
                            raw_channel = config.get('channel', '')
                            if isinstance(raw_channel, str):
                                channel_key = raw_channel.replace('PCAN_', '')
                            else:
                                channel_key = str(raw_channel).replace('PCAN_', '')
                            channel_data = {'channel': config['channel'], 'bus': None, 'address': None} # pylint: disable=line-too-long
                            self.channels[channel_key] = channel_data
            case 'gs_usb':
                if _backend is not None:
                    configs = usb.core.find(backend=_backend, idVendor=0x1D50, idProduct=0x606F, find_all=True) # pylint: disable=line-too-long
                    if configs is not None:
                        for config in configs:
                            if isinstance(config, usb.core.Device):
                                channel_key = f'CHAN_{config.address}'
                                channel_data = {'channel': config.product, 'bus': config.bus, 'address': config.address} # pylint: disable=line-too-long
                                self.channels[channel_key] = channel_data
            case 'slcan':
                known_vids = ["1D50", "0483", "0403"] # VIDs: OpenMoko, STMicro, FTDI
                ports = serial.tools.list_ports.comports()

                for port in ports:
                    # SAFETY: Skip Bluetooth ports as opening them can hang for a long time if device is offline # pylint: disable=line-too-long
                    if 'bluetooth' in (port.description or '').lower():
                        continue

                    is_slcan = False
                    baudrate = 115200 # Default slcan baudrate

                    # 1. Fast check: VID match
                    # port.hwid e.g. "USB VID:PID=..."
                    hwid = port.hwid if port.hwid else ""

                    if "0403" in hwid:
                        # Lawicel (VID 0403) typically uses 57600
                        baudrate = 57600

                    if any(vid in hwid for vid in known_vids):
                        is_slcan = True

                    # 2. Slow check: Probe port (Skipped if fast_scan_only is True)
                    if not is_slcan and not fast_scan_only:
                        try:
                            # Attempt to connect and check for 'v'ersion response
                            # write_timeout and timeout ensure we don't block
                            with serial.Serial(port.device, 115200, timeout=0.1, write_timeout=0.1) as ser: # pylint: disable=line-too-long
                                ser.write(b'v\r')
                                res = ser.read(10)
                                if res.startswith(b'V') or res.startswith(b'v'):
                                    is_slcan = True
                        except (OSError, serial.SerialException):
                            pass

                    if is_slcan:
                        channel_key = port.device
                        channel_data = {'channel': port.device, 'bus': None, 'address': None, 'baudrate': baudrate} # pylint: disable=line-too-long
                        self.channels[channel_key] = channel_data

            case _:
                pass

        if 0 != len(self.channels):
            self.channel = next(iter(self.channels))
            result = True
        return result


driver = Driver()
