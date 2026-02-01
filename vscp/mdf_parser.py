"""
Module Description File (MDF) Parser.

This module provides the MdfParser class to parse VSCP Module Description Files
in both XML and JSON formats. It extracts module information, register definitions,
and other device-specific data.
"""

import pprint # TODO remove
import re
import json
import xmltodict


class MdfParser:
    """
    Parses VSCP Module Description Files (MDF).

    Supports loading MDF content from XML or JSON strings and provides methods
    to retrieve module metadata, manufacturer info, and register maps.
    """
    def __init__(self):
        """Initializes the MdfParser with an empty state."""
        self.mdf = {}
        self.source = 'none'
        self.sync_read = '●'
        self.sync_write = '⬤'


    def parse(self, data: str) -> None:
        """
        Parses the provided MDF data string.

        Detects whether the data is XML or JSON and populates the internal
        structure accordingly.

        Args:
            data (str): The MDF content as a string (XML or JSON).
        """
        try:
            substr = str(data[:32])
            pos_xml = substr.find('<')
            pos_json = substr.find('{')
            if -1 != pos_xml:
                self.mdf = xmltodict.parse(data)
                self.mdf = self.mdf.get('vscp', {}).get('module', {})
                self.source = 'xml'
            elif -1 != pos_json:
                self.mdf = json.loads(data)
                self.mdf = self.mdf.get('module', {})
                self.source = 'json'
            else:
                self.mdf = {}
                self.source = 'none'
        except ValueError:
            self.mdf = {}


    def get(self) -> dict:
        """
        Retrieves the raw parsed MDF dictionary.

        Returns:
            dict: The parsed MDF structure.
        """
        return self.mdf


    def parse_variable(self, lang: str, var) -> str:
        """
        Extracts a variable value, potentially handling language selection.

        Args:
            lang (str): The language code (not currently used in logic but reserved).
            var: The variable to parse (dict or value).

        Returns:
            str: The value of the variable.
        """
        result = var.get(lang, '') if isinstance(var, dict) else var
        return result

    def get_module_info(self) -> dict:
        """
        Extracts high-level module information.

        Includes name, model, version, description, buffer size, etc.
        Normalizes XML data if necessary.

        Returns:
            dict: A dictionary containing module information.
        """
        result = {}
        result['name']          = self.mdf.get('name', '')
        result['model']         = self.mdf.get('model', '')
        result['version']       = self.mdf.get('version', '')
        result['description']   = self.mdf.get('description', '')
        result['infourl']       = self.mdf.get('infourl', '')
        result['buffersize']    = self.mdf.get('buffersize', '')
        result['level']         = self.mdf.get('level', '1')
        result['changed']       = self.mdf.get('changed', '')
        if 'xml' == self.source:
            result = self._normalize_xml_keys(result)
            keys = ['description', 'name', 'infourl']
            for key in keys:
                value = result.get(key, None)
                if value is not None:
                    result[key] = self._normalize_xml_values(value)
        result['description'] = self._get_eng_text(result['description'], True)
        return result


    def get_module_manufacturer(self) -> dict: # TODO parse data
        """
        Retrieves manufacturer information from the MDF.

        Returns:
            dict: Manufacturer details.
        """
        result = self.mdf.get('manufacturer', {})
        return result


    def get_boot_algorithm(self) -> dict:
        """
        Retrieves bootloader algorithm information.

        Returns:
            dict: A dictionary with 'algorithm', 'blockcount', and 'blocksize' keys.
        """
        boot = self.mdf.get('boot', {})
        if 'algorithm' in boot and 'blockcount' in boot and 'blocksize' in boot:
            result = {'algorithm':  boot['algorithm'],
                      'blockcount': boot['blockcount'],
                      'blocksize':  boot['blocksize']
                      }
        else:
            result = {}
        return result


    def get_registers_info(self) -> dict:
        """
        Constructs a complete map of device registers.

        Combines standard VSCP registers with device-specific registers defined
        in the MDF.

        Returns:
            dict: A nested dictionary mapping page -> offset -> register info.
        """
        result = self._get_standard_registers()
        data = self._parse_registers_data()
        # pp = pprint.PrettyPrinter(indent=2, width=160) # TODO remove
        # pp.pprint(data)
        for item in data: # pylint: disable=too-many-nested-blocks
            if 'page' in item:
                try:
                    page = int(str(item['page']), 0)
                    offset = int(str(item['offset']), 0)
                    if 0x80 > offset:
                        reg_type = item.get('type', 'std')
                        span = int(str(item.get('span', '1')), 0)
                        record = {
                            'access':       self._normalize_access_value(item['access']), # pylint: disable=line-too-long # TODO dmatrix fail
                            'value':        f"0x{max(min(0xFF, int(str(item.get('default', '0xFF')), 0)), 0):02X}", # pylint: disable=line-too-long
                            'to_sync':      self.sync_read,
                            'name':         self._get_eng_text(item['name'], False),
                            'description':  self._get_eng_text(item.get('description', ''), False),
                            'type':         reg_type,
                            'span':         span,
                        }
                        fg = item.get('fgcolor', 'invalid')
                        bg = item.get('bgcolor', 'invalid')
                        valid_fg = self._isrgbcolor(fg)
                        valid_bg = self._isrgbcolor(bg)
                        if valid_fg or valid_bg:
                            colors = {}
                            if valid_fg:
                                colors['fgcolor'] = fg
                            if valid_bg:
                                colors['bgcolor'] = bg
                            record['colors'] = colors
                        reg_page = result.get(page, None) # TODO unroll if span > 1
                        if reg_page is None:
                            result[page] = {offset: record}
                        else:
                            reg_page[offset] = record
                            result[page] = reg_page
                except: # pylint: disable=bare-except
                    pass
        return result


    def _isrgbcolor(self, value: str) -> bool:
        rgbstring = re.compile(r'0[xX][a-fA-F0-9]{6}$')
        return bool(rgbstring.match(value))


    def _parse_registers_data(self) -> list:
        match self.source:
            case 'xml':
                data = self.mdf.get('registers', {}).get('reg', [])
            case 'json':
                data = self.mdf.get('register', [])
            case _:
                data = []
        if 'xml' == self.source: # pylint: disable=too-many-nested-blocks
            for idx , item in enumerate(data):
                data[idx] = self._normalize_xml_keys(item)
                keys = ['description', 'name', 'infourl']
                for key in keys:
                    value = data[idx].get(key, None)
                    if value is not None:
                        data[idx][key] = self._normalize_xml_values(value)
                value = data[idx].get('valuelist', None)
                if value is not None:
                    data[idx]['valuelist'] = self._normalize_xml_valuelist(value)
                value = data[idx].get('bit', None)
                if value is not None and isinstance(value, list):
                    for subidx, subitem in enumerate(value):
                        if 'valuelist' in subitem:
                            data[idx]['bit'][subidx]['valuelist'] = self._normalize_xml_valuelist(subitem['valuelist']) # pylint: disable=line-too-long
                        for key in keys:
                            subvalue = data[idx]['bit'][subidx].get(key, None)
                            if subvalue is not None:
                                data[idx]['bit'][subidx][key] = self._normalize_xml_values(subvalue)
        return data


    def _normalize_xml_keys(self, obj):
        if isinstance(obj, dict):
            obj = {key.replace('@', '').replace('#', ''): value for key, value in obj.items()}
            for key, value in obj.items():
                if isinstance(value, list):
                    for idx, item in enumerate(value):
                        value[idx] = self._normalize_xml_keys(item)
                obj[key] = self._normalize_xml_keys(value)
        return obj


    def _normalize_xml_values(self, obj):
        if not isinstance(obj, list):
            obj = [obj]
        result = {}
        for _, item in enumerate(obj):
            if 'lang' in item or 'text' in item:
                key = item['lang'] if 'lang' in item else 'en'
                val = item['text'] if 'text' in item else ''
                try:
                    result[key] = val
                except KeyError:
                    pass
            elif isinstance(item, list):
                self._normalize_xml_values(item)
            else:
                result = item
        return result


    def _normalize_xml_valuelist(self, obj):
        result = obj['item'] if isinstance(obj, dict) and 'item' in obj else []
        for idx, item in enumerate(result):
            keys = ['description', 'name', 'infourl']
            for key in keys:
                value = item.get(key, None)
                if value is not None:
                    result[idx][key] = self._normalize_xml_values(value)
        return result


    def _normalize_access_value(self, access: str) -> str:
        result = ''
        if 'r' in access.lower():
            result += 'r'
        if 'w' in access.lower():
            result += 'w'
        if not result:
            result = '--'
        return result


    def _get_eng_text(self, item: any, last: bool) -> str:
        result = ''
        if isinstance(item, dict):
            try:
                lang = ['en', 'eng', 'gb']
                found = False
                for key in lang:
                    if key in item:
                        val = item[key]
                        found = True
                        break
                if found is False:
                    position = -1 if last else 0
                    val = item[list(item)[position]]
                result = val
            except: # pylint: disable=bare-except
                pass
        else:
            result = str(item)
        return result


    # pylint: disable=line-too-long
    def _get_standard_registers(self) -> dict:
        stdreg_description =  'Module Description File URL. A zero terminates the ASCII string if not exactly 32 bytes long.'
        stdreg_description += ' The URL points to a file that gives further information about where drivers for different'
        stdreg_description += ' environments are located. Can be returned as a zero string for devices with low memory.'
        stdreg_description += ' For a node with an embedded MDF return a zero string. The CLASS1.PROTOCOL,'
        stdreg_description += ' Type=34/35 can then be used to get the information if available.'
        result = {
            -1: {0x80: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Alarm status register',
                        'description':  'Alarm status register content (!= 0 indicates alarm). ' +
                                        'Condition is reset by a read operation. The bits represent different alarm conditions.'
                       },
                 0x81: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'VSCP specification major version number conformance',
                        'description':  'VSCP Major version number this device is constructed for.'
                       },
                 0x82: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'VSCP specification minor version number conformance',
                        'description':  'VSCP Minor version number this device is constructed for.'
                       },
                 0x83: {'access': 'rw', 'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Error counter (was node control flag prior to version 1.6)',
                        'description':  'VSCP error counter is increased when an error occurs on the device. Reset error counter by reading it.'
                       },
                 0x84: {'access': 'rw', 'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'User id 0',
                        'description':  'Client user node-ID byte 0. Use for location info or similar.'
                       },
                 0x85: {'access': 'rw', 'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'User id 1',
                        'description':  'Client user node-ID byte 1. Use for location info or similar.'
                       },
                 0x86: {'access': 'rw', 'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'User id 2',
                        'description':  'Client user node-ID byte 2. Use for location info or similar.'
                       },
                 0x87: {'access': 'rw', 'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'User id 3',
                        'description':  'Client user node-ID byte 3. Use for location info or similar.'
                       },
                 0x88: {'access': 'rw', 'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'User id 4',
                        'description':  'Client user node-ID byte 4. Use for location info or similar.'
                       },
                 0x89: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer device id 0',
                        'description':  'Manufacturer device ID byte 0. For hardware/firmware/manufacturing info.'
                       },
                 0x8A: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer device id 1',
                        'description':  'Manufacturer device ID byte 1. For hardware/firmware/manufacturing info.'
                       },
                 0x8B: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer device id 2',
                        'description':  'Manufacturer device ID byte 2. For hardware/firmware/manufacturing info.'
                       },
                 0x8C: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer device id 3',
                        'description':  'Manufacturer device ID byte 3. For hardware/firmware/manufacturing info.'
                       },
                 0x8D: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer sub device id 0',
                        'description':  'Manufacturer sub device ID byte 0. For hardware/firmware/manufacturing info.'
                       },
                 0x8E: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer sub device id 1',
                        'description':  'Manufacturer sub device ID byte 1. For hardware/firmware/manufacturing info.'
                       },
                 0x8F: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer sub device id 2',
                        'description':  'Manufacturer sub device ID byte 2. For hardware/firmware/manufacturing info.'
                       },
                 0x90: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Manufacturer sub device id 3',
                        'description':  'Manufacturer sub device ID byte 3. For hardware/firmware/manufacturing info.'
                       },
                 0x91: {'access': 'r',  'value': '0xFF',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Nickname for the device',
                        'description':  'Nickname-ID for node if assigned or 0xFF if no nickname-ID assigned.' +
                                        ' This is LSB for the nickname of nodes with 16-bit nikckname id.' +
                                        ' In this case the MSB is stored in register 0xA5.'
                       },
                 0x92: {'access': 'rw',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Page select MSB',
                        'description':  'MSB byte of current selected register page.'
                       },
                 0x93: {'access': 'rw',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Page select LSB',
                        'description':  'LSB byte of current selected register page.'
                       },
                 0x94: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Firmware major version number',
                        'description':  'Major version number for device firmware.'
                       },
                 0x95: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Firmware minor version number',
                        'description':  'Minor version number for device firmware.'
                       },
                 0x96: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Firmware build version number',
                        'description':  'Build version of device firmware.'
                       },
                 0x97: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Boot loader algorithm',
                        'description':  'Boot loader algorithm used to bootload this device. Code 0xFF is used for no boot loader support.'
                       },
                 0x98: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Buffer size',
                        'description':  'Buffer size. The value here gives an indication for clients that want to talk to this node' +
                                        ' if it can support the larger mid level Level I control events which has the full GUID.' +
                                        ' If set to 0 the default size should used. That is 8 bytes for Level I and 512-25 for Level II.'
                       },
                 0x99: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Deprecated: Number of register pages used',
                        'description':  'Number of register pages used. If not implemented one page is assumed.' +
                                        ' Set to zero if your device have more then 255 pages.' +
                                        ' Deprecated: Use the MDF instead as the central place for information about actual number of pages.'
                       },
                 0x9A: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device family code MSB',
                        'description':  'Standard device family code (MSB) Devices can belong to a common register structure standard.' +
                                        ' For such devices this describes the family coded as a 32-bit integer.' +
                                        ' Set all bytes to zero if not used. Also 0xff is reserved and should be interpreted as zero was read.' +
                                        ' Added in version 1.9.0 of the specification.'
                       },
                 0x9B: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device family code',
                        'description':  'Standard device family code Added in version 1.9.0 of the specification.'
                       },
                 0x9C: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device family code',
                        'description':  'Standard device family code Added in version 1.9.0 of the specification.'
                       },
                 0x9D: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device family code LSB',
                        'description':  'Standard device family code Added in version 1.9.0 of the specification.'
                       },
                 0x9E: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device type MSB',
                        'description':  'Standard device type (MSB). This is part of the code that specifies a device that adopts to' +
                                        ' a common register standard. This is the type code represented by a 32-bit integer and defines' +
                                        ' the type belonging to a specific standard. Added in version 1.9.0 of the specification.'
                       },
                 0x9F: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device type',
                        'description':  'Standard device family code. Added in version 1.9.0 of the specification.'
                       },
                 0xA0: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device type',
                        'description':  'Standard device family code. Added in version 1.9.0 of the specification.'
                       },
                 0xA1: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Standard device type LSB',
                        'description':  'Standard device family code (LSB). Added in version 1.9.0 of the specification.'
                       },
                 0xA2: {'access': 'w',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Restore factory defaults (Added in version 1.10)',
                        'description':  'Standard configuration should be restored for a unit if first 0x55 and then 0xAA' +
                                        ' is written to this location and is done so withing one second.' +
                                        ' Added in version 1.10.0 of the specification.'
                       },
                 0xA3: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Firmware device code MSB (Added in version 1.13)',
                        'description':  'Firmware device code MSB. Added in version 1.13.0 of the specification.'
                       },
                 0xA4: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'Firmware device code LSB (Added in version 1.13)',
                        'description':  'Firmware device code LSB. Added in version 1.13.0 of the specification.'
                       },
                 0xA5: {'access': 'r',  'value': '0xFF',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MSB Nickname for the device',
                        'description':  'MSB of 16-bit nickname-ID for node if assigned or 0xFF if no nickname-ID assigned.' +
                                        ' ONLY if 16-bit nickname is used. Undefined if not.' +
                                        ' Added in version 1.14.8 of the specification'
                       },
                 0xD0: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 0 MSB',
                        'description':  stdreg_description
                       },
                 0xD1: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 1',
                        'description':  stdreg_description
                       },
                 0xD2: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 2',
                        'description':  stdreg_description
                       },
                 0xD3: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 3',
                        'description':  stdreg_description
                       },
                 0xD4: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 4',
                        'description':  stdreg_description
                       },
                 0xD5: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 5',
                        'description':  stdreg_description
                       },
                 0xD6: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 6',
                        'description':  stdreg_description
                       },
                 0xD7: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 7',
                        'description':  stdreg_description
                       },
                 0xD8: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 8',
                        'description':  stdreg_description
                       },
                 0xD9: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 9',
                        'description':  stdreg_description
                       },
                 0xDA: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 10',
                        'description':  stdreg_description
                       },
                 0xDB: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 11',
                        'description':  stdreg_description
                       },
                 0xDC: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 12',
                        'description':  stdreg_description
                       },
                 0xDD: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 13',
                        'description':  stdreg_description
                       },
                 0xDE: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 14',
                        'description':  stdreg_description
                       },
                 0xDF: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'GUID byte 15 LSB',
                        'description':  stdreg_description
                       },
                 0xE0: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 0 MSB',
                        'description':  stdreg_description
                       },
                 0xE1: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 1',
                        'description':  stdreg_description
                       },
                 0xE2: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 2',
                        'description':  stdreg_description
                       },
                 0xE3: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 3',
                        'description':  stdreg_description
                       },
                 0xE4: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 4',
                        'description':  stdreg_description
                       },
                 0xE5: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 5',
                        'description':  stdreg_description
                       },
                 0xE6: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 6',
                        'description':  stdreg_description
                       },
                 0xE7: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 7',
                        'description':  stdreg_description
                       },
                 0xE8: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 8',
                        'description':  stdreg_description
                       },
                 0xE9: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 9',
                        'description':  stdreg_description
                       },
                 0xEA: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 10',
                        'description':  stdreg_description
                       },
                 0xEB: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 11',
                        'description':  stdreg_description
                       },
                 0xEC: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 12',
                        'description':  stdreg_description
                       },
                 0xED: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 13',
                        'description':  stdreg_description
                       },
                 0xEE: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 14',
                        'description':  stdreg_description
                       },
                 0xEF: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 15',
                        'description':  stdreg_description
                       },
                 0xF0: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 16',
                        'description':  stdreg_description
                       },
                 0xF1: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 17',
                        'description':  stdreg_description
                       },
                 0xF2: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 18',
                        'description':  stdreg_description
                       },
                 0xF3: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 19',
                        'description':  stdreg_description
                       },
                 0xF4: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 20',
                        'description':  stdreg_description
                       },
                 0xF5: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 21',
                        'description':  stdreg_description
                       },
                 0xF6: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 22',
                        'description':  stdreg_description
                       },
                 0xF7: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 23',
                        'description':  stdreg_description
                       },
                 0xF8: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 24',
                        'description':  stdreg_description
                       },
                 0xF9: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 25',
                        'description':  stdreg_description
                       },
                 0xFA: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 26',
                        'description':  stdreg_description
                       },
                 0xFB: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 27',
                        'description':  stdreg_description
                       },
                 0xFC: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 28',
                        'description':  stdreg_description
                       },
                 0xFD: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 29',
                        'description':  stdreg_description
                       },
                 0xFE: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 30',
                        'description':  stdreg_description
                       },
                 0xFF: {'access': 'r',  'value': '0x00',    'to_sync': self.sync_read,  'type': 'std',  'span': 1,
                        'name':         'MDF byte 31 LSB',
                        'description':  stdreg_description
                       },
                }
        }
        # pylint: enable=line-too-long
        return result


mdf = MdfParser()
