# pylint: disable=too-many-lines, line-too-long, missing-module-docstring, missing-class-docstring, missing-function-docstring

import os
from copy import deepcopy
from datetime import datetime
from functools import singledispatchmethod
from .utils import search


UNKNOWN_VALUE = 65534
UNKNOWN_NAME = "UNKNOWN"
MULTILINE_INDENT = 18


class Dictionary:
    def __init__(self) -> None:
        pass


    def get(self) -> list:
        return _vscp_class_1_dict


    def priority_id(self, name: str) -> int:
        result = search(name, 'name', 'id', _vscp_priority)
        if not isinstance(result, int):
            result = _vscp_priority[-1]['id']
        return result


    def priority_name(self, var: int) -> str:
        result = search(var, 'id', 'name', _vscp_priority)
        if not isinstance(result, str):
            result = str(UNKNOWN_NAME)
        return result


    def class_name(self, var: int) -> str:
        result = search(var, 'id', 'class', self.get())
        if not isinstance(result, str):
            result = str(UNKNOWN_NAME)
        return result


    def class_id(self, name: str) -> int:
        result = search(name, 'class', 'id', self.get())
        if not isinstance(result, int):
            result = int(UNKNOWN_VALUE)
        return result


    def type_name(self, class_id: int, type_id: int) -> str:
        result = search(type_id, 'id', 'type', self.class_types(class_id))
        if not isinstance(result, str):
            result = str(UNKNOWN_NAME)
        return result


    def type_id(self, class_, type_: str) -> int:
        result = None
        if isinstance(class_, (int, str)):
            result = search(type_, 'type', 'id', self.class_types(class_))
        if not isinstance(result, int):
            result = int(UNKNOWN_VALUE)
        return result


    @singledispatchmethod
    def class_types(self, _var) -> list:
        return []


    @class_types.register
    def _(self, var: int) -> list:
        return search(var, 'id', 'types', self.get()) or []


    @class_types.register
    def _(self, var: str) -> list:
        return search(var, 'class', 'types', self.get()) or []


    def parse_data(self, class_id: int, type_id: int, data: list) -> list:
        data_descr = self._get_data_description(class_id, type_id)
        description = data_descr['str'] if 'str' in data_descr else ''
        units = data_descr['uni'] if 'uni' in data_descr else {}
        result = [[description, '']]
        if 'dlc' in data_descr:
            pos = 0
            for idx in range(len(data_descr['dlc'])):
                data_len = data_descr['dlc'][idx]['l']
                data_type = data_descr['dlc'][idx]['t']
                data_str = data_descr['dlc'][idx]['d']
                value_str = self._convert(data_type, data[pos:(pos + data_len)], units)
                if 0 != len(data) or 'none' == data_type:
                    result.append([data_str, value_str])
                pos += data_len
        return result


    def _get_data_description(self, class_id: int, type_id: int) -> dict:
        result = search(type_id, 'id', 'descr', self.class_types(class_id))
        if not isinstance(result, dict):
            result = {}
        return result


    def _convert_bits(self, data: list, _) -> str:
        result = ''
        for idx, val in enumerate(data):
            result += f'{val:08b}'
            result += ' ' if 3 !=idx else (os.linesep + (' ' * MULTILINE_INDENT))
        return result


    def _convert_int(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=True)
        except ValueError:
            val = 0
        return f'{val:d}'


    def _convert_uint(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=False)
        except ValueError:
            val = 0
        return f'{val:d}'


    def _convert_ruint(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=False) & 0xFF
            if 0 == val:
                val = 256
            result = f'{val:d}'
        except ValueError:
            result = ''
        return result


    def _convert_hexint(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=False)
        except ValueError:
            val = 0
        width = 2 * len(data)
        return f'0x{val:0{width}X}'


    def _convert_combined_ints(self, data: list, _) -> str:
        indent = os.linesep + (' ' * MULTILINE_INDENT)
        result_hex  =          f'{"HEX":<6}'  + self._convert_hexint(data, _)
        result_int  = indent + f'{"int":<6}'  + self._convert_int(data, _)
        result_uint = indent + f'{"uint":<6}' + self._convert_uint(data, _)
        return result_hex + result_int + result_uint


    def _convert_normalizedint(self, data: list, _) -> str:
        result = ''
        if 1 < len(data):
            try:
                val = int(data[0])
                exponent = (val & 0x7F) * (-1 if 0 != val & 0x80 else 1)
                normalizer = pow(10, exponent)
                val = float(int.from_bytes(data[1:], 'big', signed=True) * normalizer)
                result = f'{val:.16G}'
            except ValueError:
                result = 'NaN'
        return result


    def _convert_float(self, data: list, _) -> str:
        data.reverse()
        try:
            val = memoryview(bytearray(data)).cast('f')[0]
        except ValueError:
            val = 0.0
        return f'{val:.7G}'


    def _convert_double(self, data: list, _) -> str:
        data.reverse()
        try:
            val = memoryview(bytearray(data)).cast('d')[0]
        except ValueError:
            val = 0.0
        return f'{val:.16G}'


    def _convert_dtime0(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=False) & 0x00000000FFFFFFFF
        except ValueError:
            val = 0
        return str(datetime.fromtimestamp(val))


    def _convert_dtime1(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big') & 0x0000003FFFFFFFFF
            year   = val >> 26 & 0x0FFF
            month  = val >> 22 & 0x0F
            day    = val >> 17 & 0x1F
            hour   = val >> 12 & 0x1F
            minute = val >> 6  & 0x3F
            second = val >> 0  & 0x3F
            result = f'{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'
        except ValueError:
            result = '0000-00-00 00:00:00'
        return result


    def _convert_dtime2(self, data: list, _) -> str:
        result = '0000-00-00 00:00:00'
        if 7 == len(data):
            try:
                year   = int(int.from_bytes(data[:2], 'big', signed=False))
                month  = int(data[2])
                day    = int(data[3])
                hour   = int(data[4])
                minute = int(data[5])
                second = int(data[6])
                result = f'{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'
            except ValueError:
                pass
        return result


    def _convert_date_ymd(self, data: list, _) -> str:
        result = '0000-00-00'
        if 4 == len(data):
            try:
                year = int(int.from_bytes(data[:2], 'big', signed=False))
                month = int(data[2])
                day = int(data[3])
                result = f'{year:04d}-{month:02d}-{day:02d}'
            except ValueError:
                pass
        return result


    def _convert_time_hms(self, data: list, _) -> str:
        if 6 != len(data):
            result = '00:00:00'
        else:
            pos = [1, 3]
            result = ''
            for idx, val in enumerate(data):
                result += chr(val)
                result += ':' if idx in pos else ''
        return result


    def _convert_time_hms_ms(self, data: list, _) -> str:
        result = '00:00:00.000'
        if 5 == len(data):
            try:
                hour = int(data[0], 'big', signed=False)
                minute = int(data[1])
                second = int(data[2])
                millisecond = int(int.from_bytes(data[3:], 'big', signed=False))
                result = f'{hour:02d}:{minute:02d}:{second:02d}.{millisecond:03d}'
            except ValueError:
                pass
        return result


    def _convert_weekday(self, data: list, _) -> str:
        results = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        try:
            result = results[data[0]]
        except (KeyError, ValueError):
            result = 'Unknown'
        return result


    def _convert_flags0(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=False)
        except ValueError:
            val = 0
        result = ''
        bits = []
        for idx in range (5, 8):
            if val & (1 << idx):
                bits.append(idx)
        bits_count = len(bits)
        for idx in range(bits_count):
            match bits[idx]:
                case 5:
                    result += 'Reset device. Keep nickname (ID).'
                case 6:
                    result += 'Set persistent storage to default.'
                case 7:
                    result += 'Go idle. Do not start up again.'
                case _:
                    pass
            if (idx + 1) < bits_count:
                result += os.linesep + (' ' * MULTILINE_INDENT)
        return result


    def _convert_flags1(self, data: list, _) -> str:
        try:
            val = int.from_bytes(data, 'big', signed=False)
        except ValueError:
            val = 0
        result = ''
        bits = []
        for idx in range (0, 16):
            if val & (1 << idx):
                bits.append(idx)
        results = {
            0x0F:   'Have VSCP TCP serv. with VCSP link iface',
            0x0E:   'Have VSCP UDP server',
            0x0D:   'Have VSCP Multicast announce interface',
            0x0C:   'Have VSCP raw Ethernet',
            0x0B:   'Have Web server',
            0x0A:   'Have VSCP Websocket interface ',
            0x09:   'Have VSCP REST interface',
            0x08:   'Have VSCP Multicast channel support',
            0x07:   'Reserved',
            0x06:   'IPv6 support',
            0x05:   'IPv4 support',
            0x04:   'SSL support',
            0x03:   'Accepts >=2 concurrent TCP/IP conn.',
            0x02:   'Support AES256',
            0x01:   'Support AES192',
            0x00:   'Support AES128',
        }
        bits_count = len(bits)
        for idx, val in enumerate(reversed(bits)):
            result += results[val]
            if (idx + 1) < bits_count:
                result += os.linesep + (' ' * MULTILINE_INDENT)
        return result


    def _convert_blalgo(self, data: list, _) -> str:
        results = {
            0x00:   'VSCP algorithm',
            0x01:   'Microchip PIC algorithm',
            0x10:   'Atmel AVR algorithm',
            0x20:   'NXP ARM algorithm',
            0x30:   'ST ARM algorithm',
            0x40:   'Freescale algorithm',
            0x50:   'Espressif algorithm',
            0xFF:   'No bootloader available',
        }
        for key in range(0xF0, 0xFF):
            results[key] = 'User defined algorithm'
        try:
            result = results[int.from_bytes(data, 'big', signed=False)]
        except (KeyError, ValueError):
            result = 'Undefined algorithm'
        return result


    def _convert_memtyp(self, data: list, _) -> str:
        results = {
            0x01:   'DATA (EEPROM, MRAM, FRAM)',
            0x02:   'CONFIG (CPU configuration)',
            0x03:   'RAM',
            0x04:   'USERID/GUID etc.',
            0x05:   'FUSES',
            0x06:   'BOOTLOADER',
            0xFD:   'User specified memory area 1',
            0xFE:   'User specified memory area 2',
            0xFF:   'User specified memory area 3',
        }
        try:
            result = results[int.from_bytes(data, 'big', signed=False)]
        except (KeyError, ValueError):
            result = 'Undefined'
        return result


    def _convert_dimtype(self, data: list, _) -> str:
        try:
            val = int(data[0])
        except ValueError:
            val = -1
        if 1 <= val <= 99:
            result = f'{val:d}'
        elif 0 == val:
            result = 'OFF'
        elif 100 == val:
            result = 'full ON'
        elif 254 == val:
            result = 'dim down one step'
        elif 255 == val:
            result = 'dim up one step'
        else:
            result = 'Undefined'
        return result


    def _convert_repeattype(self, data: list, _) -> str:
        try:
            val = int(data[0])
        except ValueError:
            val = -1
        if 0 == val:
            result = 'repeat forever'
        elif 0 < val:
            result = f'{val:d}'
        else:
            result = 'Unknown'
        return result


    def _convert_evbutton(self, data: list, _) -> str:
        result = ''
        try:
            val = int(data) & 0xFF
        except ValueError:
            val = 0
        if val & 0x02:
            result += 'Pressed '
        if val & 0x01:
            result += 'Released '
        if val & 0x04:
            result += 'Clicked '
        if 0 != val:
            result += f'# {(val >> 3):d} times'
        return result


    def _convert_evtoken(self, data: list, _) -> str:
        event_codes = {
            0:  'Touched-released',
            1:  'Touched',
            2:  'Released',
            3:  'Reserved'
        }
        token_types = {
            0:  'Unknown Token 128b',
            1:  'iButton Token 64b',
            2:  'RFID Token 64b',
            3:  'RFID Token 128b',
            4:  'RFID Token 256b',
            9:  'ID/Credit card 128b',
            16: 'Biometric device 256b',
            17: 'Biometric device 64b',
            18: 'Bluetooth device 48b',
            19: 'GSM IMEI code 64b',
            20: 'GSM IMSI code 64b',
            21: 'RFID Token 40b',
            22: 'RFID Token 32b',
            23: 'RFID Token 24b',
            24: 'RFID Token 16b',
            25: 'RFID Token 8b',
        }
        reserved = (*range(5, 9), *range(10, 16), *range(26, 64))
        for key in reserved:
            token_types[key] = 'Reserved'
        try:
            val = int(data[0]) & 0x03
            result = event_codes[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        result += ' : '
        try:
            val = (int(data[0]) >> 2) & 0x3F
            result += token_types[val]
        except (ValueError, KeyError):
            result += 'Unknown'
        return result


    def _convert_onoffstate(self, data: list, _) -> str:
        result = ''
        if 1 == len(data):
            result = 'ON' if 0 != data[0] else 'OFF'
        return result


    def _convert_ledaction(self, data: list, _) -> str:
        try:
            results = {
                0:  'OFF',
                1:  'ON',
                2:  'BLINK',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_playbackfunction(self, data: list, _) -> str:
        try:
            results = {
                0:  'Stop',
                1:  'Pause',
                2:  'Play',
                3:  'Forward',
                4:  'Rewind',
                5:  'Fast Forward',
                6:  'Fast Rewind',
                7:  'Next Track',
                30: 'Previous Track',
                31: 'Toggle repeat mode',
                32: 'Repeat mode ON',
                33: 'Repeat mode OFF',
                34: 'Toggle Shuffle mode',
                35: 'Shuffle ON',
                36: 'Shuffle mode OFF',
                37: 'Fade in, Play',
                38: 'Fade out, Stop',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_navigationfunction(self, data: list, _) -> str:
        try:
            results = {
                10: '+10',
                20: 'OK',
                21: 'Left',
                22: 'Right',
                23: 'Up',
                24: 'Down',
                25: 'Menu',
                26: 'Selecting',
            }
            for idx in range(10):
                results[idx] = f'{idx:d}'
            chars = (*range(65, 91), *range(97, 123))
            for idx in chars:
                results[idx] = chr(idx)
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_screenformat(self, data: list, _) -> str:
        try:
            results = {
                0:  'Auto',
                1:  'Just',
                2:  'Normal',
                3:  'Zoom',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_devicecode_input(self, data: list, _) -> str:
        try:
            val = int(data[0])
        except ValueError:
            val = 0xFF
        results = {
            0:  'Auto',
            1:  'CD',
            2:  'AUX',
            3:  'DVD',
            4:  'SAT',
            5:  'VCR',
            6:  'Tape',
            7:  'Phone',
            8:  'Tuner',
            9:  'FM',
            10: 'AM',
            11: 'Radio',
            16: 'Component',
            17: 'VGA',
            18: 'SVideo',
            19: 'Video1',
            20: 'Video2',
            21: 'Video3',
            22: 'Sat1',
            23: 'Sat2',
            24: 'Sat3',
            25: 'mp3 source',
            26: 'mpeg source',
        }
        result = results[val] if val in results else f'0x{val:02X}'
        return result


    def _convert_devicecode_output(self, data: list, _) -> str:
        try:
            val = int(data[0])
        except ValueError:
            val = 0xFF
        results = {
            0:  'Auto',
            16: 'Component',
            17: 'VGA',
            18: 'SVideo',
            19: 'Video1',
            20: 'Video2',
            21: 'Video3',
            30: 'HDMI1',
            31: 'HDMI2',
            32: 'HDMI3',
        }
        result = results[val] if val in results else f'0x{val:02X}'
        return result


    def _convert_recording_control(self, data: list, _) -> str:
        try:
            results = {
                0:  'Start recording',
                1:  'Stop recording',
                2:  'Disable AGC',
                3:  'Enable AGC',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_tivocode(self, data: list, _) -> str:
        try:
            results = {
                1:  'Box Office',
                2:  'Services',
                3:  'Program Guide',
                4:  'Text',
                5:  'Info',
                6:  'Help',
                7:  'Backup',
                20: 'Red key',
                21: 'Yellow key',
                22: 'Green key',
                23: 'Blue key',
                24: 'White key',
                25: 'Black key',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_media_information(self, data: list, _) -> str:
        try:
            results = {
                0:  'Current Title',
                1:  'Get Folders',
                2:  'Get Disks',
                3:  'Get Tracks',
                4:  'Get Albums/Play lists',
                5:  'Get Channels',
                6:  'Get Pages',
                7:  'Get Chapters',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_multimedia_control(self, data: list, _) -> str:
        try:
            results = {
                0:  'Active Title',
                1:  'Set Title',
                2:  'Active Folder',
                3:  'Set Active Folder',
                4:  'Artist',
                5:  'Year',
                6:  'Genre',
                7:  'Album',
                8:  'Comment',
                9:  'Track',
                10: 'Picture',
                11: 'Sample rate',
                12: 'Bit-rate',
                13: 'Channels',
                14: 'Media size bytes',
                15: 'Time',
                16: 'Mpeg version',
                17: 'Mpeg layer',
                18: 'Frequency',
                19: 'Channel Mode',
                20: 'CRC',
                21: 'Copyright',
                22: 'Original',
                23: 'Emphasis',
                24: 'Media position in milliseconds',
                25: 'Media-length in milliseconds',
                26: 'Version',
                27: 'Album/Play list',
                28: 'Play file',
                29: 'Add file to album/play-list',
                30: 'Current Folder',
                31: 'Folder content',
                32: 'Set Folder',
                33: 'Get Folder content',
                34: 'Get Folder content albums/play-lists',
                35: 'Get Folder content filter',
                36: 'Disks list',
                37: 'Folders list',
                38: 'Tracks list',
                39: 'Albums/Play list list',
                40: 'Channels list',
                41: 'Pages list',
                42: 'Chapters list',
                43: 'New Album/Play list',
            }
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_securevent(self, data: list, _) -> str:
        result = 'Unknown'
        if 0 < len(data):
            results = {
                0:  'Security event occurred',
                1:  'Activated',
                2:  'Inactivated',
            }
            result = results[data[0]] if data[0] in results else self._convert_int(data, _)
        return result


    def _convert_id_check_bits(self, data: list, _) -> str:
        try:
            val = int(data[0])
            result = self._convert_bits(data, _)
            bits = []
            for idx in range (0, 2):
                if val & (1 << idx):
                    bits.append(idx)
            bits_count = len(bits)
            for idx in range(bits_count):
                result += os.linesep + (' ' * MULTILINE_INDENT)
                match bits[idx]:
                    case 0:
                        result += 'Authenticated'
                    case 1:
                        result += 'Authorized'
                    case _:
                        pass
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_config_status(self, data: list, _) -> str:
        result = ''
        try:
            val = int(data[0])
            if val & (1 << 7):
                result = 'Reboot device after config loaded'
        except ValueError:
            pass
        return result


    def _convert_timeunit(self, data: list, _) -> str:
        results = {
            0:  'Time in microseconds',
            1:  'Time in milliseconds',
            2:  'Time in seconds',
            3:  'Time in minutes',
            4:  'Time in hours',
            5:  'Time in days',
        }
        try:
            val = int(data[0]) & 0x0F
            result = results[val]
        except (ValueError, KeyError):
            result = 'Reserved'
        return result


    def _convert_langcoding(self, data: list, _) -> str:
        results = {
            0:  'Custom coded system',
            1:  'ISO 639-1',
            2:  'ISO 639-2/T',
            3:  'ISO 639-2/B',
            4:  'ISO 639-3',
            5:  'IETF (RFC-5646/4647)',
        }
        try:
            val = int(data[0])
            result = results[val]
        except (ValueError, KeyError):
            result = 'Unknown'
        return result


    def _convert_pulsetypecoding(self, data: list, _) -> str:
        try:
            val = int(data[0])
            result = self._convert_timeunit(data, _)
            bits = []
            for idx in range (6, 8):
                if val & (1 << idx):
                    bits.append(idx)
            bits_count = len(bits)
            for idx in range(bits_count):
                result += os.linesep + (' ' * MULTILINE_INDENT)
                match bits[idx]:
                    case 6:
                        result += 'Send INFO.ON  event when pulse goes on'
                    case 7:
                        result += 'Send INFO.OFF event when pulse goes off'
                    case _:
                        pass
        except (ValueError, KeyError):
            result = 'Reserved'
        return result


    def _convert_measurecoding(self, data: list, units: dict) -> dict:
        result = {'dataType':       'raw',
                  'unit':           '',
                  'sensorIndex':    0}
        if 1 == len(data):
            formats = {
                0x00:   'bits',
                0x01:   'raw',
                0x02:   'ascii',
                0x03:   'int',
                0x04:   'normint',
                0x05:   'float',
                0x06:   'double',
                0x07:   'RESERVED'
            }
            try:
                val = int(data[0])
                result['sensorIndex'] = val & 0x07
                unit = units[(val >> 3) & 0x03] if (val >> 3) & 0x03 in units else ''
                if isinstance(unit, dict):
                    result['unit'] = unit['u'] if 'u' in unit else ''
                    data_type = unit['t'] if 't' in unit else 'unknown'
                else:
                    result['unit'] = unit
                    data_type = formats[(val >> 5) & 0x07]
                result['dataType'] = data_type
            except (ValueError, KeyError):
                pass
        return result


    def _convert_measurement_data(self, data: list, units: dict) -> str:
        result = 'CONVERSION ERROR'
        if 1 < len(data):
            coding = self._convert_measurecoding([data[0]], units)
            try:
                result = self._convert(coding['dataType'], data[1:], {})
                result += (' ' + coding['unit']) if '' != coding['unit'] else ''
                result += os.linesep + f"{'Sensor index':<{MULTILINE_INDENT}}" + str(coding['sensorIndex'])
            except KeyError:
                pass
        return result


    def _convert_measurement_zoned_data(self, data: list, units: dict) -> str:
        result = 'CONVERSION ERROR'
        if 5 <= len(data):
            coding = self._convert_measurecoding([0x80], units) # coding: normalized int; unit: default
            try:
                result = self._convert(coding['dataType'], data[:5], {})
                result += (' ' + coding['unit']) if '' != coding['unit'] else ''
            except KeyError:
                pass
        return result


    def _convert_measurement_32_data(self, data: list, units: dict) -> str:
        result = 'CONVERSION ERROR'
        if 4 <= len(data):
            coding = self._convert_measurecoding([0xA0], units) # coding: float; unit: default
            try:
                result = self._convert(coding['dataType'], data[:4], {})
                result += (' ' + coding['unit']) if '' != coding['unit'] else ''
            except KeyError:
                pass
        return result


    def _convert_measurement_64_data(self, data: list, units: dict) -> str:
        result = 'CONVERSION ERROR'
        if 8 == len(data):
            coding = self._convert_measurecoding([0xC0], units) # coding: double; unit: default
            try:
                result = self._convert(coding['dataType'], data, {})
                result += (' ' + coding['unit']) if '' != coding['unit'] else ''
            except KeyError:
                pass
        return result


    def _convert_measureindex(self, data: list, _) -> str:
        try:
            val = int(data[0])
        except ValueError:
            val = -1
        if 0 == val:
            result = 'all measurements'
        elif 0 < val:
            result = f'{val:d}'
        else:
            result = 'Undefined'
        return result


    def _convert_sensorindex(self, data: list, _) -> str:
        try:
            val = int(data[0])
        except ValueError:
            val = -1
        if 0xFF == val:
            result = 'all sensors'
        elif 0 <= val:
            result = f'{val:d}'
        else:
            result = 'Undefined'
        return result


    def _convert_changecode(self, data: list, _) -> str:
        try:
            val = int(data[0], )
        except ValueError:
            val = -1
        if 0 <= val <= 127:
            result = f'{val:d}'
        elif 128 <= val <= 157:
            result = f'down by {(val - 127):d}'
        elif 160 <= val <= 189:
            result = f'up by {(val - 159):d}'
        elif 255 == val:
            result = 'extended'
        else:
            result = 'Undefined'
        return result


    def _convert_coord(self, data: list, _) -> str:
        result = ''
        if 1 == len(data):
            result = 'absolute' if 0 != data[0] else 'relative'
        return result


    def _convert_loglevel(self, data: list, _) -> str:
        result = 'Unknown'
        if 0 < len(data):
            results = {
                0:  'Emergency',
                1:  'Alert',
                2:  'Critical',
                3:  'Error',
                4:  'Warning',
                5:  'Notice',
                6:  'Informational',
                7:  'Debug',
                8:  'Verbose',
            }
            result = results[data[0]] if data[0] in results else self._convert_int(data, _)
        return result


    def _convert_ipv4(self, data: list, _) -> str:
        result = 'None' if 4 != len(data) else '.'.join(f'{(val & 0xFF):d}' for val in data)
        return result


    def _convert_raw(self, data: list, _) -> str:
        result = ' '.join(f'0x{val:02X}' for val in data) if 0 != len(data) else ''
        return result


    def _convert_ascii(self, data: list, _) -> str:
        result = ''.join([chr(val) for val in data]) if 0 != len(data) else ''
        return result


    def _convert_utf8(self, data: list, _) -> str:
        result = bytes(data).decode('utf-8') if 0 != len(data) else ''
        return result


    def _convert(self, data_type: str, data: list, units: dict) -> str:
        func_map = {'bits':     self._convert_bits,
                    'int':      self._convert_int,
                    'uint':     self._convert_uint,
                    'ruint':    self._convert_ruint,
                    'hexint':   self._convert_hexint,
                    'combints': self._convert_combined_ints,
                    'normint':  self._convert_normalizedint,
                    'float':    self._convert_float,
                    'double':   self._convert_double,
                    'dtime0':   self._convert_dtime0,
                    'dtime1':   self._convert_dtime1,
                    'dtime2':   self._convert_dtime2,
                    'dateYMD':  self._convert_date_ymd,
                    'timeHMS':  self._convert_time_hms,
                    'timHMSms': self._convert_time_hms_ms,
                    'weekday':  self._convert_weekday,
                    'flags0':   self._convert_flags0,
                    'flags1':   self._convert_flags1,
                    'blalgo':   self._convert_blalgo,
                    'memtyp':   self._convert_memtyp,
                    'dimtype':  self._convert_dimtype,
                    'reptype':  self._convert_repeattype,
                    'evbutt':   self._convert_evbutton,
                    'evtoken':  self._convert_evtoken,
                    'onoffst':  self._convert_onoffstate,
                    'ledact':   self._convert_ledaction,
                    'pbfunc':   self._convert_playbackfunction,
                    'navkey':   self._convert_navigationfunction,
                    'scrform':  self._convert_screenformat,
                    'devcodi':  self._convert_devicecode_input,
                    'devcodo':  self._convert_devicecode_output,
                    'recfunc':  self._convert_recording_control,
                    'tivocod':  self._convert_tivocode,
                    'medinfo':  self._convert_media_information,
                    'mmedcont': self._convert_multimedia_control,
                    'securevt': self._convert_securevent,
                    'idchkbit': self._convert_id_check_bits,
                    'confstat': self._convert_config_status,
                    'timeunit': self._convert_timeunit,
                    'langcod':  self._convert_langcoding,
                    'pulsecod': self._convert_pulsetypecoding,
                    'measdata': self._convert_measurement_data,
                    'measdatz': self._convert_measurement_zoned_data,
                    'measdatf': self._convert_measurement_32_data,
                    'measdatd': self._convert_measurement_64_data,
                    'measidx':  self._convert_measureindex,
                    'sensidx':  self._convert_sensorindex,
                    'chancod':  self._convert_changecode,
                    'coord':    self._convert_coord,
                    'loglev':   self._convert_loglevel,
                    'ipv4':     self._convert_ipv4,
                    'raw':      self._convert_raw,
                    'ascii':    self._convert_ascii,
                    'utf8':     self._convert_utf8,
                   }
        if data_type not in func_map:
            data_type = 'raw'
        return func_map[data_type](data, units)


def modify_dictionary(input_defs: list, option: str) -> list:
    options = { 'none':    {'type_from':   '',
                            'type_to':     '',
                            'dlc_ins':     {}},
                'addZone': {'type_from':    'measdata',
                            'type_to':      'measdatz',
                            'dlc_ins':     {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                            1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                            2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}},
                'float':   {'type_from':    'measdata',
                            'type_to':      'measdatf',
                            'dlc_ins':     {}},
                'double':  {'type_from':    'measdata',
                            'type_to':      'measdatd',
                            'dlc_ins':     {}}}
    if not option in options:
        option = 'none'
    items = deepcopy(input_defs)
    pos_move = len(options[option]['dlc_ins'])
    for idx, item in enumerate(items):
        if not 'descr' in item: continue # pylint: disable=multiple-statements
        descr = item['descr']
        if not 'dlc' in descr: continue # pylint: disable=multiple-statements
        dlc = descr['dlc']
        for pos in range(len(dlc)): # pylint: disable=consider-using-enumerate
            if 'l' in dlc[pos]:
                dlc[pos]['l'] = dlc[pos]['l'] - pos_move
            if 't' in dlc[pos] and options[option]['type_from'] == dlc[pos]['t']:
                dlc[pos]['t'] = options[option]['type_to']
            dlc[pos + pos_move] = dlc.pop(pos)
        temp_dlc = options[option]['dlc_ins']
        temp_dlc.update(dlc)
        items[idx]['descr']['dlc'] = temp_dlc
    return items


_vscp_priority = [
    {'name': 'Highest',     'id': 0},
    {'name': 'Even higher', 'id': 1},
    {'name': 'Higher',      'id': 2},
    {'name': 'Normal high', 'id': 3},
    {'name': 'Normal low',  'id': 4},
    {'name': 'Lower',       'id': 5},
    {'name': 'Even lower',  'id': 6},
    {'name': 'Lowest',      'id': 7}
]
_class_1_protocol = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'SEGCTRL_HEARTBEAT',                   'id': 1,    'descr': {'str': 'Segment Controller Heartbeat',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Segment GUID CRC'},
                                                                                  1: {'l': 4, 't': 'dtime0', 'd': 'Date/Time'}}
                                                                         }},    # Segment Controller Heartbeat
    {'type': 'NEW_NODE_ONLINE',                     'id': 2,    'descr': {'str': 'New node on line / Probe',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target nickname'}}
                                                                         }},    # New node on line / Probe
    {'type': 'PROBE_ACK',                           'id': 3,    'descr': {'str': 'Probe ACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Probe ACK
    {'type': 'RESERVED4',                           'id': 4,    'descr': {}},   # Reserved for future use
    {'type': 'RESERVED5',                           'id': 5,    'descr': {}},   # Reserved for future use
    {'type': 'SET_NICKNAME',                        'id': 6,    'descr': {'str': 'Set nickname-ID for node',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Old node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'New node ID'}}
                                                                         }},    # Set nickname-ID for node
    {'type': 'NICKNAME_ACCEPTED',                   'id': 7,    'descr': {'str': 'New node ID accepted',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Nickname-ID accepted
    {'type': 'DROP_NICKNAME',                       'id': 8,    'descr': {'str': 'Drop node ID / Reset Device',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Current node ID'},
                                                                                  1: {'l': 1, 't': 'flags0', 'd': 'Flags'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Action wait time'}}
                                                                         }},    # Drop nickname-ID / Reset Device
    {'type': 'READ_REGISTER',                       'id': 9,    'descr': {'str': 'Read register',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Register to read'}}
                                                                         }},    # Read register
    {'type': 'RW_RESPONSE',                         'id': 10,   'descr': {'str': 'Read/Write response',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Register address'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Content of reg.'}}
                                                                         }},    # Read/Write response
    {'type': 'WRITE_REGISTER',                      'id': 11,   'descr': {'str': 'Write register',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Register to write'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'Content of reg.'}}
                                                                         }},    # Write register
    {'type': 'ENTER_BOOT_LOADER',                   'id': 12,   'descr': {'str': 'Enter boot loader mode',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'blalgo', 'd': 'Boot loader algo.'},
                                                                                  2: {'l': 4, 't': 'raw', 'd': 'GUID[0][3][5][7]'},
                                                                                  3: {'l': 2, 't': 'raw', 'd': '#reg.[0x92][0x93]'}}
                                                                         }},    # Enter boot loader mode
    {'type': 'ACK_BOOT_LOADER',                     'id': 13,   'descr': {'str': 'ACK boot loader mode',
                                                                          'dlc': {0: {'l': 4, 't': 'uint', 'd': 'Flash block size'},
                                                                                  1: {'l': 4, 't': 'uint', 'd': 'Number of blocks'}}
                                                                         }},    # ACK boot loader mode
    {'type': 'NACK_BOOT_LOADER',                    'id': 14,   'descr': {'str': 'NACK boot loader mode',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Error code'}}
                                                                         }},    # NACK boot loader mode
    {'type': 'START_BLOCK',                         'id': 15,   'descr': {'str': 'Start block data transfer',
                                                                          'dlc': {0: {'l': 4, 't': 'uint', 'd': 'Block number'},
                                                                                  1: {'l': 1, 't': 'memtyp', 'd': 'Mem. to wr. type'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Memory Bank/Image'}}
                                                                         }},    # Start block data transfer
    {'type': 'BLOCK_DATA',                          'id': 16,   'descr': {'str': 'Block data',
                                                                          'dlc': {0: {'l': 8, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Block data
    {'type': 'BLOCK_DATA_ACK',                      'id': 17,   'descr': {'str': 'ACK data block',
                                                                          'dlc': {0: {'l': 2, 't': 'hexint', 'd': 'CRC for block'},
                                                                                  1: {'l': 4, 't': 'uint', 'd': 'Block number'}}
                                                                         }},    # ACK data block
    {'type': 'BLOCK_DATA_NACK',                     'id': 18,   'descr': {'str': 'NACK data block',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Error code'},
                                                                                  1: {'l': 4, 't': 'uint', 'd': 'Block number'}}
                                                                         }},    # NACK data block
    {'type': 'PROGRAM_BLOCK_DATA',                  'id': 19,   'descr': {'str': 'Program data block',
                                                                          'dlc': {0: {'l': 4, 't': 'uint', 'd': 'Block number'}}
                                                                         }},    # Program data block
    {'type': 'PROGRAM_BLOCK_DATA_ACK',              'id': 20,   'descr': {'str': 'ACK program data block',
                                                                          'dlc': {0: {'l': 4, 't': 'uint', 'd': 'Block number'}}
                                                                         }},    # ACK program data block
    {'type': 'PROGRAM_BLOCK_DATA_NACK',             'id': 21,   'descr': {'str': 'NACK program data block',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Error code'},
                                                                                  1: {'l': 4, 't': 'uint', 'd': 'Block number'}}
                                                                         }},    # NACK program data block
    {'type': 'ACTIVATE_NEW_IMAGE',                  'id': 22,   'descr': {'str': 'Activate new image',
                                                                          'dlc': {0: {'l': 2, 't': 'hexint', 'd': 'CRC of all blocks'}}
                                                                         }},    # Activate new image
    {'type': 'RESET_DEVICE',                        'id': 23,   'descr': {'str': 'GUID drop node ID & reset device',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 4, 't': 'raw', 'd': 'GUID bytes 15..0'}}
                                                                         }},    # GUID drop nickname-ID / reset device
    {'type': 'PAGE_READ',                           'id': 24,   'descr': {'str': 'Page read',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Register to read'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Numb. regs to rd.'}}
                                                                         }},    # Page read
    {'type': 'PAGE_WRITE',                          'id': 25,   'descr': {'str': 'Page write',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Register to write'},
                                                                                  2: {'l': 6, 't': 'raw', 'd': 'Content of reg(s)'}}
                                                                         }},    # Page write
    {'type': 'RW_PAGE_RESPONSE',                    'id': 26,   'descr': {'str': 'Read/Write page response',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  1: {'l': 7, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Read/Write page response
    {'type': 'HIGH_END_SERVER_PROBE',               'id': 27,   'descr': {'str': 'High end server/service probe',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # High end server/service probe
    {'type': 'HIGH_END_SERVER_RESPONSE',            'id': 28,   'descr': {'str': 'High end server/service response',
                                                                          'dlc': {0: {'l': 2, 't': 'flags1', 'd': 'Capability flags'},
                                                                                  1: {'l': 4, 't': 'ipv4', 'd': 'Server IP address'},
                                                                                  2: {'l': 2, 't': 'uint', 'd': 'Server Port'}}
                                                                         }},    # High end server/service response
    {'type': 'INCREMENT_REGISTER',                  'id': 29,   'descr': {'str': 'Increment register',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Reg. to increment'}}
                                                                         }},    # Increment register
    {'type': 'DECREMENT_REGISTER',                  'id': 30,   'descr': {'str': 'Decrement register',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Reg. to decrement'}}
                                                                         }},    # Decrement register
    {'type': 'WHO_IS_THERE',                        'id': 31,   'descr': {'str': 'Who is there?',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'}}
                                                                         }},    # Who is there?
    {'type': 'WHO_IS_THERE_RESPONSE',               'id': 32,   'descr': {'str': 'Who is there response',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Chunk index'},
                                                                                  1: {'l': 7, 't': 'raw', 'd': 'Chunk data'}}
                                                                         }},    # Who is there response
    {'type': 'GET_MATRIX_INFO',                     'id': 33,   'descr': {'str': 'Get decision matrix info',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'}}
                                                                         }},    # Get decision matrix info
    {'type': 'GET_MATRIX_INFO_RESPONSE',            'id': 34,   'descr': {'str': 'Decision matrix info response',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Matrix size'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'Reg. space offset'},
                                                                                  2: {'l': 2, 't': 'uint', 'd': 'Page start'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Page end'}}
                                                                         }},    # Decision matrix info response
    {'type': 'GET_EMBEDDED_MDF',                    'id': 35,   'descr': {'str': 'Get embedded MDF',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'}}
                                                                         }},    # Get embedded MDF
    {'type': 'GET_EMBEDDED_MDF_RESPONSE',           'id': 36,   'descr': {'str': 'Embedded MDF response',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Chunk index'},
                                                                                  1: {'l': 6, 't': 'raw', 'd': 'Chunk data'}}
                                                                         }},    # Embedded MDF response
    {'type': 'EXTENDED_PAGE_READ',                  'id': 37,   'descr': {'str': 'Extended page read register(s)',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 2, 't': 'uint', 'd': 'Reg. page addr.'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'Register to read'},
                                                                                  3: {'l': 1, 't': 'ruint', 'd': 'Numb. regs to rd.'}}
                                                                         }},    # Extended page read register
    {'type': 'EXTENDED_PAGE_WRITE',                 'id': 38,   'descr': {'str': 'Extended page write register(s)',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'},
                                                                                  1: {'l': 2, 't': 'uint', 'd': 'Reg. page addr.'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'Register to write'},
                                                                                  3: {'l': 4, 't': 'raw', 'd': 'Content of reg(s)'}}
                                                                         }},    # Extended page write register
    {'type': 'EXTENDED_PAGE_RESPONSE',              'id': 39,   'descr': {'str': 'Extended page read/write response',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 2, 't': 'uint', 'd': 'Reg. page addr.'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'Reg. read/written'},
                                                                                  3: {'l': 4, 't': 'raw', 'd': 'Content of reg(s)'}}
                                                                         }},    # Extended page read/write response
    {'type': 'GET_EVENT_INTEREST',                  'id': 40,   'descr': {'str': 'Get event interest',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Target node ID'}}
                                                                         }},   # Get event interest
    {'type': 'GET_EVENT_INTEREST_RESPONSE',         'id': 41,   'descr': {'str': 'Get event interest response',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 2, 't': 'hexint', 'd': 'VSCP class ID'},
                                                                                  2: {'l': 2, 't': 'hexint', 'd': 'VSCP type ID'}}
                                                                         }},    # Get event interest response
    {'type': 'ACTIVATE_NEW_IMAGE_ACK',              'id': 48,   'descr': {'str': 'Activate new image ACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Activate new image ACK
    {'type': 'ACTIVATE_NEW_IMAGE_NACK',             'id': 49,   'descr': {'str': 'Activate new image NACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Activate new image NACK
    {'type': 'START_BLOCK_ACK',                     'id': 50,   'descr': {'str': 'Start Block ACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Block data transfer ACK
    {'type': 'START_BLOCK_NACK',                    'id': 51,   'descr': {'str': 'Start Block NACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Block data transfer NACK
    {'type': 'BLOCK_CHUNK_ACK',                     'id': 52,   'descr': {'str': 'Block Data Chunk ACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Block Data Chunk ACK
    {'type': 'BLOCK_CHUNK_NACK',                    'id': 53,   'descr': {'str': 'Block Data Chunk NACK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Block Data Chunk NACK
    {'type': 'BOOT_LOADER_CHECK',                   'id': 54,   'descr': {'str': 'Bootloader CHECK',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Bootloader CHECK
]
_class_1_alarm = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'WARNING',                             'id': 1,    'descr': {'str': 'Warning',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning
    {'type': 'ALARM',                               'id': 2,    'descr': {'str': 'Alarm occurred',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Code'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Alarm occurred
    {'type': 'SOUND',                               'id': 3,    'descr': {'str': 'Alarm sound on/off',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Alarm sound on/off
    {'type': 'LIGHT',                               'id': 4,    'descr': {'str': 'Alarm light on/off',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Alarm light on/off
    {'type': 'POWER',                               'id': 5,    'descr': {'str': 'Power on/off',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Power on/off
    {'type': 'EMERGENCY_STOP',                      'id': 6,    'descr': {'str': 'Emergency Stop',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Emergency Stop
    {'type': 'EMERGENCY_PAUSE',                     'id': 7,    'descr': {'str': 'Emergency Pause',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Emergency Pause
    {'type': 'EMERGENCY_RESET',                     'id': 8,    'descr': {'str': 'Emergency Reset',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Emergency Reset
    {'type': 'EMERGENCY_RESUME',                    'id': 9,    'descr': {'str': 'Emergency Resume',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},  # Emergency Resume
    {'type': 'ARM',                                 'id': 10,   'descr': {'str': 'Arm',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Arm
    {'type': 'DISARM',                              'id': 11,   'descr': {'str': 'Disarm',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Disarm
    {'type': 'WATCHDOG',                            'id': 12,   'descr': {'str': 'Watchdog',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Watchdog
    {'type': 'RESET',                               'id': 13,   'descr': {'str': 'Alarm reset',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Code'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Alarm reset
]
_class_1_security = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'MOTION',                              'id': 1,    'descr': {'str': 'Motion Detect',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'securevt', 'd': 'Status'}}
                                                                         }},    # Motion Detect
    {'type': 'GLASS_BREAK',                         'id': 2,    'descr': {'str': 'Glass break',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Glass break
    {'type': 'BEAM_BREAK',                          'id': 3,    'descr': {'str': 'Beam break',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Beam break
    {'type': 'SENSOR_TAMPER',                       'id': 4,    'descr': {'str': 'Sensor tamper',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sensor tamper
    {'type': 'SHOCK_SENSOR',                        'id': 5,    'descr': {'str': 'Shock sensor',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shock sensor
    {'type': 'SMOKE_SENSOR',                        'id': 6,    'descr': {'str': 'Smoke sensor',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Smoke sensor
    {'type': 'HEAT_SENSOR',                         'id': 7,    'descr': {'str': 'Heat sensor',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Heat sensor
    {'type': 'PANIC_SWITCH',                        'id': 8,    'descr': {'str': 'Panic switch',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Panic switch
    {'type': 'DOOR_OPEN',                           'id': 9,    'descr': {'str': 'Door Contact',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Door Contact
    {'type': 'WINDOW_OPEN',                         'id': 10,   'descr': {'str': 'Window Contact',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Window Contact
    {'type': 'CO_SENSOR',                           'id': 11,   'descr': {'str': 'CO Sensor',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # CO Sensor
    {'type': 'FROST_DETECTED',                      'id': 12,   'descr': {'str': 'Frost detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Frost detected
    {'type': 'FLAME_DETECTED',                      'id': 13,   'descr': {'str': 'Flame detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Flame detected
    {'type': 'OXYGEN_LOW',                          'id': 14,   'descr': {'str': 'Oxygen Low',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Oxygen Low
    {'type': 'WEIGHT_DETECTED',                     'id': 15,   'descr': {'str': 'Weight detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Weight detected
    {'type': 'WATER_DETECTED',                      'id': 16,   'descr': {'str': 'Water detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Water detected
    {'type': 'CONDENSATION_DETECTED',               'id': 17,   'descr': {'str': 'Condensation detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Condensation detected
    {'type': 'SOUND_DETECTED',                      'id': 18,   'descr': {'str': 'Noise (sound) detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Noise (sound) detected
    {'type': 'HARMFUL_SOUND_LEVEL',                 'id': 19,   'descr': {'str': 'Harmful sound levels detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Harmful sound levels detected
    {'type': 'TAMPER',                              'id': 20,   'descr': {'str': 'Tamper detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Tamper detected
    {'type': 'AUTHENTICATED',                       'id': 21,   'descr': {'str': 'Authenticated',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Authenticated
    {'type': 'UNAUTHENTICATED',                     'id': 22,   'descr': {'str': 'Unauthenticated',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Unauthenticated
    {'type': 'AUTHORIZED',                          'id': 23,   'descr': {'str': 'Authorized',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Authorized
    {'type': 'UNAUTHORIZED',                        'id': 24,   'descr': {'str': 'Unauthorized',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Unauthorized
    {'type': 'ID_CHECK',                            'id': 25,   'descr': {'str': 'ID check',
                                                                          'dlc': {0: {'l': 1, 't': 'idchkbit', 'd': 'ID check bits'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # ID check
    {'type': 'PIN_OK',                              'id': 26,   'descr': {'str': 'Valid pin',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Valid pin
    {'type': 'PIN_FAIL',                            'id': 27,   'descr': {'str': 'Invalid pin',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Invalid pin
    {'type': 'PIN_WARNING',                         'id': 28,   'descr': {'str': 'Pin warning',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pin warning
    {'type': 'PIN_ERROR',                           'id': 29,   'descr': {'str': 'Pin error',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pin error
    {'type': 'PASSWORD_OK',                         'id': 30,   'descr': {'str': 'Valid password',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Valid password
    {'type': 'PASSWORD_FAIL',                       'id': 31,   'descr': {'str': 'Invalid password',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Invalid password
    {'type': 'PASSWORD_WARNING',                    'id': 32,   'descr': {'str': 'Password warning',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Password warning
    {'type': 'PASSWORD_ERROR',                      'id': 33,   'descr': {'str': 'Password error',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Password error
    {'type': 'GAS_SENSOR',                          'id': 34,   'descr': {'str': 'Gas has been detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Gas
    {'type': 'IN_MOTION_DETECTED',                  'id': 35,   'descr': {'str': 'In motion',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # In motion
    {'type': 'NOT_IN_MOTION_DETECTED',              'id': 36,   'descr': {'str': 'Not in motion',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Not in motion
    {'type': 'VIBRATION_DETECTED',                  'id': 37,   'descr': {'str': 'Vibration detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Vibration
]
_class_1_measurement = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'COUNT',                               'id': 1,    'descr': {'str': 'Count',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {}                 # no unit
                                                                         }},    # Count
    {'type': 'LENGTH',                              'id': 2,    'descr': {'str': 'Length/Distance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm'}           # meter
                                                                         }},    # Length/Distance
    {'type': 'MASS',                                'id': 3,    'descr': {'str': 'Mass',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'kg'}          # kilogram
                                                                         }},    # Mass
    {'type': 'TIME',                                'id': 4,    'descr': {'str': 'Time',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 's',               # seconds
                                                                                  1: 'ms',              # milliseconds
                                                                                  2: {'t': 'dtime2'},   # y-y-m-d-h-m-s (binary) conversion
                                                                                  3: {'t': 'timeHMS'}}  # string: "HHMMSS"
                                                                         }},    # Time
    {'type': 'ELECTRIC_CURRENT',                    'id': 5,    'descr': {'str': 'Electric Current',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'A'}           # ampere
                                                                         }},    # Electric Current
    {'type': 'TEMPERATURE',                         'id': 6,    'descr': {'str': 'Temperature',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'K',           # Kelvin
                                                                                  1: '°C',          # degree Celsius
                                                                                  2: '°F'}          # degree Fahrenheit
                                                                         }},    # Temperature
    {'type': 'AMOUNT_OF_SUBSTANCE',                 'id': 7,    'descr': {'str': 'Electric Current',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'mol'}         # mole (amount of a substance)
                                                                         }},    # Amount of substance
    {'type': 'INTENSITY_OF_LIGHT',                  'id': 8,    'descr': {'str': 'Luminous Intensity (Intensity of light)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'cd'}          # candela
                                                                         }},    # Luminous Intensity (Intensity of light)
    {'type': 'FREQUENCY',                           'id': 9,    'descr': {'str': 'Frequency',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Hz'}          # hertz
                                                                         }},    # Frequency
    {'type': 'RADIOACTIVITY',                       'id': 10,   'descr': {'str': 'Radioactivity and other random events',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Bq',          # becquerel
                                                                                  1: 'Ci'}          # curie
                                                                         }},    # Radioactivity and other random events
    {'type': 'FORCE',                               'id': 11,   'descr': {'str': 'Force',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'N'}           # newton
                                                                         }},    # Force
    {'type': 'PRESSURE',                            'id': 12,   'descr': {'str': 'Pressure',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Pa',          # pascal
                                                                                  1: 'bar',         # 1 bar ≡ 100 kPa
                                                                                  2: 'psi'}         # pound per square inch
                                                                         }},    # Pressure
    {'type': 'ENERGY',                              'id': 13,   'descr': {'str': 'Energy',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'J',           # joule
                                                                                  1: 'kWh',         # kilowatt hour
                                                                                  2: 'Wh',          # watt hour
                                                                                  3: 'eV'}          # electron volt
                                                                         }},    # Energy
    {'type': 'POWER',                               'id': 14,   'descr': {'str': 'Power',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W',           # watt
                                                                                  1: 'HP (met)',    # horse power metric
                                                                                  2: 'HP (imp)'}    # horse power imperial
                                                                         }},    # Power
    {'type': 'ELECTRICAL_CHARGE',                   'id': 15,   'descr': {'str': 'Electrical Charge',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'C'}           # coulomb
                                                                         }},    # Electrical Charge
    {'type': 'ELECTRICAL_POTENTIAL',                'id': 16,   'descr': {'str': 'Electrical Potential (Voltage)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'V'}           # volt
                                                                         }},    # Electrical Potential (Voltage)
    {'type': 'ELECTRICAL_CAPACITANCE',              'id': 17,   'descr': {'str': 'Electrical Capacitance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'F'}           # farad
                                                                         }},    # Electrical Capacitance
    {'type': 'ELECTRICAL_RESISTANCE',               'id': 18,   'descr': {'str': 'Electrical Resistance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Ω'}           # ohm
                                                                         }},    # Electrical Resistance
    {'type': 'ELECTRICAL_CONDUCTANCE',              'id': 19,   'descr': {'str': 'Electrical Conductance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'S'}           # siemens
                                                                         }},    # Electrical Conductance
    {'type': 'MAGNETIC_FIELD_STRENGTH',             'id': 20,   'descr': {'str': 'Magnetic Field Strength',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'H [A/m]',     # amperes per meter
                                                                                  1: 'Oe'}          # oersted
                                                                         }},    # Magnetic Field Strength
    {'type': 'MAGNETIC_FLUX',                       'id': 21,   'descr': {'str': 'Magnetic Flux',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Wb'}          # weber
                                                                         }},    # Magnetic Flux
    {'type': 'MAGNETIC_FLUX_DENSITY',               'id': 22,   'descr': {'str': 'Magnetic Flux Density',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'T',           # tesla
                                                                                  1: 'G'}           # gauss
                                                                         }},    # Magnetic Flux Density
    {'type': 'INDUCTANCE',                          'id': 23,   'descr': {'str': 'Inductance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'H'}           # henry
                                                                         }},    # Inductance
    {'type': 'FLUX_OF_LIGHT',                       'id': 24,   'descr': {'str': 'Luminous Flux',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'lm'}          # lumen
                                                                         }},    # Luminous Flux
    {'type': 'ILLUMINANCE',                         'id': 25,   'descr': {'str': 'Illuminance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'lx'}          # lux
                                                                         }},    # Illuminance
    {'type': 'RADIATION_DOSE_ABSORBED',             'id': 26,   'descr': {'str': 'Radiation dose (absorbed)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Gy'}          # gray
                                                                         }},    # Radiation dose (absorbed)
    {'type': 'CATALYTIC_ACITIVITY',                 'id': 27,   'descr': {'str': 'Catalytic activity',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'kat'}         # katal - this is a measurement of catalytic activity used in biochemistry
                                                                         }},    # Catalytic activity
    {'type': 'VOLUME',                              'id': 28,   'descr': {'str': 'Volume',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm³',          # cubic meter
                                                                                  1: 'dm³',         # liter
                                                                                  2: 'cm³',         # millilitre
                                                                                  3: '100cm³'}      # decilitre
                                                                         }},    # Volume
    {'type': 'SOUND_INTENSITY',                     'id': 29,   'descr': {'str': 'Sound intensity',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W/m²'}        # watt per square meter
                                                                         }},    # Sound intensity
    {'type': 'ANGLE',                               'id': 30,   'descr': {'str': 'Angle, direction or similar',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'rad',         # radian
                                                                                  1: '°',           # degree
                                                                                  2: '′',           # arcminute
                                                                                  3: '″'}           # arcseconds
                                                                         }},    # Angle, direction or similar
    {'type': 'POSITION',                            'id': 31,   'descr': {'str': 'Position WGS 84',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'λ',           # longitude
                                                                                  1: 'φ'}           # latitude
                                                                         }},    # Position WGS 84
    {'type': 'SPEED',                               'id': 32,   'descr': {'str': 'Speed',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm/s',         # meters per second
                                                                                  1: 'km/h',        # kilometers per hour
                                                                                  2: 'mph',         # miles per hour
                                                                                  3: 'kt'}          # nautical knot
                                                                         }},    # Speed
    {'type': 'ACCELERATION',                        'id': 33,   'descr': {'str': 'Acceleration',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm/s²'}        # metre per second squared
                                                                         }},    # Acceleration
    {'type': 'TENSION',                             'id': 34,   'descr': {'str': 'Tension',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'N/m'}         # niuton per meter
                                                                         }},    # Tension
    {'type': 'HUMIDITY',                            'id': 35,   'descr': {'str': 'Damp/moist (Hygrometer reading)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: '%'}           # relative percentage 0-100%
                                                                         }},    # Damp/moist (Hygrometer reading)
    {'type': 'FLOW',                                'id': 36,   'descr': {'str': 'Flow',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm³/s',        # cubic meters/second
                                                                                  1: 'l/s'}         # liters/second
                                                                         }},    # Flow
    {'type': 'THERMAL_RESISTANCE',                  'id': 37,   'descr': {'str': 'Thermal resistance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'K/W'}         # kelvin per watt - (thermal ohm)
                                                                         }},    # Thermal resistance
    {'type': 'REFRACTIVE_POWER',                    'id': 38,   'descr': {'str': 'Refractive (optical) power',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'dpt'}         # dioptre
                                                                         }},    # Refractive (optical) power
    {'type': 'DYNAMIC_VISCOSITY',                   'id': 39,   'descr': {'str': 'Dynamic viscosity',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Pa·s',        # pascal-second
                                                                                  1: 'Pl',          # poiseuille    1 [Pl] = 1   [Pa·s]
                                                                                  2: 'P'}           # poise         1 [P]  = 0.1 [Pa·s]
                                                                         }},    # Dynamic viscosity
    {'type': 'SOUND_IMPEDANCE',                     'id': 40,   'descr': {'str': 'Sound impedance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Pa·s/m'}      # rayl
                                                                         }},    # Sound impedance
    {'type': 'SOUND_RESISTANCE',                    'id': 41,   'descr': {'str': 'Sound resistance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Pa·s/m³'}     # acoustic ohm
                                                                         }},    # Sound resistance
    {'type': 'ELECTRIC_ELASTANCE',                  'id': 42,   'descr': {'str': 'Electric elastance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'F⁻¹'}         # daraf - inverse farad
                                                                         }},    # Electric elastance
    {'type': 'LUMINOUS_ENERGY',                     'id': 43,   'descr': {'str': 'Luminous energy',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'tb'}          # talbot - lumen-second (tb = lm·s)
                                                                         }},    # Luminous energy
    {'type': 'LUMINANCE',                           'id': 44,   'descr': {'str': 'Luminance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'cd/m²'}       # nit
                                                                         }},    # Luminance
    {'type': 'CHEMICAL_CONCENTRATION_MOLAR',        'id': 45,   'descr': {'str': 'Chemical (molar) concentration',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'mol/m³',      # mole per cubic meter
                                                                                  1: 'ppm',         # parts-per-million
                                                                                  2: '%'}           # percent
                                                                         }},    # Chemical (molar) concentration
    {'type': 'CHEMICAL_CONCENTRATION_MASS',         'id': 46,   'descr': {'str': 'Chemical (mass) concentration',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'kg/m³'}       # kilogram per cubic meter
                                                                         }},    # Chemical (mass) concentration
    {'type': 'RESERVED47',                          'id': 47,   'descr': {}},   # Reserved
    {'type': 'RESERVED48',                          'id': 48,   'descr': {}},   # Reserved
    {'type': 'DEWPOINT',                            'id': 49,   'descr': {'str': 'Dew Point',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'K',           # Kelvin
                                                                                  1: '°C',          # degree Celsius
                                                                                  2: '°F'}          # degree Fahrenheit
                                                                         }},    # Dew Point
    {'type': 'RELATIVE_LEVEL',                      'id': 50,   'descr': {'str': 'Relative Level',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {}                 # no unit
                                                                         }},    # Relative Level
    {'type': 'ALTITUDE',                            'id': 51,   'descr': {'str': 'Altitude',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm',           # meter
                                                                                  1: 'ft',          # foot
                                                                                  2: 'in'}          # inch
                                                                         }},    # Altitude
    {'type': 'AREA',                                'id': 52,   'descr': {'str': 'Area',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'm²',          # square metre
                                                                                  1: 'are',         # 1 are = 100 m²
                                                                                  2: 'hectare',     # 1 hectare = 100 ares = 10000 m² = 0.01 km²
                                                                                  3: 'km²'}         # square kilometer
                                                                         }},    # Area
    {'type': 'RADIANT_INTENSITY',                   'id': 53,   'descr': {'str': 'Radiant intensity',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W/sr'}        # watt per steradian
                                                                         }},     # Radiant intensity
    {'type': 'RADIANCE',                            'id': 54,   'descr': {'str': 'Radiance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W/(sr·m²)'}   # watt per steradian per square metre
                                                                         }},    # Radiance
    {'type': 'IRRADIANCE',                          'id': 55,   'descr': {'str': 'Irradiance, Exitance, Radiosity',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W/m²'}        # watt per square metre
                                                                         }},    # Irradiance, Exitance, Radiosity
    {'type': 'SPECTRAL_RADIANCE',                   'id': 56,   'descr': {'str': 'Spectral radiance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W·sr⁻¹·m⁻²·nm⁻¹', # watt per steradian per square metre per nanometre
                                                                                  1: 'W·sr⁻¹·m⁻³',      # watt per steradian per square metre per metre
                                                                                  2: 'W·sr⁻¹·m⁻²·Hz⁻¹'} # watt per steradian per square metre per hertz
                                                                         }},    # Spectral radiance
    {'type': 'SPECTRAL_IRRADIANCE',                 'id': 57,   'descr': {'str': 'Spectral irradiance',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'W·m⁻²·nm⁻¹',  # watt per square metre per nanometre
                                                                                  1: 'W·m⁻³',       # watt per square metre per metre
                                                                                  2: 'W·m⁻²·Hz⁻¹'}  # watt per square metre per hertz
                                                                         }},    # Spectral irradiance
    {'type': 'SOUND_PRESSURE',                      'id': 58,   'descr': {'str': 'Sound pressure (acoustic pressure)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Pa'}          # pascal
                                                                         }},    # Sound pressure (acoustic pressure)
    {'type': 'SOUND_DENSITY',                       'id': 59,   'descr': {'str': 'Sound energy density',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Pa'}          # pascal
                                                                         }},    # Sound energy density
    {'type': 'SOUND_LEVEL',                         'id': 60,   'descr': {'str': 'Sound level',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'dB'}          # decibel
                                                                         }},    # Sound level
    {'type': 'DOSE_EQVIVALENT',                     'id': 61,   'descr': {'str': 'Radiation dose (equivalent)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'Sv',          # sievert
                                                                                  1: 'rem'}         # Röntgen equivalent in man (1 rem = 0.01 Sv)
                                                                         }},    # Radiation dose (equivalent)
    {'type': 'RADIATION_DOSE_EXPOSURE',             'id': 62,   'descr': {'str': 'Radiation dose (exposure)',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'C/kg',        # coulomb per kilogram
                                                                                  1: 'R'}           # Röntgen
                                                                         }},    # Radiation dose (exposure)
    {'type': 'POWER_FACTOR',                        'id': 63,   'descr': {'str': 'Power factor',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'cos φ'}       # power factor
                                                                         }},    # Power factor
    {'type': 'REACTIVE_POWER',                      'id': 64,   'descr': {'str': 'Reactive Power',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'VAr'}         # reactive power
                                                                         }},    # Reactive Power
    {'type': 'REACTIVE_ENERGY',                     'id': 65,   'descr': {'str': 'Reactive Energy',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: 'kVArh'}       # reactive energy
                                                                         }},    # Reactive Energy
]
_class_1_measurement_x1 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_measurement_x2 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_measurement_x3 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_measurement_x4 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_data = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'IO',                                  'id': 1,    'descr': {'str': 'I/O value',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {}                 # no unit
                                                                         }},    # I/O value
    {'type': 'AD',                                  'id': 2,    'descr': {'str': 'A/D value',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {}                 # no unit
                                                                         }},    # A/D value
    {'type': 'DA',                                  'id': 3,    'descr': {'str': 'D/A value',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {}                 # no unit
                                                                         }},    # D/A value
    {'type': 'RELATIVE_STRENGTH',                   'id': 4,    'descr': {'str': 'Relative strength',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: '',            # no unit
                                                                                  1: 'dB',          # decibel
                                                                                  2: 'dBV'}         # decibel volts
                                                                         }},    # Relative strength
    {'type': 'SIGNAL_LEVEL',                        'id': 5,    'descr': {'str': 'Signal Level',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: '%',           # 0-100 percentage
                                                                                  1: ''}            # no unit
                                                                         }},    # Signal Level
    {'type': 'SIGNAL_QUALITY',                      'id': 6,    'descr': {'str': 'Signal Quality',
                                                                          'dlc': {0: {'l': 8, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {0: '%',           # 0-100 percentage
                                                                                  1: '',            # no unit
                                                                                  2: 'dBm'}         # decibel milliwatts
                                                                         }},    # Signal Quality
]
_class_1_information = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'BUTTON',                              'id': 1,    'descr': {'str': 'Button',
                                                                          'dlc': {0: {'l': 1, 't': 'evbutt', 'd': 'State / Repeats'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Button code'},
                                                                                  4: {'l': 2, 't': 'uint', 'd': 'Code page'}}
                                                                         }},    # Button
    {'type': 'MOUSE',                               'id': 2,    'descr': {'str': 'Mouse',
                                                                          'dlc': {0: {'l': 1, 't': 'coord', 'd': 'Coordinates type'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'int', 'd': 'X-coordinate'},
                                                                                  4: {'l': 2, 't': 'int', 'd': 'Y-coordinate'}}
                                                                         }},    # Mouse
    {'type': 'ON',                                  'id': 3,    'descr': {'str': 'On',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # On
    {'type': 'OFF',                                 'id': 4,    'descr': {'str': 'Off',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Off
    {'type': 'ALIVE',                               'id': 5,    'descr': {'str': 'Alive',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Alive
    {'type': 'TERMINATING',                         'id': 6,    'descr': {'str': 'Terminating',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Terminating
    {'type': 'OPENED',                              'id': 7,    'descr': {'str': 'Opened',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Opened
    {'type': 'CLOSED',                              'id': 8,    'descr': {'str': 'Closed',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Closed
    {'type': 'NODE_HEARTBEAT',                      'id': 9,    'descr': {'str': 'Node Heartbeat',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Node Heartbeat
    {'type': 'BELOW_LIMIT',                         'id': 10,   'descr': {'str': 'Below limit',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Below limit
    {'type': 'ABOVE_LIMIT',                         'id': 11,   'descr': {'str': 'Above limit',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Above limit
    {'type': 'PULSE',                               'id': 12,   'descr': {'str': 'Pulse',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pulse
    {'type': 'ERROR',                               'id': 13,   'descr': {'str': 'Error',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Error
    {'type': 'RESUMED',                             'id': 14,   'descr': {'str': 'Resumed',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Resumed
    {'type': 'PAUSED',                              'id': 15,   'descr': {'str': 'Paused',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Paused
    {'type': 'SLEEP',                               'id': 16,   'descr': {'str': 'Sleeping',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sleeping
    {'type': 'GOOD_MORNING',                        'id': 17,   'descr': {'str': 'Good morning',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Good morning
    {'type': 'GOOD_DAY',                            'id': 18,   'descr': {'str': 'Good day',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Good day
    {'type': 'GOOD_AFTERNOON',                      'id': 19,   'descr': {'str': 'Good afternoon',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Good afternoon
    {'type': 'GOOD_EVENING',                        'id': 20,   'descr': {'str': 'Good evening',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Good evening
    {'type': 'GOOD_NIGHT',                          'id': 21,   'descr': {'str': 'Good night',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Good night
    {'type': 'SEE_YOU_SOON',                        'id': 22,   'descr': {'str': 'See you soon',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # See you soon
    {'type': 'GOODBYE',                             'id': 23,   'descr': {'str': 'Goodbye',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Goodbye
    {'type': 'STOP',                                'id': 24,   'descr': {'str': 'Stop',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Stop
    {'type': 'START',                               'id': 25,   'descr': {'str': 'Start',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Start
    {'type': 'RESET_COMPLETED',                     'id': 26,   'descr': {'str': 'Reset completed',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # ResetCompleted
    {'type': 'INTERRUPTED',                         'id': 27,   'descr': {'str': 'Interrupted',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Interrupted
    {'type': 'PREPARING_TO_SLEEP',                  'id': 28,   'descr': {'str': 'Preparing to sleep',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # PreparingToSleep
    {'type': 'WOKEN_UP',                            'id': 29,   'descr': {'str': 'Woken up',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # WokenUp
    {'type': 'DUSK',                                'id': 30,   'descr': {'str': 'Dusk',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Dusk
    {'type': 'DAWN',                                'id': 31,   'descr': {'str': 'Dawn',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Dawn
    {'type': 'ACTIVE',                              'id': 32,   'descr': {'str': 'Active',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Active
    {'type': 'INACTIVE',                            'id': 33,   'descr': {'str': 'Inactiv',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Inactive
    {'type': 'BUSY',                                'id': 34,   'descr': {'str': 'Busy',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Busy
    {'type': 'IDLE',                                'id': 35,   'descr': {'str': 'Idle',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Idle
    {'type': 'STREAM_DATA',                         'id': 36,   'descr': {'str': 'Stream Data',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  1: {'l': 7, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Stream Data
    {'type': 'TOKEN_ACTIVITY',                      'id': 37,   'descr': {'str': 'Token Activity',
                                                                          'dlc': {0: {'l': 1, 't': 'evtoken', 'd': 'Event/Token type'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  4: {'l': 4, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Token Activity
    {'type': 'STREAM_DATA_WITH_ZONE',               'id': 38,   'descr': {'str': 'Stream Data with zone',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  3: {'l': 5, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Stream Data with zone
    {'type': 'CONFIRM',                             'id': 39,   'descr': {'str': 'Confirm',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  3: {'l': 2, 't': 'hexint', 'd': 'VSCP class ID'},
                                                                                  4: {'l': 2, 't': 'hexint', 'd': 'VSCP type ID'}}
                                                                         }},    # Confirm
    {'type': 'LEVEL_CHANGED',                       'id': 40,   'descr': {'str': 'Level Changed',
                                                                          'dlc': {0: {'l': 1, 't': 'int', 'd': 'Rel/abs lev. val.'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Level Changed
    {'type': 'WARNING',                             'id': 41,   'descr': {'str': 'Warning',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning
    {'type': 'STATE',                               'id': 42,   'descr': {'str': 'State',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'hexint', 'd': 'Changed from'},
                                                                                  4: {'l': 1, 't': 'hexint', 'd': 'New State'}}
                                                                         }},    # State
    {'type': 'ACTION_TRIGGER',                      'id': 43,   'descr': {'str': 'Action trigger',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Action ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Action Trigger
    {'type': 'SUNRISE',                             'id': 44,   'descr': {'str': 'Sunrise',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sunrise
    {'type': 'SUNSET',                              'id': 45,   'descr': {'str': 'Sunset',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sunset
    {'type': 'START_OF_RECORD',                     'id': 46,   'descr': {'str': 'Start of record',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Number of frames'}}
                                                                         }},    # Start of record
    {'type': 'END_OF_RECORD',                       'id': 47,   'descr': {'str': 'End of record',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # End of record
    {'type': 'PRESET_ACTIVE',                       'id': 48,   'descr': {'str': 'Pre-set active',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'hexint', 'd': 'Code for pre-set'}}
                                                                         }},    # Pre-set active
    {'type': 'DETECT',                              'id': 49,   'descr': {'str': 'Detect',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Detect
    {'type': 'OVERFLOW',                            'id': 50,   'descr': {'str': 'Overflow',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Overflow
    {'type': 'BIG_LEVEL_CHANGED',                   'id': 51,   'descr': {'str': 'Big level changed',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'int', 'd': 'Level'}}
                                                                         }},    # Big level changed
    {'type': 'SUNRISE_TWILIGHT_START',              'id': 52,   'descr': {'str': 'Civil sunrise twilight time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Civil sunrise twilight time
    {'type': 'SUNSET_TWILIGHT_START',               'id': 53,   'descr': {'str': 'Civil sunset twilight time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Civil sunset twilight time
    {'type': 'NAUTICAL_SUNRISE_TWILIGHT_START',     'id': 54,   'descr': {'str': 'Nautical sunrise twilight time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Nautical sunrise twilight time
    {'type': 'NAUTICAL_SUNSET_TWILIGHT_START',      'id': 55,   'descr': {'str': 'Nautical sunset twilight time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Nautical sunset twilight time
    {'type': 'ASTRONOMICAL_SUNRISE_TWILIGHT_START', 'id': 56,   'descr': {'str': 'Astronomical sunrise twilight time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Astronomical sunrise twilight time
    {'type': 'ASTRONOMICAL_SUNSET_TWILIGHT_START',  'id': 57,   'descr': {'str': 'Astronomical sunset twilight time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Astronomical sunset twilight time
    {'type': 'CALCULATED_NOON',                     'id': 58,   'descr': {'str': 'Calculated Noon',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Calculated Noon
    {'type': 'SHUTTER_UP',                          'id': 59,   'descr': {'str': 'Shutter up',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter up
    {'type': 'SHUTTER_DOWN',                        'id': 60,   'descr': {'str': 'Shutter down',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter down
    {'type': 'SHUTTER_LEFT',                        'id': 61,   'descr': {'str': 'Shutter left',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter left
    {'type': 'SHUTTER_RIGHT',                       'id': 62,   'descr': {'str': 'Shutter right',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter right
    {'type': 'SHUTTER_END_TOP',                     'id': 63,   'descr': {'str': 'Shutter reached top end',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter reached top end
    {'type': 'SHUTTER_END_BOTTOM',                  'id': 64,   'descr': {'str': 'Shutter reached bottom end',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter reached bottom end
    {'type': 'SHUTTER_END_MIDDLE',                  'id': 65,   'descr': {'str': 'Shutter reached middle end',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter reached middle end
    {'type': 'SHUTTER_END_PRESET',                  'id': 66,   'descr': {'str': 'Shutter reached preset end',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter reached preset end
    {'type': 'SHUTTER_END_LEFT',                    'id': 67,   'descr': {'str': 'Shutter reached preset left',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter reached preset left
    {'type': 'SHUTTER_END_RIGHT',                   'id': 68,   'descr': {'str': 'Shutter reached preset right',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Shutter reached preset right
    {'type': 'LONG_CLICK',                          'id': 69,   'descr': {'str': 'Long click',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Long click
    {'type': 'SINGLE_CLICK',                        'id': 70,   'descr': {'str': 'Single click',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Single click
    {'type': 'DOUBLE_CLICK',                        'id': 71,   'descr': {'str': 'Double click',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Double click
    {'type': 'DATE',                                'id': 72,   'descr': {'str': 'Date',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 4, 't': 'dateYMD', 'd': 'Date'}}
                                                                         }},    # Date
    {'type': 'TIME',                                'id': 73,   'descr': {'str': 'Time',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'timHMSms', 'd': 'Time'}}
                                                                         }},    # Time
    {'type': 'WEEKDAY',                             'id': 74,   'descr': {'str': 'Weekday',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'weekday', 'd': 'Weekday'}}
                                                                         }},    # Weekday
    {'type': 'LOCK',                                'id': 75,   'descr': {'str': 'Lock',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Lock
    {'type': 'UNLOCK',                              'id': 76,   'descr': {'str': 'Unlock',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Unlock
    {'type': 'DATETIME',                            'id': 77,   'descr': {'str': 'Date & Time',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Device index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'dtime1', 'd': 'Date/Time'}}
                                                                         }},   # DateTime
    {'type': 'RISING',                              'id': 78,   'descr': {'str': 'Rising',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Rising
    {'type': 'FALLING',                             'id': 79,   'descr': {'str': 'Falling',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Falling
    {'type': 'UPDATED',                             'id': 80,   'descr': {'str': 'Updated',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Updated
    {'type': 'CONNECT',                             'id': 81,   'descr': {'str': 'Connect',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Connect
    {'type': 'DISCONNECT',                          'id': 82,   'descr': {'str': 'Disconnect',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Disconnect
    {'type': 'RECONNECT',                           'id': 83,   'descr': {'str': 'Reconnect',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Reconnect
    {'type': 'ENTER',                               'id': 84,   'descr': {'str': 'Enter',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Enter
    {'type': 'EXIT',                                'id': 85,   'descr': {'str': 'Exit',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Exit
    {'type': 'INCREMENTED',                         'id': 86,   'descr': {'str': 'Incremented',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Value'}}
                                                                         }},    # Incremented
    {'type': 'DECREMENTED',                         'id': 87,   'descr': {'str': 'Decremented',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Value'}}
                                                                         }},    # Decremented
    {'type': 'PROXIMITY_DETECTED',                  'id': 88,   'descr': {'str': 'Proximity detected',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Proximity val.'}}
                                                                         }},    # Proximity detected
]
_class_1_control = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'MUTE',                                'id': 1,    'descr': {'str': 'Mute on/off',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'Mute'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Mute on/off
    {'type': 'ALL_LAMPS',                           'id': 2,    'descr': {'str': '(All) Lamp(s) on/off',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'State'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # (All) Lamp(s) on/off
    {'type': 'OPEN',                                'id': 3,    'descr': {'str': 'Open',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Open
    {'type': 'CLOSE',                               'id': 4,    'descr': {'str': 'Close',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Close
    {'type': 'TURNON',                              'id': 5,    'descr': {'str': 'Turn On',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # TurnOn
    {'type': 'TURNOFF',                             'id': 6,    'descr': {'str': 'Turn Off',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # TurnOff
    {'type': 'START',                               'id': 7,    'descr': {'str': 'Start',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Start
    {'type': 'STOP',                                'id': 8,    'descr': {'str': 'Stop',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Stop
    {'type': 'RESET',                               'id': 9,    'descr': {'str': 'Reset',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Reset
    {'type': 'INTERRUPT',                           'id': 10,   'descr': {'str': 'Interrupt',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Level'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Interrupt
    {'type': 'SLEEP',                               'id': 11,   'descr': {'str': 'Sleep',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sleep
    {'type': 'WAKEUP',                              'id': 12,   'descr': {'str': 'Wake up',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Wakeup
    {'type': 'RESUME',                              'id': 13,   'descr': {'str': 'Resume',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Resume
    {'type': 'PAUSE',                               'id': 14,   'descr': {'str': 'Pause',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pause
    {'type': 'ACTIVATE',                            'id': 15,   'descr': {'str': 'Activate',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Activate
    {'type': 'DEACTIVATE',                          'id': 16,   'descr': {'str': 'Deactivate',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Deactivate
    {'type': 'TURN_ALL_OFF',                        'id': 17,   'descr': {'str': 'Set all devices off',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Set all devices off
    {'type': 'TURN_ALL_ON',                         'id': 18,   'descr': {'str': 'Set all devices on',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},   # Set all devices on
    {'type': 'TURN_ALL_X',                          'id': 19,   'descr': {'str': 'Set all device on/off as of argument',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'onoffst', 'd': 'State'}}
                                                                         }},    # Set all device on/off as of argument
    {'type': 'DIM_LAMPS',                           'id': 20,   'descr': {'str': 'Dim lamp(s)',
                                                                          'dlc': {0: {'l': 1, 't': 'dimtype', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Dim lamp(s)
    {'type': 'CHANGE_CHANNEL',                      'id': 21,   'descr': {'str': 'Change Channel',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Channel number'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Extended'}}
                                                                         }},    # Change Channel
    {'type': 'CHANGE_LEVEL',                        'id': 22,   'descr': {'str': 'Change Level',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Absolute level'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Change Level
    {'type': 'RELATIVE_CHANGE_LEVEL',               'id': 23,   'descr': {'str': 'Relative Change Level',
                                                                          'dlc': {0: {'l': 1, 't': 'int', 'd': 'Relative level'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Relative Change Level
    {'type': 'MEASUREMENT_REQUEST',                 'id': 24,   'descr': {'str': 'Measurement Request',
                                                                          'dlc': {0: {'l': 1, 't': 'measidx', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Measurement Request
    {'type': 'STREAM_DATA',                         'id': 25,   'descr': {'str': 'Stream Data',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  1: {'l': 7, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Stream Data
    {'type': 'SYNC',                                'id': 26,   'descr': {'str': 'Sync',
                                                                          'dlc': {0: {'l': 1, 't': 'sensidx', 'd': 'Sensor index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sync
    {'type': 'ZONED_STREAM_DATA',                   'id': 27,   'descr': {'str': 'Zoned Stream Data',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Sequence number'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Zoned Stream Data
    {'type': 'SET_PRESET',                          'id': 28,   'descr': {'str': 'Set Pre-set',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Code for pre-set'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Set Pre-set
    {'type': 'TOGGLE_STATE',                        'id': 29,   'descr': {'str': 'Toggle state',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Toggle state
    {'type': 'TIMED_PULSE_ON',                      'id': 30,   'descr': {'str': 'Timed pulse on',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'pulsecod', 'd': 'Control byte'},
                                                                                  4: {'l': 4, 't': 'uint', 'd': 'Time-On'}}
                                                                         }},    # Timed pulse on
    {'type': 'TIMED_PULSE_OFF',                     'id': 31,   'descr': {'str': 'Timed pulse off',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'pulsecod', 'd': 'Control byte'},
                                                                                  4: {'l': 4, 't': 'uint', 'd': 'Time-Off'}}
                                                                         }},    # Timed pulse off
    {'type': 'SET_COUNTRY_LANGUAGE',                'id': 32,   'descr': {'str': 'Set country/language',
                                                                          'dlc': {0: {'l': 1, 't': 'langcod', 'd': 'Code type'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'ascii', 'd': 'Language code'}}
                                                                         }},    # Set country/language
    {'type': 'BIG_CHANGE_LEVEL',                    'id': 33,   'descr': {'str': 'Big Change level',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'int', 'd': 'Level'}}
                                                                         }},    # Big Change level
    {'type': 'SHUTTER_UP',                          'id': 34,   'descr': {'str': 'Move shutter up',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Move shutter up
    {'type': 'SHUTTER_DOWN',                        'id': 35,   'descr': {'str': 'Move shutter down',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Move shutter down
    {'type': 'SHUTTER_LEFT',                        'id': 36,   'descr': {'str': 'Move shutter left',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Move shutter left
    {'type': 'SHUTTER_RIGHT',                       'id': 37,   'descr': {'str': 'Move shutter right',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Move shutter right
    {'type': 'SHUTTER_MIDDLE',                      'id': 38,   'descr': {'str': 'Move shutter to middle position',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Move shutter to middle position
    {'type': 'SHUTTER_PRESET',                      'id': 39,   'descr': {'str': 'Move shutter to preset position',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Position'}}
                                                                         }},    # Move shutter to preset position
    {'type': 'ALL_LAMPS_ON',                        'id': 40,   'descr': {'str': '(All) Lamp(s) on',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # (All) Lamp(s) on
    {'type': 'ALL_LAMPS_OFF',                       'id': 41,   'descr': {'str': '(All) Lamp(s) off',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # (All) Lamp(s) off
    {'type': 'LOCK',                                'id': 42,   'descr': {'str': 'Lock',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Lock
    {'type': 'UNLOCK',                              'id': 43,   'descr': {'str': 'Unlock',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Unlock
    {'type': 'PWM',                                 'id': 44,   'descr': {'str': 'PWM set',
                                                                          'dlc': {0: {'l': 1, 't': 'reptype', 'd': 'Repeat/counter'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'timeunit', 'd': 'Control byte'},
                                                                                  4: {'l': 2, 't': 'uint', 'd': 'Time-On'},
                                                                                  5: {'l': 2, 't': 'uint', 'd': 'Time-Off'}}
                                                                         }},    # PWM set
    {'type': 'TOKEN_LOCK',                          'id': 45,   'descr': {'str': 'Lock with token',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Token'}}
                                                                         }},    # Lock with token
    {'type': 'TOKEN_UNLOCK',                        'id': 46,   'descr': {'str': 'Unlock with token',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Token'}}
                                                                         }},    # Unlock with token
    {'type': 'SET_SECURITY_LEVEL',                  'id': 47,   'descr': {'str': 'Set security level',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Security level'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Set security level
    {'type': 'SET_SECURITY_PIN',                    'id': 48,   'descr': {'str': 'Set security pin',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Pin'}}
                                                                         }},    # Set security pin
    {'type': 'SET_SECURITY_PASSWORD',               'id': 49,   'descr': {'str': 'Set security password',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'utf8', 'd': 'Password'}}
                                                                         }},    # Set security password
    {'type': 'SET_SECURITY_TOKEN',                  'id': 50,   'descr': {'str': 'Set security token',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Token'}}
                                                                         }},    # Set security token
    {'type': 'REQUEST_SECURITY_TOKEN',              'id': 51,   'descr': {'str': 'Request new security token',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Request new security token
    {'type': 'INCREMENT',                           'id': 52,   'descr': {'str': 'Increment',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Value'}}
                                                                         }},    # Increment
    {'type': 'DECREMENT',                           'id': 53,   'descr': {'str': 'Decrement',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Value'}}
                                                                         }},    # Decrement
]
_class_1_multimedia = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'PLAYBACK',                            'id': 1,    'descr': {'str': 'Playback',
                                                                          'dlc': {0: {'l': 1, 't': 'pbfunc', 'd': 'Function'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Playback
    {'type': 'NAVIGATOR_KEY_ENG',                   'id': 2,    'descr': {'str': 'NavigatorKey English',
                                                                          'dlc': {0: {'l': 1, 't': 'navkey', 'd': 'Function'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # NavigatorKey English
    {'type': 'ADJUST_CONTRAST',                     'id': 3,    'descr': {'str': 'Adjust Contrast',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Contrast
    {'type': 'ADJUST_FOCUS',                        'id': 4,    'descr': {'str': 'Adjust Focus',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Focus
    {'type': 'ADJUST_TINT',                         'id': 5,    'descr': {'str': 'Adjust Tint',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Tint
    {'type': 'ADJUST_COLOUR_BALANCE',               'id': 6,    'descr': {'str': 'Adjust Color Balance',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Color Balance
    {'type': 'ADJUST_BRIGHTNESS',                   'id': 7,    'descr': {'str': 'Adjust Brightness',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Brightness
    {'type': 'ADJUST_HUE',                          'id': 8,    'descr': {'str': 'Adjust Hue',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Hue
    {'type': 'ADJUST_BASS',                         'id': 9,    'descr': {'str': 'Adjust Bass',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Bass
    {'type': 'ADJUST_TREBLE',                       'id': 10,   'descr': {'str': 'Adjust Treble',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Treble
    {'type': 'ADJUST_MASTER_VOLUME',                'id': 11,   'descr': {'str': 'Adjust Master Volume',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Master Volume
    {'type': 'ADJUST_FRONT_VOLUME',                 'id': 12,   'descr': {'str': 'Adjust Front Volume',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Front Volume
    {'type': 'ADJUST_CENTRE_VOLUME',                'id': 13,   'descr': {'str': 'Adjust Center Volume',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Center Volume
    {'type': 'ADJUST_REAR_VOLUME',                  'id': 14,   'descr': {'str': 'Adjust Rear Volume',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Rear Volume
    {'type': 'ADJUST_SIDE_VOLUME',                  'id': 15,   'descr': {'str': 'Adjust Side Volume',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Adjust Side Volume
    {'type': 'RESERVED16',                          'id': 16,   'descr': {}},   # Reserved
    {'type': 'RESERVED17',                          'id': 17,   'descr': {}},   # Reserved
    {'type': 'RESERVED18',                          'id': 18,   'descr': {}},   # Reserved
    {'type': 'RESERVED19',                          'id': 19,   'descr': {}},   # Reserved
    {'type': 'ADJUST_SELECT_DISK',                  'id': 20,   'descr': {'str': 'Select Disk',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Disk
    {'type': 'ADJUST_SELECT_TRACK',                 'id': 21,   'descr': {'str': 'Select Track',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Track
    {'type': 'ADJUST_SELECT_ALBUM',                 'id': 22,   'descr': {'str': 'Select Album/Play list',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Album/Play list
    {'type': 'ADJUST_SELECT_CHANNEL',               'id': 23,   'descr': {'str': 'Select Channel',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Channel
    {'type': 'ADJUST_SELECT_PAGE',                  'id': 24,   'descr': {'str': 'Select Page',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Page
    {'type': 'ADJUST_SELECT_CHAPTER',               'id': 25,   'descr': {'str': 'Select Chapter',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Chapter
    {'type': 'ADJUST_SELECT_SCREEN_FORMAT',         'id': 26,   'descr': {'str': 'Select Screen Format',
                                                                          'dlc': {0: {'l': 1, 't': 'scrform', 'd': 'Format'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Screen Format
    {'type': 'ADJUST_SELECT_INPUT_SOURCE',          'id': 27,   'descr': {'str': 'Select Input Source',
                                                                          'dlc': {0: {'l': 1, 't': 'devcodi', 'd': 'Source'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Input Source
    {'type': 'ADJUST_SELECT_OUTPUT',                'id': 28,   'descr': {'str': 'Select Input Source',
                                                                          'dlc': {0: {'l': 1, 't': 'devcodo', 'd': 'Output'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Select Output
    {'type': 'RECORD',                              'id': 29,   'descr': {'str': 'Select Input Source',
                                                                          'dlc': {0: {'l': 1, 't': 'recfunc', 'd': 'Output'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Record
    {'type': 'SET_RECORDING_VOLUME',                'id': 30,   'descr': {'str': 'Set Recording Volume',
                                                                          'dlc': {0: {'l': 1, 't': 'chancod', 'd': 'Value'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Set Recording Volume
    {'type': 'TIVO_FUNCTION',                       'id': 40,   'descr': {'str': 'Tivo Function',
                                                                          'dlc': {0: {'l': 1, 't': 'tivocod', 'd': 'TIVO Code'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Tivo Function
    {'type': 'GET_CURRENT_TITLE',                   'id': 50,   'descr': {'str': 'Get Current Title',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Get Current Title
    {'type': 'SET_POSITION',                        'id': 51,   'descr': {'str': 'Set media position in milliseconds',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'uint', 'd': 'Position [ms]'}}
                                                                         }},    # Set media position in milliseconds
    {'type': 'GET_MEDIA_INFO',                      'id': 52,   'descr': {'str': 'Get media information',
                                                                          'dlc': {0: {'l': 1, 't': 'medinfo', 'd': 'Info req.'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Get media information
    {'type': 'REMOVE_ITEM',                         'id': 53,   'descr': {'str': 'Remove Item from Album',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Item/Track ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Remove Item from Album
    {'type': 'REMOVE_ALL_ITEMS',                    'id': 54,   'descr': {'str': 'Remove all Items from Album',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Reserved'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Remove all Items from Album
    {'type': 'SAVE_ALBUM',                          'id': 55,   'descr': {'str': 'Save Album/Play list',
                                                                          'dlc': {0: {'l': 1, 't': 'onoffst', 'd': 'Overwr. existing'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Save Album/Play list
    {'type': 'CONTROL',                             'id': 60,   'descr': {'str': 'Save Album/Play list',
                                                                          'dlc': {0: {'l': 1, 't': 'mmedcont', 'd': 'Control code'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  4: {'l': 4, 't': 'utf8', 'd': 'Data'}}
                                                                         }},    # Multimedia Control
    {'type': 'CONTROL_RESPONSE',                    'id': 61,   'descr': {'str': 'Multimedia Control response',
                                                                          'dlc': {0: {'l': 0, 't': 'none', 'd': 'no arguments'}}
                                                                         }},    # Multimedia Control response
]
_class_1_aol = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'UNPLUGGED_POWER',                     'id': 1,    'descr': {'str': 'System unplugged from power source',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # System unplugged from power source
    {'type': 'UNPLUGGED_LAN',                       'id': 2,    'descr': {'str': 'System unplugged from network',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # System unplugged from network
    {'type': 'CHASSIS_INTRUSION',                   'id': 3,    'descr': {'str': 'Chassis intrusion',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Chassis intrusion
    {'type': 'PROCESSOR_REMOVAL',                   'id': 4,    'descr': {'str': 'Processor removal',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Processor removal
    {'type': 'ENVIRONMENT_ERROR',                   'id': 5,    'descr': {'str': 'System environmental errors',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # System environmental errors
    {'type': 'HIGH_TEMPERATURE',                    'id': 6,    'descr': {'str': 'High temperature',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # High temperature
    {'type': 'FAN_SPEED',                           'id': 7,    'descr': {'str': 'Fan speed problem',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Fan speed problem
    {'type': 'VOLTAGE_FLUCTUATIONS',                'id': 8,    'descr': {'str': 'Voltage fluctuations',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Voltage fluctuations
    {'type': 'OS_ERROR',                            'id': 9,    'descr': {'str': 'Operating system errors',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Operating system errors
    {'type': 'POWER_ON_ERROR',                      'id': 10,   'descr': {'str': 'System power-on error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # System power-on error
    {'type': 'SYSTEM_HUNG',                         'id': 11,   'descr': {'str': 'System is hung',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # System is hung
    {'type': 'COMPONENT_FAILURE',                   'id': 12,   'descr': {'str': 'Component failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Component failure
    {'type': 'REBOOT_UPON_FAILURE',                 'id': 13,   'descr': {'str': 'Remote system reboot upon report of a critical failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Remote system reboot upon report of a critical failure
    {'type': 'REPAIR_OPERATING_SYSTEM',             'id': 14,   'descr': {'str': 'Repair Operating System',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Repair Operating System
    {'type': 'UPDATE_BIOS_IMAGE',                   'id': 15,   'descr': {'str': 'Update BIOS image',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Update BIOS image
    {'type': 'UPDATE_DIAGNOSTIC_PROCEDURE',         'id': 16,   'descr': {'str': 'Update Perform other diagnostic procedures',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index for record'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Update Perform other diagnostic procedures
]
_class_1_measurement_64 = modify_dictionary(_class_1_measurement, 'double')
_class_1_measurement_64_x1 = _class_1_measurement_x1
_class_1_measurement_64_x2 = _class_1_measurement_x2
_class_1_measurement_64_x3 = _class_1_measurement_x3
_class_1_measurement_64_x4 = _class_1_measurement_x4
_class_1_measure_zone = modify_dictionary(_class_1_measurement, 'addZone')
_class_1_measure_zone_x1 = _class_1_measurement_x1
_class_1_measure_zone_x2 = _class_1_measurement_x2
_class_1_measure_zone_x3 = _class_1_measurement_x3
_class_1_measure_zone_x4 = _class_1_measurement_x4
_class_1_measurement_32 = modify_dictionary(_class_1_measurement, 'float')
_class_1_measurement_32_x1 = _class_1_measurement_x1
_class_1_measurement_32_x2 = _class_1_measurement_x2
_class_1_measurement_32_x3 = _class_1_measurement_x3
_class_1_measurement_32_x4 = _class_1_measurement_x4
_class_1_set_value_zone = modify_dictionary(_class_1_measurement, 'addZone')
_class_1_set_value_zone_x1 = _class_1_measurement_x1
_class_1_set_value_zone_x2 = _class_1_measurement_x2
_class_1_set_value_zone_x3 = _class_1_measurement_x3
_class_1_set_value_zone_x4 = _class_1_measurement_x4
_class_1_weather = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'SEASONS_WINTER',                      'id': 1,    'descr': {'str': 'Season winter',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Season winter
    {'type': 'SEASONS_SPRING',                      'id': 2,    'descr': {'str': 'Season spring',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Season spring
    {'type': 'SEASONS_SUMMER',                      'id': 3,    'descr': {'str': 'Season summer',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Season summer
    {'type': 'SEASONS_AUTUMN',                      'id': 4,    'descr': {'str': 'Season autumn',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Season autumn
    {'type': 'WIND_NONE',                           'id': 5,    'descr': {'str': 'No wind',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # No wind
    {'type': 'WIND_LOW',                            'id': 6,    'descr': {'str': 'Low wind',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Low wind
    {'type': 'WIND_MEDIUM',                         'id': 7,    'descr': {'str': 'Medium wind',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Medium wind
    {'type': 'WIND_HIGH',                           'id': 8,    'descr': {'str': 'High wind',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # High wind
    {'type': 'WIND_VERY_HIGH',                      'id': 9,    'descr': {'str': 'Very high wind',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Very high wind
    {'type': 'AIR_FOGGY',                           'id': 10,   'descr': {'str': 'Air foggy',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air foggy
    {'type': 'AIR_FREEZING',                        'id': 11,   'descr': {'str': 'Air freezing',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air freezing
    {'type': 'AIR_VERY_COLD',                       'id': 12,   'descr': {'str': 'Air Very cold',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air Very cold
    {'type': 'AIR_COLD',                            'id': 13,   'descr': {'str': 'Air cold',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air cold
    {'type': 'AIR_NORMAL',                          'id': 14,   'descr': {'str': 'Air normal',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air normal
    {'type': 'AIR_HOT',                             'id': 15,   'descr': {'str': 'Air hot',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air hot
    {'type': 'AIR_VERY_HOT',                        'id': 16,   'descr': {'str': 'Air very hot',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air very hot
    {'type': 'AIR_POLLUTION_LOW',                   'id': 17,   'descr': {'str': 'Pollution low',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pollution low
    {'type': 'AIR_POLLUTION_MEDIUM',                'id': 18,   'descr': {'str': 'Pollution medium',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pollution medium
    {'type': 'AIR_POLLUTION_HIGH',                  'id': 19,   'descr': {'str': 'Pollution high',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Pollution high
    {'type': 'AIR_HUMID',                           'id': 20,   'descr': {'str': 'Air humid',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air humid
    {'type': 'AIR_DRY',                             'id': 21,   'descr': {'str': 'Air dry',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Air dry
    {'type': 'SOIL_HUMID',                          'id': 22,   'descr': {'str': 'Soil humid',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Soil humid
    {'type': 'SOIL_DRY',                            'id': 23,   'descr': {'str': 'Soil dry',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Soil dry
    {'type': 'RAIN_NONE',                           'id': 24,   'descr': {'str': 'Rain none',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Rain none
    {'type': 'RAIN_LIGHT',                          'id': 25,   'descr': {'str': 'Rain light',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Rain light
    {'type': 'RAIN_HEAVY',                          'id': 26,   'descr': {'str': 'Rain heavy',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Rain heavy
    {'type': 'RAIN_VERY_HEAVY',                     'id': 27,   'descr': {'str': 'Rain very heavy',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Rain very heavy
    {'type': 'SUN_NONE',                            'id': 28,   'descr': {'str': 'Sun none',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sun none
    {'type': 'SUN_LIGHT',                           'id': 29,   'descr': {'str': 'Sun light',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sun light
    {'type': 'SUN_HEAVY',                           'id': 30,   'descr': {'str': 'Sun heavy',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Sun heavy
    {'type': 'SNOW_NONE',                           'id': 31,   'descr': {'str': 'Snow none',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Snow none
    {'type': 'SNOW_LIGHT',                          'id': 32,   'descr': {'str': 'Snow light',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Snow light
    {'type': 'SNOW_HEAVY',                          'id': 33,   'descr': {'str': 'Snow heavy',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Snow heavy
    {'type': 'DEW_POINT',                           'id': 34,   'descr': {'str': 'Dew point',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Dew point
    {'type': 'STORM',                               'id': 35,   'descr': {'str': 'Storm',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Storm
    {'type': 'FLOOD',                               'id': 36,   'descr': {'str': 'Flood',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Flood
    {'type': 'EARTHQUAKE',                          'id': 37,   'descr': {'str': 'Earthquake',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Earthquake
    {'type': 'NUCLEAR_DISASTER',                    'id': 38,   'descr': {'str': 'Nuclear disaster',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Nuclear disaster
    {'type': 'FIRE',                                'id': 39,   'descr': {'str': 'Fire',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Fire
    {'type': 'LIGHTNING',                           'id': 40,   'descr': {'str': 'Lightning',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Lightning
    {'type': 'UV_RADIATION_LOW',                    'id': 41,   'descr': {'str': 'UV Radiation low',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # UV Radiation low
    {'type': 'UV_RADIATION_MEDIUM',                 'id': 42,   'descr': {'str': 'UV Radiation medium',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # UV Radiation medium
    {'type': 'UV_RADIATION_NORMAL',                 'id': 43,   'descr': {'str': 'UV Radiation normal',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # UV Radiation normal
    {'type': 'UV_RADIATION_HIGH',                   'id': 44,   'descr': {'str': 'UV Radiation high',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # UV Radiation high
    {'type': 'UV_RADIATION_VERY_HIGH',              'id': 45,   'descr': {'str': 'UV Radiation very high',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # UV Radiation very high
    {'type': 'WARNING_LEVEL1',                      'id': 46,   'descr': {'str': 'Warning level 1',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning level 1
    {'type': 'WARNING_LEVEL2',                      'id': 47,   'descr': {'str': 'Warning level 2',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning level 2
    {'type': 'WARNING_LEVEL3',                      'id': 48,   'descr': {'str': 'Warning level 3',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning level 3
    {'type': 'WARNING_LEVEL4',                      'id': 49,   'descr': {'str': 'Warning level 4',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning level 4
    {'type': 'WARNING_LEVEL5',                      'id': 50,   'descr': {'str': 'Warning level 5',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Warning level 5
    {'type': 'ARMAGEDON',                           'id': 51,   'descr': {'str': 'Armageddon',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Armageddon
    {'type': 'UV_INDEX',                            'id': 52,   'descr': {'str': 'UV Index',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'UV Index (0-15)'}}
                                                                         }},    # UV Index
]
_class_1_weather_forecast = _class_1_weather
_class_1_phone = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'INCOMING_CALL',                       'id': 1,    'descr': {'str': 'Incoming call',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'Chunk index'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Total chunks'},
                                                                                  3: {'l': 1, 't': 'utf8', 'd': 'Call information'}}
                                                                         }},    # Incoming call
    {'type': 'OUTGOING_CALL',                       'id': 2,    'descr': {'str': 'Outgoing call',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'Chunk index'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Total chunks'},
                                                                                  3: {'l': 1, 't': 'utf8', 'd': 'Call information'}}
                                                                         }},    # Outgoing call
    {'type': 'RING',                                'id': 3,    'descr': {'str': 'Ring',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'}}
                                                                         }},    # Ring
    {'type': 'ANSWER',                              'id': 4,    'descr': {'str': 'Answer',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Answer
    {'type': 'HANGUP',                              'id': 5,    'descr': {'str': 'Hangup',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'}}
                                                                         }},    # Hangup
    {'type': 'GIVEUP',                              'id': 6,    'descr': {'str': 'Giveup',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'}}
                                                                         }},    # Giveup
    {'type': 'TRANSFER',                            'id': 7,    'descr': {'str': 'Transfer',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'}}
                                                                         }},    # Transfer
    {'type': 'DATABASE_INFO',                       'id': 8,    'descr': {'str': 'Database Info',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Call ID'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'Chunk index'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Total chunks'},
                                                                                  3: {'l': 1, 't': 'utf8', 'd': 'Call information'}}
                                                                         }},    # Database Info
]
_class_1_display = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'CLEAR_DISPLAY',                       'id': 1,    'descr': {'str': 'Clear Display',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Code'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Clear Display
    {'type': 'POSITION_CURSOR',                     'id': 2,    'descr': {'str': 'Position cursor',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Row'},
                                                                                  4: {'l': 1, 't': 'uint', 'd': 'Column'}}
                                                                         }},    # Position cursor
    {'type': 'WRITE_DISPLAY',                       'id': 3,    'descr': {'str': 'Write Display',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Write Display
    {'type': 'WRITE_DISPLAY_BUFFER',                'id': 4,    'descr': {'str': 'Write Display buffer',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Write Display buffer
    {'type': 'SHOW_DISPLAY_BUFFER',                 'id': 5,    'descr': {'str': 'Show Display Buffer',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},    # Show Display Buffer
    {'type': 'SET_DISPLAY_BUFFER_PARAM',            'id': 6,    'descr': {'str': 'Set Display Buffer Parameter',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Param. index'},
                                                                                  1: {'l': 7, 't': 'measdata', 'd': 'Value'}},
                                                                          'uni': {}                 # no unit
                                                                         }},    # Set Display Buffer Parameter
    {'type': 'SHOW_TEXT',                           'id': 32,   'descr': {'str': 'Show Text',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'raw', 'd': 'Data'}}
                                                                         }},    # Show Text
    {'type': 'SET_LED',                             'id': 48,   'descr': {'str': 'Set LED',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'ledact', 'd': 'Action'},
                                                                                  4: {'l': 2, 't': 'uint', 'd': 'Time-On [ms]'},
                                                                                  5: {'l': 2, 't': 'uint', 'd': 'Time-Off [ms]'}}
                                                                         }},    # Set LED
    {'type': 'SET_COLOR',                           'id': 49,   'descr': {'str': 'Set RGB Color',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Red'},
                                                                                  4: {'l': 1, 't': 'uint', 'd': 'Green'},
                                                                                  5: {'l': 1, 't': 'uint', 'd': 'Blue'}}
                                                                         }},    # Set RGB Color
]
_class_1_remote = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'RC5',                                 'id': 1,    'descr': {'str': 'RC5 Send/Receive',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'RC5 code'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'RC5 address'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Repeat count'}}
                                                                         }},    # RC5 Send/Receive
    {'type': 'SONY12',                              'id': 3,    'descr': {'str': 'SONY 12-bit Send/Receive',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'SONY code'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'SONY address'},
                                                                                  2: {'l': 1, 't': 'uint', 'd': 'Repeat count'}}
                                                                         }},    # SONY 12-bit Send/Receive
    {'type': 'LIRC',                                'id': 32,   'descr': {'str': 'LIRC (Linux Infrared Remote Control) Code',
                                                                          'dlc': {0: {'l': 7, 't': 'hexint', 'd': 'Code'},
                                                                                  1: {'l': 1, 't': 'uint', 'd': 'Repeat count'}}
                                                                         }},    # LIRC (Linux Infrared Remote Control)
    {'type': 'VSCP',                                'id': 48,   'descr': {'str': 'VSCP Abstract Remote Format',
                                                                          'dlc': {0: {'l': 2, 't': 'hexint', 'd': 'Code'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 1, 't': 'uint', 'd': 'Repeat count'}}
                                                                         }},    # VSCP Abstract Remote Format
    {'type': 'MAPITO',                              'id': 49,   'descr': {'str': 'MAPito Remote Format',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Repeat count'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 4, 't': 'hexint', 'd': 'Control address'},
                                                                                  4: {'l': 1, 't': 'hexint', 'd': 'Key code'}}
                                                                         }},    # MAPito Remote Format
]
_class_1_configuration = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'LOAD',                                'id': 1,    'descr': {'str': 'Load configuration',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Configuration ID'},
                                                                                  4: {'l': 1, 't': 'confstat', 'd': 'Control byte'}}
                                                                         }},    # Load configuration
    {'type': 'LOAD_ACK',                            'id': 2,    'descr': {'str': 'Load configuration acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Load configuration acknowledge
    {'type': 'LOAD_NACK',                           'id': 3,    'descr': {'str': 'Load configuration negative acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Load configuration negative acknowledge
    {'type': 'SAVE',                                'id': 4,    'descr': {'str': 'Save configuration',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Configuration ID'},
                                                                                  4: {'l': 1, 't': 'confstat', 'd': 'Control byte'}}
                                                                         }},    # Save configuration
    {'type': 'SAVE_ACK',                            'id': 5,    'descr': {'str': 'Save configuration acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Save configuration acknowledge
    {'type': 'SAVE_NACK',                           'id': 6,    'descr': {'str': 'Save configuration negative acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Save configuration negative acknowledge
    {'type': 'COMMIT',                              'id': 7,    'descr': {'str': 'Commit configuration',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Configuration ID'},
                                                                                  4: {'l': 1, 't': 'confstat', 'd': 'Control byte'}}
                                                                         }},    # Commit configuration
    {'type': 'COMMIT_ACK',                          'id': 8,    'descr': {'str': 'Commit configuration acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Commit configuration acknowledge
    {'type': 'COMMIT_NACK',                         'id': 9,    'descr': {'str': 'Commit configuration negative acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Commit configuration negative acknowledge
    {'type': 'RELOAD',                              'id': 10,   'descr': {'str': 'Reload configuration',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Configuration ID'},
                                                                                  4: {'l': 1, 't': 'confstat', 'd': 'Control byte'}}
                                                                         }},    # Reload configuration
    {'type': 'REALOD_ACK',                          'id': 11,   'descr': {'str': 'Reload configuration acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Reload configuration acknowledge
    {'type': 'RELOAD_NACK',                         'id': 12,   'descr': {'str': 'Reload configuration negative acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Reload configuration negative acknowledge
    {'type': 'RESTORE',                             'id': 13,   'descr': {'str': 'Restore configuration',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Configuration ID'},
                                                                                  4: {'l': 1, 't': 'confstat', 'd': 'Control byte'}}
                                                                         }},    # Restore configuration
    {'type': 'RESTORE_ACK',                         'id': 14,   'descr': {'str': 'Restore configuration acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Restore configuration acknowledge
    {'type': 'RESTORE_NACK',                        'id': 15,   'descr': {'str': 'Restore configuration negative acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Restore configuration negative acknowledge
    {'type': 'SET_PARAMETER',                       'id': 30,   'descr': {'str': 'Set parameter',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Parameter ID'},
                                                                                  4: {'l': 2, 't': 'combints', 'd': 'Value'}}
                                                                         }},    # Set parameter
    {'type': 'SET_PARAMETER_DEFAULT',               'id': 31,   'descr': {'str': 'Set parameter to default',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 2, 't': 'uint', 'd': 'Parameter ID'}}
                                                                         }},    # Set parameter to default
    {'type': 'SET_PARAMETER_ACK',                   'id': 32,   'descr': {'str': 'Set parameter acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Set parameter acknowledge
    {'type': 'SET_PARAMETER_NACK',                  'id': 33,   'descr': {'str': 'Set paramter negative acknowledge',
                                                                          'dlc': {0: {'l': 2, 't': 'uint', 'd': 'Configuration ID'}}
                                                                         }},    # Set paramter negative acknowledge
]
_class_1_gnss = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'POSITION',                            'id': 1,    'descr': {'str': 'Position',
                                                                          'dlc': {0: {'l': 4, 't': 'float', 'd': 'Latitude'},
                                                                                  1: {'l': 4, 't': 'float', 'd': 'Longitude'}}
                                                                         }},    # Position
    {'type': 'SATELLITES',                          'id': 2,    'descr': {'str': 'Satellites',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Count'}}
                                                                         }},    # Satellites
]
_class_1_wireless = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'GSM_CELL',                            'id': 1,    'descr': {'str': 'GSM Cell',
                                                                          'dlc': {0: {'l': 8, 't': 'hexint', 'd': 'Cell ID'}}
                                                                         }},    # GSM Cell
]
_class_1_diagnostic = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'OVERVOLTAGE',                         'id': 1,    'descr': {'str': 'Overvoltage',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Overvoltage
    {'type': 'UNDERVOLTAGE',                        'id': 2,    'descr': {'str': 'Undervoltage',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Undervoltage
    {'type': 'VBUS_LOW',                            'id': 3,    'descr': {'str': 'USB VBUS low',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # USB VBUS low
    {'type': 'BATTERY_LOW',                         'id': 4,    'descr': {'str': 'Battery voltage low',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Battery voltage low
    {'type': 'BATTERY_FULL',                        'id': 5,    'descr': {'str': 'Battery full voltage',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Battery full voltage
    {'type': 'BATTERY_ERROR',                       'id': 6,    'descr': {'str': 'Battery error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Battery error
    {'type': 'BATTERY_OK',                          'id': 7,    'descr': {'str': 'Battery OK',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Battery OK
    {'type': 'OVERCURRENT',                         'id': 8,    'descr': {'str': 'Over current',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Over current
    {'type': 'CIRCUIT_ERROR',                       'id': 9,    'descr': {'str': 'Circuit error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Circuit error
    {'type': 'SHORT_CIRCUIT',                       'id': 10,   'descr': {'str': 'Short circuit',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Short circuit
    {'type': 'OPEN_CIRCUIT',                        'id': 11,   'descr': {'str': 'Open Circuit',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Open Circuit
    {'type': 'MOIST',                               'id': 12,   'descr': {'str': 'Moist',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Moist
    {'type': 'WIRE_FAIL',                           'id': 13,   'descr': {'str': 'Wire failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Wire failure
    {'type': 'WIRELESS_FAIL',                       'id': 14,   'descr': {'str': 'Wireless faliure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Wireless faliure
    {'type': 'IR_FAIL',                             'id': 15,   'descr': {'str': 'IR failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # IR failure
    {'type': '1WIRE_FAIL',                          'id': 16,   'descr': {'str': '1-wire failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # 1-wire failure
    {'type': 'RS222_FAIL',                          'id': 17,   'descr': {'str': 'RS-222 failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # RS-222 failure
    {'type': 'RS232_FAIL',                          'id': 18,   'descr': {'str': 'RS-232 failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # RS-232 failure
    {'type': 'RS423_FAIL',                          'id': 19,   'descr': {'str': 'RS-423 failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # RS-423 failure
    {'type': 'RS485_FAIL',                          'id': 20,   'descr': {'str': 'RS-485 failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # RS-485 failure
    {'type': 'CAN_FAIL',                            'id': 21,   'descr': {'str': 'CAN failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # CAN failure
    {'type': 'LAN_FAIL',                            'id': 22,   'descr': {'str': 'LAN failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # LAN failure
    {'type': 'USB_FAIL',                            'id': 23,   'descr': {'str': 'USB failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # USB failure
    {'type': 'WIFI_FAIL',                           'id': 24,   'descr': {'str': 'Wifi failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Wifi failure
    {'type': 'NFC_RFID_FAIL',                       'id': 25,   'descr': {'str': 'NFC/RFID failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # NFC/RFID failure
    {'type': 'LOW_SIGNAL',                          'id': 26,   'descr': {'str': 'Low signal',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Low signal
    {'type': 'HIGH_SIGNAL',                         'id': 27,   'descr': {'str': 'High signal',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # High signal
    {'type': 'ADC_FAIL',                            'id': 28,   'descr': {'str': 'ADC failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # ADC failure
    {'type': 'ALU_FAIL',                            'id': 29,   'descr': {'str': 'ALU failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # ALU failure
    {'type': 'ASSERT',                              'id': 30,   'descr': {'str': 'Assert',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Assert
    {'type': 'DAC_FAIL',                            'id': 31,   'descr': {'str': 'DAC failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # DAC failure
    {'type': 'DMA_FAIL',                            'id': 32,   'descr': {'str': 'DMA failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # DMA failure
    {'type': 'ETH_FAIL',                            'id': 33,   'descr': {'str': 'Ethernet failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Ethernet failure
    {'type': 'EXCEPTION',                           'id': 34,   'descr': {'str': 'Exception',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Exception
    {'type': 'FPU_FAIL',                            'id': 35,   'descr': {'str': 'FPU failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # FPU failure
    {'type': 'GPIO_FAIL',                           'id': 36,   'descr': {'str': 'GPIO failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # GPIO failure
    {'type': 'I2C_FAIL',                            'id': 37,   'descr': {'str': 'I2C failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # I2C failure
    {'type': 'I2S_FAIL',                            'id': 38,   'descr': {'str': 'I2S failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # I2S failure
    {'type': 'INVALID_CONFIG',                      'id': 39,   'descr': {'str': 'Invalid configuration',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Invalid configuration
    {'type': 'MMU_FAIL',                            'id': 40,   'descr': {'str': 'MMU failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # MMU failure
    {'type': 'NMI',                                 'id': 41,   'descr': {'str': 'NMI failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # NMI failure
    {'type': 'OVERHEAT',                            'id': 42,   'descr': {'str': 'Overheat',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Overheat
    {'type': 'PLL_FAIL',                            'id': 43,   'descr': {'str': 'PLL fail',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # PLL fail
    {'type': 'POR_FAIL',                            'id': 44,   'descr': {'str': 'POR failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # POR failure
    {'type': 'PWM_FAIL',                            'id': 45,   'descr': {'str': 'PWM failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # PWM failure
    {'type': 'RAM_FAIL',                            'id': 46,   'descr': {'str': 'RAM failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # RAM failure
    {'type': 'ROM_FAIL',                            'id': 47,   'descr': {'str': 'ROM failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # ROM failure
    {'type': 'SPI_FAIL',                            'id': 48,   'descr': {'str': 'SPI failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # SPI failure
    {'type': 'STACK_FAIL',                          'id': 49,   'descr': {'str': 'Stack failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Stack failure
    {'type': 'LIN_FAIL',                            'id': 50,   'descr': {'str': 'LIN bus failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # LIN bus failure
    {'type': 'UART_FAIL',                           'id': 51,   'descr': {'str': 'UART failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # UART failure
    {'type': 'UNHANDLED_INT',                       'id': 52,   'descr': {'str': 'Unhandled interrupt',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Unhandled interrupt
    {'type': 'MEMORY_FAIL',                         'id': 53,   'descr': {'str': 'Memory failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Memory failure
    {'type': 'VARIABLE_RANGE',                      'id': 54,   'descr': {'str': 'Variable range failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Variable range failure
    {'type': 'WDT',                                 'id': 55,   'descr': {'str': 'WDT failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # WDT failure
    {'type': 'EEPROM_FAIL',                         'id': 56,   'descr': {'str': 'EEPROM failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # EEPROM failure
    {'type': 'ENCRYPTION_FAIL',                     'id': 57,   'descr': {'str': 'Encryption failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Encryption failure
    {'type': 'BAD_USER_INPUT',                      'id': 58,   'descr': {'str': 'Bad user input failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Bad user input failure
    {'type': 'DECRYPTION_FAIL',                     'id': 59,   'descr': {'str': 'Decryption failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Decryption failure
    {'type': 'NOISE',                               'id': 60,   'descr': {'str': 'Noise',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Noise
    {'type': 'BOOTLOADER_FAIL',                     'id': 61,   'descr': {'str': 'Boot loader failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Boot loader failure
    {'type': 'PROGRAMFLOW_FAIL',                    'id': 62,   'descr': {'str': 'Program flow failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Program flow failure
    {'type': 'RTC_FAIL',                            'id': 63,   'descr': {'str': 'RTC faiure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # RTC faiure
    {'type': 'SYSTEM_TEST_FAIL',                    'id': 64,   'descr': {'str': 'System test failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # System test failure
    {'type': 'SENSOR_FAIL',                         'id': 65,   'descr': {'str': 'Sensor failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Sensor failure
    {'type': 'SAFESTATE',                           'id': 66,   'descr': {'str': 'Safe state entered',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Safe state entered
    {'type': 'SIGNAL_IMPLAUSIBLE',                  'id': 67,   'descr': {'str': 'Signal implausible',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Signal implausible
    {'type': 'STORAGE_FAIL',                        'id': 68,   'descr': {'str': 'Storage fail',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Storage fail
    {'type': 'SELFTEST_FAIL',                       'id': 69,   'descr': {'str': 'Self test OK',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Self test OK
    {'type': 'ESD_EMC_EMI',                         'id': 70,   'descr': {'str': 'ESD/EMC/EMI failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},  # ESD/EMC/EMI failure
    {'type': 'TIMEOUT',                             'id': 71,   'descr': {'str': 'Timeout',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Timeout
    {'type': 'LCD_FAIL',                            'id': 72,   'descr': {'str': 'LCD failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # LCD failure
    {'type': 'TOUCHPANEL_FAIL',                     'id': 73,   'descr': {'str': 'Touch panel failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Touch panel failure
    {'type': 'NOLOAD',                              'id': 74,   'descr': {'str': 'No load',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # No load
    {'type': 'COOLING_FAIL',                        'id': 75,   'descr': {'str': 'Cooling failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Cooling failure
    {'type': 'HEATING_FAIL',                        'id': 76,   'descr': {'str': 'Heating failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Heating failure
    {'type': 'TX_FAIL',                             'id': 77,   'descr': {'str': 'Transmission failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Transmission failure
    {'type': 'RX_FAIL',                             'id': 78,   'descr': {'str': 'Receiption failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Receiption failure
    {'type': 'EXT_IC_FAIL',                         'id': 79,   'descr': {'str': 'External IC failure',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # External IC failure
    {'type': 'CHARGING_ON',                         'id': 80,   'descr': {'str': 'Charging of battery or similar has started or in progress',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Charging of battery or similar has started or is in progress
    {'type': 'CHARGING_OFF',                        'id': 81,   'descr': {'str': 'Charging of battery or similar has ended',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Charging of battery or similar has ended
]
_class_1_error = [
    {'type': 'SUCCESS',                             'id': 0,    'descr': {'str': 'Success',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Success
    {'type': 'ERROR',                               'id': 1,    'descr': {'str': 'Error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Error
    {'type': 'CHANNEL',                             'id': 7,    'descr': {'str': 'Channel error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Channel error
    {'type': 'FIFO_EMPTY',                          'id': 8,    'descr': {'str': 'Fifo empty error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Fifo empty error
    {'type': 'FIFO_FULL',                           'id': 9,    'descr': {'str': 'Fifo full error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Fifo full error
    {'type': 'FIFO_SIZE',                           'id': 10,   'descr': {'str': 'Fifo size error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Fifo size error
    {'type': 'FIFO_WAIT',                           'id': 11,   'descr': {'str': 'Fifo wait error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Fifo wait error
    {'type': 'GENERIC',                             'id': 12,   'descr': {'str': 'Generic error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Generic error
    {'type': 'HARDWARE',                            'id': 13,   'descr': {'str': 'Hardware error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Hardware error
    {'type': 'INIT_FAIL',                           'id': 14,   'descr': {'str': 'Initialization error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # initialization error
    {'type': 'INIT_MISSING',                        'id': 15,   'descr': {'str': 'Missing initialization error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Missing initialization error
    {'type': 'INIT_READY',                          'id': 16,   'descr': {'str': 'Initialization ready',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Initialization ready
    {'type': 'NOT_SUPPORTED',                       'id': 17,   'descr': {'str': 'Not supported',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Not supported
    {'type': 'OVERRUN',                             'id': 18,   'descr': {'str': 'Overrun error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Overrun error
    {'type': 'RCV_EMPTY',                           'id': 19,   'descr': {'str': 'Receiver empty error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Receiver empty error
    {'type': 'REGISTER',                            'id': 20,   'descr': {'str': 'Register error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Register error
    {'type': 'TRM_FULL',                            'id': 21,   'descr': {'str': 'Transmitter full error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Transmitter full error
    {'type': 'LIBRARY',                             'id': 28,   'descr': {'str': 'Library error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Library error
    {'type': 'PROCADDRESS',                         'id': 29,   'descr': {'str': 'Procedural address error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Procedural address error
    {'type': 'ONLY_ONE_INSTANCE',                   'id': 30,   'descr': {'str': 'Only one instance error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Only one instance error
    {'type': 'SUB_DRIVER',                          'id': 31,   'descr': {'str': 'Sub driver error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Sub driver error
    {'type': 'TIMEOUT',                             'id': 32,   'descr': {'str': 'Timeout error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Timeout error
    {'type': 'NOT_OPEN',                            'id': 33,   'descr': {'str': 'Not open error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Not open error
    {'type': 'PARAMETER',                           'id': 34,   'descr': {'str': 'Parameter error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Parameter error
    {'type': 'MEMORY',                              'id': 35,   'descr': {'str': 'Memory error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Memory error
    {'type': 'INTERNAL',                            'id': 36,   'descr': {'str': 'Internal error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Internal error
    {'type': 'COMMUNICATION',                       'id': 37,   'descr': {'str': 'Communication error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Communication error
    {'type': 'USER',                                'id': 38,   'descr': {'str': 'User error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # User error
    {'type': 'PASSWORD',                            'id': 39,   'descr': {'str': 'Password error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Password error
    {'type': 'CONNECTION',                          'id': 40,   'descr': {'str': 'Connection error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Connection error
    {'type': 'INVALID_HANDLE',                      'id': 41,   'descr': {'str': 'nvalid handle error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Invalid handle error
    {'type': 'OPERATION_FAILED',                    'id': 42,   'descr': {'str': 'Operation failed error',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Operation failed error
    {'type': 'BUFFER_SMALL',                        'id': 43,   'descr': {'str': 'Supplied buffer is to small to fit content',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Supplied buffer is to small to fit content
    {'type': 'ITEM_UNKNOWN',                        'id': 44,   'descr': {'str': 'Requested item is unknown',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Requested item is unknown
    {'type': 'NAME_USED',                           'id': 45,   'descr': {'str': 'Name is already in use',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Name is already in use
    {'type': 'DATA_WRITE',                          'id': 46,   'descr': {'str': 'Error when writing data',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Error when writing data
    {'type': 'ABORTED',                             'id': 47,   'descr': {'str': 'Operation stopped or aborted',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Operation stopped or aborted
    {'type': 'INVALID_POINTER',                     'id': 48,   'descr': {'str': 'Pointer with invalid value',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'hexint', 'd': 'User specific'}}
                                                                         }},    # Pointer with invalid value
]
_class_1_log = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},   # General event
    {'type': 'MESSAGE',                             'id': 1,    'descr': {'str': 'Log event',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Event ID'},
                                                                                  1: {'l': 1, 't': 'loglev', 'd': 'Msg. log level'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'Msg. index'},
                                                                                  3: {'l': 5, 't': 'ascii', 'd': 'Message'}}
                                                                         }},    # Log event
    {'type': 'START',                               'id': 2,    'descr': {'str': 'Start logging',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Log ID'}}
                                                                         }},    # Log Start
    {'type': 'STOP',                                'id': 3,    'descr': {'str': 'Stop logging',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Log ID'}}
                                                                         }},    # Log Stop
    {'type': 'LEVEL',                               'id': 4,    'descr': {'str': 'Set level for logging',
                                                                          'dlc': {0: {'l': 1, 't': 'loglev', 'd': 'Level'}}
                                                                         }},    # Log Level

]
_class_1_laboratory = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_local = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_vscp_class_1_dict = [
    {'class': 'CLASS1.PROTOCOL',            'id': 0,    'types': _class_1_protocol},            # VSCP Protocol Functionality
    {'class': 'CLASS1.ALARM',               'id': 1,    'types': _class_1_alarm},               # Alarm functionality
    {'class': 'CLASS1.SECURITY',            'id': 2,    'types': _class_1_security},            # Security
    {'class': 'CLASS1.MEASUREMENT',         'id': 10,   'types': _class_1_measurement},         # Measurement
    {'class': 'CLASS1.MEASUREMENTX1',       'id': 11,   'types': _class_1_measurement_x1},      # Measurement
    {'class': 'CLASS1.MEASUREMENTX2',       'id': 12,   'types': _class_1_measurement_x2},      # Measurement
    {'class': 'CLASS1.MEASUREMENTX3',       'id': 13,   'types': _class_1_measurement_x3},      # Measurement
    {'class': 'CLASS1.MEASUREMENTX4',       'id': 14,   'types': _class_1_measurement_x4},      # Measurement
    {'class': 'CLASS1.DATA',                'id': 15,   'types': _class_1_data},                # Data
    {'class': 'CLASS1.INFORMATION',         'id': 20,   'types': _class_1_information},         # Information
    {'class': 'CLASS1.CONTROL',             'id': 30,   'types': _class_1_control},             # Control
    {'class': 'CLASS1.MULTIMEDIA',          'id': 40,   'types': _class_1_multimedia},          # Multimedia
    {'class': 'CLASS1.AOL',                 'id': 50,   'types': _class_1_aol},                 # Alert On LAN
    {'class': 'CLASS1.MEASUREMENT64',       'id': 60,   'types': _class_1_measurement_64},      # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X1',     'id': 61,   'types': _class_1_measurement_64_x1},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X2',     'id': 62,   'types': _class_1_measurement_64_x2},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X3',     'id': 63,   'types': _class_1_measurement_64_x3},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X4',     'id': 64,   'types': _class_1_measurement_64_x4},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREZONE',         'id': 65,   'types': _class_1_measure_zone},        # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX1',       'id': 66,   'types': _class_1_measure_zone_x1},     # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX2',       'id': 67,   'types': _class_1_measure_zone_x2},     # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX3',       'id': 68,   'types': _class_1_measure_zone_x3},     # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX4',       'id': 69,   'types': _class_1_measure_zone_x4},     # Measurement with zone
    {'class': 'CLASS1.MEASUREMENT32',       'id': 70,   'types': _class_1_measurement_32},      # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X1',     'id': 71,   'types': _class_1_measurement_32_x1},   # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X2',     'id': 72,   'types': _class_1_measurement_32_x2},   # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X3',     'id': 73,   'types': _class_1_measurement_32_x3},   # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X4',     'id': 74,   'types': _class_1_measurement_32_x4},   # Single precision floating point measurement
    {'class': 'CLASS1.SETVALUEZONE',        'id': 85,   'types': _class_1_set_value_zone},      # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX1',      'id': 86,   'types': _class_1_set_value_zone_x1},   # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX2',      'id': 87,   'types': _class_1_set_value_zone_x2},   # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX3',      'id': 88,   'types': _class_1_set_value_zone_x3},   # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX4',      'id': 89,   'types': _class_1_set_value_zone_x4},   # Set value with zone
    {'class': 'CLASS1.WEATHER',             'id': 90,   'types': _class_1_weather},             # Weather
    {'class': 'CLASS1.WEATHER_FORECAST',    'id': 95,   'types': _class_1_weather_forecast},    # Weather forecast
    {'class': 'CLASS1.PHONE',               'id': 100,  'types': _class_1_phone},               # Phone
    {'class': 'CLASS1.DISPLAY',             'id': 102,  'types': _class_1_display},             # Display
    {'class': 'CLASS1.IR',                  'id': 110,  'types': _class_1_remote},              # IR Remote I/f
    {'class': 'CLASS1.CONFIGURATION',       'id': 120,  'types': _class_1_configuration},       # Configuration
    {'class': 'CLASS1.GNSS',                'id': 206,  'types': _class_1_gnss},                # Position (GNSS)
    {'class': 'CLASS1.WIRELESS',            'id': 212,  'types': _class_1_wireless},            # Wireless
    {'class': 'CLASS1.DIAGNOSTIC',          'id': 506,  'types': _class_1_diagnostic},          # Diagnostic
    {'class': 'CLASS1.ERROR',               'id': 508,  'types': _class_1_error},               # Error
    {'class': 'CLASS1.LOG',                 'id': 509,  'types': _class_1_log},                 # Logging
    {'class': 'CLASS1.LABORATORY',          'id': 510,  'types': _class_1_laboratory},          # Laboratory use
    {'class': 'CLASS1.LOCAL',               'id': 511,  'types': _class_1_local}                # Local use
]


dictionary = Dictionary()
