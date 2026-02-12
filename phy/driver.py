"""
CAN Bus Driver Module.

This module provides a wrapper around the python-can library to handle
CAN bus communication. It supports interface detection (specifically for
PCAN, GS_USB, SLCAN, and SocketCAN), configuration, and lifecycle management
of the bus connection.

@file driver.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""


import platform
import serial
import serial.tools.list_ports
from can.bus import BusState
import can
import usb.core
import usb.util
import vscp


class Driver: # pylint: disable=too-many-instance-attributes
    """
    Manages the CAN bus driver configuration and communication.

    This class handles the initialization of the physical layer, manages
    bitrates, detects available interfaces, and sets up message notifications.
    """


    def __init__(self):
        """
        Initializes the Driver instance with default settings.
        """
        self.notifier = None
        self.is_phy_initialized = False
        self.bus = None
        self.bitrates = {
            '250 kbps': 250000,
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

        # Initial scan: fast_scan_only=True prevents startup hangs on probing sensitive ports.
        if self.find_interfaces():
            self.find_interface_channels(
                self.interfaces[next(iter(self.interfaces))],
                fast_scan_only=True
            )

    def initialize(self, vscp_callbacks: list) -> bool:
        """
        Initializes the physical CAN bus connection.

        Connects to the configured interface/channel and starts the CAN notifier
        with the provided VSCP callbacks.

        Args:
            vscp_callbacks (list): A list of callback functions (or VSCP objects)
                                   to handle incoming messages.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        result = False
        if self.is_phy_initialized is False:
            try:
                kwargs = {}
                if self.interface == 'slcan':
                    baudrate = 115200
                    # Detect specific baudrate overrides (e.g. Lawicel 57600)
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

        Safely stops the notifier and the bus, ensuring resources are released.
        Specific handling is included for GS_USB on Windows to allow reconnection.
        """
        if self.notifier is not None:
            self.notifier.stop()
            self.notifier = None

        if self.bus is not None:
            try:
                self.bus.shutdown()
            except Exception: # pylint: disable=broad-exception-caught
                pass
            finally:
                # Critical: remove reference to allow GC and prevent __del__ errors
                self.bus = None

        # Explicitly dispose USB resources for gs_usb to fix re-connection issues on Windows.
        if self.interface == 'gs_usb' and self.device_bus and self.address:
            try:
                # Find device by bus/address to dispose resources
                # since we don't hold the device object directly.
                dev = usb.core.find(
                    idVendor=0x1D50, idProduct=0x606F,
                    custom_match=lambda d: d.bus == self.device_bus and d.address == self.address
                )
                if dev:
                    usb.util.dispose_resources(dev)
            except Exception: # pylint: disable=broad-exception-caught
                pass

        self.is_phy_initialized = False


    def configure(self, bitrate: int = 0, interface: str = '', channel: str = '', bus: str = '', address: str = ''): # pylint: disable=too-many-arguments, too-many-positional-arguments, line-too-long
        """
        Configures the driver parameters.

        Updates the configuration settings if provided values are not empty or zero.

        Args:
            bitrate (int, optional): The CAN bus bitrate.
            interface (str, optional): The interface name (e.g., 'pcan', 'slcan').
            channel (str, optional): The channel identifier.
            bus (str, optional): The bus identifier (backend specific).
            address (str, optional): The device address.
        """
        if interface:
            self.interface = interface
        if 0 != bitrate:
            self.bitrate = bitrate
        if channel:
            self.channel = channel

        # bus and address checks handle default "no change" signal (empty string)
        if '' != bus:
            self.device_bus = bus
        if '' != address:
            self.address = address


    def find_interfaces(self) -> bool:
        """
        Scans for available and supported CAN interfaces.

        Supported interfaces:
        - 'pcan' (Cross-platform)
        - 'gs_usb' (Windows only)
        - 'socketcan' (Linux only)
        - 'slcan' (Serial port based)

        Returns:
            bool: True if at least one interface was found, False otherwise.
        """
        result = False
        native_ifaces = ['pcan']

        if platform.system() == 'Windows':
            native_ifaces.append('gs_usb')
        elif platform.system() == 'Linux':
            native_ifaces.append('socketcan')

        self.interfaces.clear()

        # 1. Check Native Interfaces (High Priority)
        for iface in native_ifaces:
            match iface:
                case 'gs_usb':
                    # Rely on PyUSB to find the backend (e.g. WinUSB via system libusb wrapper)
                    canable = usb.core.find(idVendor=0x1D50, idProduct=0x606F)
                    if canable is not None:
                        self.interfaces['canable'] = iface
                case 'socketcan':
                    configs = can.detect_available_configs(interfaces=['socketcan'])
                    if configs:
                        self.interfaces['socketcan'] = iface
                case _:
                    configs = can.detect_available_configs(interfaces=iface)
                    if 0 != len(configs):
                        self.interfaces[iface.upper()] = iface

        # 2. Check Serial Ports for SLCAN (Low Priority - added last)
        com_ports = serial.tools.list_ports.comports()
        if len(com_ports) > 0:
            self.interfaces['slcan'] = 'slcan'

        if 0 != len(self.interfaces):
            # Default to the first found interface (Native takes precedence)
            self.interface = next(iter(self.interfaces))
            result = True
        return result


    def find_interface_channels(self, interface: str, fast_scan_only: bool = False): # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Finds available channels for a specific interface.

        Populates the `self.channels` dictionary with available channels for
        the given interface type (e.g. device IDs or COM ports).

        Args:
            interface (str): The name of the interface to scan.
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
                # Rely on PyUSB defaults to support WinUSB properly without forcing specific DLLs
                configs = usb.core.find(idVendor=0x1D50, idProduct=0x606F, find_all=True)
                if configs is not None:
                    for config in configs:
                        if isinstance(config, usb.core.Device):
                            channel_key = f'CHAN_{config.address}'

                            # Safely attempt to read product string, fallback on error
                            try:
                                product_name = config.product
                            except Exception: # pylint: disable=broad-exception-caught
                                product_name = f"GS_USB Device {config.address}"

                            # Pass product name as channel to satisfy type hints (str).
                            # Actual device identification relies on 'bus' and 'address' params.
                            channel_data = {'channel': product_name, 'bus': config.bus, 'address': config.address} # pylint: disable=line-too-long
                            self.channels[channel_key] = channel_data
            case 'socketcan':
                configs = can.detect_available_configs(interfaces=['socketcan'])
                for config in configs:
                    channel_name = config.get('channel')
                    if channel_name:
                        self.channels[channel_name] = {'channel': channel_name, 'bus': None, 'address': None} # pylint: disable=line-too-long
            case 'slcan':
                known_vids = ["1D50", "0483", "0403"] # VIDs: OpenMoko, STMicro, FTDI
                ports = serial.tools.list_ports.comports()

                for port in ports:
                    # SAFETY: Skip Bluetooth ports as opening them can hang if device is offline
                    if 'bluetooth' in (port.description or '').lower():
                        continue

                    is_slcan = False
                    baudrate = 115200

                    # 1. Fast check: VID match
                    hwid = port.hwid if port.hwid else ""

                    if "0403" in hwid:
                        baudrate = 57600

                    if any(vid in hwid for vid in known_vids):
                        is_slcan = True

                    # 2. Slow check: Probe port (Skipped if fast_scan_only is True)
                    if not is_slcan and not fast_scan_only:
                        try:
                            # Attempt to connect and check for 'v'ersion response.
                            # Timeout args ensure we don't block indefinitely.
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
