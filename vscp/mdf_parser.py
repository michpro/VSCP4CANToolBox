"""
Module Description File (MDF) Parser.

This module provides the MdfParser class to parse VSCP Module Description Files
in both XML and JSON formats. It extracts module information, register definitions,
and other device-specific data.

@file mdf_parser.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""
# pylint: disable=too-many-lines


# TODO remove debug print
# import pprint
from typing import Dict, Any, cast
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
            # Use strip() to handle potential whitespace before the first tag
            data_clean = data.strip()
            substr = str(data_clean[:32])
            pos_xml = substr.find('<')
            pos_json = substr.find('{')

            if -1 != pos_xml:
                self.mdf = xmltodict.parse(data)
                # Handle both <vscp><module>...</module></vscp> and direct <module>...</module> roots # pylint: disable=line-too-long
                if 'vscp' in self.mdf:
                    self.mdf = self.mdf.get('vscp', {}).get('module', {})
                elif 'module' in self.mdf:
                    self.mdf = self.mdf.get('module', {})
                else:
                    self.mdf = {}

                self.source = 'xml'
            elif -1 != pos_json:
                self.mdf = json.loads(data)
                self.mdf = self.mdf.get('module', {})
                self.source = 'json'
            else:
                self.mdf = {}
                self.source = 'none'
        except (ValueError, Exception): # pylint: disable=broad-exception-caught
            self.mdf = {}
            self.source = 'none'


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
            lang (str): The language code key to retrieve if var is a dictionary.
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

        # XML data requires normalization to handle attributes and text content consistently
        if 'xml' == self.source:
            result = cast(Dict[str, Any], self._normalize_xml_keys(result))
            keys = ['description', 'name', 'infourl']
            for key in keys:
                value = result.get(key, None)
                if value is not None:
                    result[key] = self._normalize_xml_values(value)

        # Return English description by default
        result['description'] = self._get_eng_text(result['description'], True)
        return result


    def get_module_manufacturer(self) -> dict:
        """
        Retrieves manufacturer information from the MDF.

        Returns:
            dict: Manufacturer details.
        """
        raw = self.mdf.get('manufacturer', {})
        if not raw:
            return {}

        if 'xml' == self.source and isinstance(raw, dict):
            raw = cast(Dict[str, Any], self._normalize_xml_keys(raw))

        result = {}

        name_val = raw.get('name', '')
        if isinstance(name_val, (dict, list)):
            name_val = self._normalize_xml_values(name_val)
            result['name'] = self._get_eng_text(name_val, False)
        else:
            result['name'] = str(name_val)

        addr_raw = raw.get('address', {})
        if addr_raw:
            addr_res = {}
            for field in ['street', 'town', 'city', 'postcode', 'state', 'region', 'country']:
                val = addr_raw.get(field, '')
                if isinstance(val, (dict, list)):
                    val = self._normalize_xml_values(val)
                    addr_res[field] = self._get_eng_text(val, False)
                else:
                    addr_res[field] = str(val)
            result['address'] = addr_res

        result['telephone'] = self._process_manufacturer_list(raw.get('telephone'), 'number')
        result['fax'] = self._process_manufacturer_list(raw.get('fax'), 'number')
        result['email'] = self._process_manufacturer_list(raw.get('email'), 'address')
        result['web'] = self._process_manufacturer_list(raw.get('web'), 'url')

        return result


    def _process_manufacturer_list(self, data_list: Any, value_key: str) -> list:
        """
        Helper to process list items for manufacturer contact info (phone, fax, email, web).

        Args:
            data_list: The raw data from MDF (dict or list of dicts).
            value_key: The key holding the main value (e.g., 'number', 'address', 'url').

        Returns:
            list: Processed list of dicts with 'value', 'description', 'infourl'.
        """
        if not data_list:
            return []

        if isinstance(data_list, dict):
            data_list = [data_list]

        results = []
        for item in data_list:
            # item keys are already normalized (no @/#) by _normalize_xml_keys in parent

            # Normalize potential multilingual fields
            desc = item.get('description')
            if desc is not None:
                desc = self._normalize_xml_values(desc)

            infourl = item.get('infourl')
            if infourl is not None:
                infourl = self._normalize_xml_values(infourl)

            entry = {
                'value': str(item.get(value_key, '')),
                'description': self._get_eng_text(desc, False) if desc else '',
                'infourl': self._get_eng_text(infourl, False) if infourl else ''
            }
            results.append(entry)

        return results


    def get_boot_algorithm(self) -> dict:
        """
        Retrieves bootloader algorithm information.

        Returns:
            dict: A dictionary with 'algorithm', 'blockcount', and 'blocksize' keys.
        """
        boot = self.mdf.get('boot', {})
        if 'xml' == self.source and isinstance(boot, dict):
            boot = cast(Dict[str, Any], self._normalize_xml_keys(boot))

        if 'algorithm' in boot and 'blockcount' in boot and 'blocksize' in boot:
            result = {'algorithm':  boot['algorithm'],
                      'blockcount': boot['blockcount'],
                      'blocksize':  boot['blocksize']
                      }
        else:
            result = {}
        return result


    def get_registers_info(self) -> dict: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Constructs a complete map of device registers.

        Combines standard VSCP registers with device-specific registers defined
        in the MDF.

        Returns:
            dict: A nested dictionary mapping page -> offset -> register info.
        """
        result = self._get_standard_registers()

        # Inject Alarm bits into the standard Alarm Status Register (0x80)
        alarm_bits = self._parse_alarm_data()
        if alarm_bits and -1 in result and 0x80 in result[-1]:
            result[-1][0x80]['bits'] = alarm_bits

        data = self._parse_registers_data()

        # TODO remove debug print
        # pp = pprint.PrettyPrinter(indent=2, width=160)
        # pp.pprint(data)

        for item in data: # pylint: disable=too-many-nested-blocks
            if 'page' in item:
                try:
                    page = int(str(item['page']), 0)
                    offset = int(str(item['offset']), 0)

                    # Only process user registers (0x00-0x7F).
                    # Standard registers (0x80-0xFF) are handled by _get_standard_registers.
                    if 0x80 > offset:
                        reg_type = item.get('type', 'std')
                        span = int(str(item.get('span', '1')), 0)
                        width = int(str(item.get('width', '8')), 0)
                        size = int(str(item.get('size', '1')), 0)

                        min_val = item.get('min', None)
                        max_val = item.get('max', None)

                        default_val_raw = item.get('default', '0xFF')
                        try:
                            # Clamp default value to 0-255 byte range for display safety
                            default_int = int(str(default_val_raw), 0)
                            default_display = f"0x{max(min(0xFF, default_int), 0):02X}"
                        except ValueError:
                            default_display = '0x00'

                        record = {
                            'access':       self._normalize_access_value(item.get('access', 'rw')),
                            'value':        default_display,
                            'default':      default_display,
                            'to_sync':      self.sync_read,
                            'name':         self._get_eng_text(item.get('name', ''), False),
                            'description':  self._get_eng_text(item.get('description', ''), False),
                            'type':         reg_type,
                            'span':         span,
                            'width':        width,
                            'size':         size
                        }

                        if min_val is not None:
                            record['min'] = min_val
                        if max_val is not None:
                            record['max'] = max_val

                        valuelist_data = self._process_valuelist(item)
                        if valuelist_data:
                            record['valuelist'] = valuelist_data

                        bits_data = item.get('bit', None)
                        if bits_data:
                            # Ensure it's a list (defensive, should be handled by normalization)
                            if isinstance(bits_data, dict):
                                bits_data = [bits_data]

                            record['bits'] = []
                            for b_item in bits_data:
                                b_rec = {
                                    'name': self._get_eng_text(b_item.get('name', ''), False),
                                    'pos': int(str(b_item.get('pos', '0')), 0),
                                    'width': int(str(b_item.get('width', '1')), 0),
                                    'default': b_item.get('default', '0'),
                                    'description': self._get_eng_text(b_item.get('description', ''), False), # pylint: disable=line-too-long
                                }

                                for opt_field in ['min', 'max', 'access']:
                                    if opt_field in b_item:
                                        b_rec[opt_field] = b_item[opt_field]

                                infourl = self._get_eng_text(b_item.get('infourl', ''), False)
                                if infourl:
                                    b_rec['infourl'] = infourl

                                b_valuelist = self._process_valuelist(b_item)
                                if b_valuelist:
                                    b_rec['valuelist'] = b_valuelist

                                record['bits'].append(b_rec)

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

                        # Expand register based on span (e.g. for block types)
                        base_name = record['name']

                        for i in range(span):
                            current_offset = offset + (i * size)

                            # Ensure we stay within User Register space
                            if current_offset >= 0x80:
                                continue

                            instance_record = record.copy()

                            if span > 1:
                                instance_record['name'] = f"{base_name} {i}"

                            if page not in result:
                                result[page] = {}

                            result[page][current_offset] = instance_record

                except: # pylint: disable=bare-except
                    pass
        # TODO remove debug print
        # pp.pprint(result)
        return result


    def get_remote_variables_info(self) -> list: # pylint: disable=too-many-locals, too-many-branches
        """
        Parses and returns the list of remote variables from the MDF.
        Similar to registers but creates a flat list of abstracted variables.
        """
        data = self._parse_remote_vars_data()
        result = []

        for item in data:
            try:
                # Default values if keys are missing
                name = self._get_eng_text(item.get('name', ''), False)
                # Auto-generate name if missing: rv_reg_{name}_
                # This logic is simplified; spec says rv_<regname>, but here we don't have
                # easy access to reg name if it's not provided in remotevar tag.
                if not name:
                    name = "rv_undefined"

                rec = {
                    'name': name,
                    'type': item.get('type', 'uint8_t'),
                    'offset': int(str(item.get('offset', '0')), 0),
                    'page': int(str(item.get('page', '0')), 0),
                    'access': self._normalize_access_value(item.get('access', 'rw')),
                    'default': item.get('default', '0'),
                    'description': self._get_eng_text(item.get('description', ''), False),
                }

                if 'bitpos' in item:
                    rec['bitpos'] = int(str(item['bitpos']), 0)

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
                    rec['colors'] = colors

                valuelist_data = self._process_valuelist(item)
                if valuelist_data:
                    rec['valuelist'] = valuelist_data

                bits_data = item.get('bit', None)
                if bits_data:
                    if isinstance(bits_data, dict):
                        bits_data = [bits_data]

                    rec['bits'] = []
                    for b_item in bits_data:
                        b_rec = {
                            'name': self._get_eng_text(b_item.get('name', ''), False),
                            'pos': int(str(b_item.get('pos', '0')), 0),
                            'width': int(str(b_item.get('width', '1')), 0),
                            'default': b_item.get('default', '0'),
                            'description': self._get_eng_text(b_item.get('description', ''), False),
                        }

                        infourl = self._get_eng_text(b_item.get('infourl', ''), False)
                        if infourl:
                            b_rec['infourl'] = infourl

                        b_valuelist = self._process_valuelist(b_item)
                        if b_valuelist:
                            b_rec['valuelist'] = b_valuelist

                        rec['bits'].append(b_rec)

                result.append(rec)

            except: # pylint: disable=bare-except
                pass

        return result


    def get_decision_matrix_info(self) -> dict: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Parses the Decision Matrix definition from the MDF.

        Extracts matrix properties (level, page, offset, row count) and the list of Actions.
        Each Action can contain Parameters, which in turn can contain Bits and ValueLists.

        Returns:
            dict: A dictionary containing 'level', 'start_page', 'start_offset',
                  'row_count', 'row_size' and a list of 'actions'.
        """
        raw_dm = self.mdf.get('dmatrix', {})
        if not raw_dm:
            return {}

        if 'xml' == self.source:
            raw_dm = cast(Dict[str, Any], self._normalize_xml_keys(raw_dm))

        result = {}

        result['level'] = int(str(raw_dm.get('level', '1')), 0)

        # Handle 'rowcnt' vs 'rowcount' inconsistency (spec vs common usage)
        row_count_val = raw_dm.get('rowcnt')
        if row_count_val is None:
            row_count_val = raw_dm.get('rowcount', '0')
        result['row_count'] = int(str(row_count_val), 0)

        result['row_size'] = int(str(raw_dm.get('rowsize', '8')), 0)

        # Handle Start Page/Offset: Can be attributes directly on dmatrix or a nested <start> tag
        start_node = raw_dm.get('start', {})

        # Check explicit attributes first (e.g., start-page="3")
        start_page = raw_dm.get('start-page')
        start_offset = raw_dm.get('start-offset')

        # Fallback to nested start tag (e.g., <start page="3" offset="0"/>)
        if start_page is None:
            start_page = start_node.get('page', '0') if isinstance(start_node, dict) else '0'
        if start_offset is None:
            start_offset = start_node.get('offset', '0') if isinstance(start_node, dict) else '0'

        result['start_page'] = int(str(start_page), 0)
        result['start_offset'] = int(str(start_offset), 0)

        actions_list = []
        raw_actions = raw_dm.get('action', [])
        if isinstance(raw_actions, dict):
            raw_actions = [raw_actions]

        text_keys = ['description', 'name', 'infourl']

        for action in raw_actions: # # pylint: disable=too-many-nested-blocks
            if 'xml' == self.source:
                action = cast(Dict[str, Any], self._normalize_xml_keys(action))
                for key in text_keys:
                    if key in action:
                        action[key] = self._normalize_xml_values(action[key])

            action_rec = {
                'name': self._get_eng_text(action.get('name', ''), False),
                'code': int(str(action.get('code', '0')), 0),
                'description': self._get_eng_text(action.get('description', ''), False),
                'infourl': self._get_eng_text(action.get('infourl', ''), False),
                'params': []
            }

            # Spec usually implies one param for Level I, but MDF structure allows list
            raw_params = action.get('param', [])

            if isinstance(raw_params, dict):
                raw_params = [raw_params]

            for param in raw_params:
                if 'xml' == self.source:
                    param = cast(Dict[str, Any], self._normalize_xml_keys(param))
                    for key in text_keys:
                        if key in param:
                            param[key] = self._normalize_xml_values(param[key])
                    # Normalize nested lists inside param (valuelist, bit)
                    if 'valuelist' in param:
                        param['valuelist'] = self._normalize_xml_valuelist(param['valuelist'])

                    # Normalize bits
                    if 'bit' in param:
                        if isinstance(param['bit'], dict):
                            param['bit'] = [param['bit']]
                        # Recursively normalize bits
                        for idx, b_item in enumerate(param['bit']):
                            param['bit'][idx] = cast(Any, self._normalize_xml_keys(b_item))
                            b_item = param['bit'][idx]
                            for key in text_keys:
                                if key in b_item:
                                    param['bit'][idx][key] = self._normalize_xml_values(b_item[key])
                            if 'valuelist' in b_item:
                                param['bit'][idx]['valuelist'] = self._normalize_xml_valuelist(b_item['valuelist']) # pylint: disable=line-too-long

                param_rec = {
                    'name': self._get_eng_text(param.get('name', ''), False),
                    'offset': int(str(param.get('offset', '0')), 0),
                    'min': int(str(param.get('min', '0')), 0),
                    'max': int(str(param.get('max', '255')), 0),
                    'description': self._get_eng_text(param.get('description', ''), False),
                    'infourl': self._get_eng_text(param.get('infourl', ''), False)
                }

                vl = self._process_valuelist(param)
                if vl:
                    param_rec['valuelist'] = vl

                bits_data = param.get('bit', [])
                if isinstance(bits_data, dict):
                    bits_data = [bits_data]

                if bits_data:
                    param_rec['bits'] = []
                    for b_item in bits_data:
                        b_rec = {
                            'name': self._get_eng_text(b_item.get('name', ''), False),
                            'pos': int(str(b_item.get('pos', '0')), 0),
                            'width': int(str(b_item.get('width', '1')), 0),
                            'description': self._get_eng_text(b_item.get('description', ''), False),
                            'infourl': self._get_eng_text(b_item.get('infourl', ''), False)
                        }
                        b_vl = self._process_valuelist(b_item)
                        if b_vl:
                            b_rec['valuelist'] = b_vl

                        param_rec['bits'].append(b_rec)

                action_rec['params'].append(param_rec)

            actions_list.append(action_rec)

        result['actions'] = actions_list
        return result


    def get_events_info(self) -> list: # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Parses the Events definition from the MDF.

        Returns:
            list: A list of dictionary objects representing events.
        """
        raw_events = self.mdf.get('events', {})
        if not raw_events:
            return []

        # Extract 'event' list/dict
        if 'xml' == self.source:
            raw_data = raw_events.get('event', [])
        else:
            raw_data = raw_events.get('event', []) if isinstance(raw_events, dict) else []

        if isinstance(raw_data, dict):
            raw_data = [raw_data]

        result = []
        text_keys = ['description', 'name', 'infourl']

        for item in raw_data: # pylint: disable=too-many-nested-blocks
            if 'xml' == self.source:
                item = cast(Dict[str, Any], self._normalize_xml_keys(item))
                # Normalize text fields
                for key in text_keys:
                    if key in item:
                        item[key] = self._normalize_xml_values(item[key])

            # Name fallback (Name vs name in XML attributes)
            evt_name = item.get('name') or item.get('Name', '')
            evt_name = self._get_eng_text(evt_name, False)

            # Direction fallback (direction vs dir)
            evt_dir = item.get('direction') or item.get('dir', 'out')

            rec = {
                'name': evt_name,
                'class': item.get('class', '-'),
                'type': item.get('type', '-'),
                'priority': int(str(item.get('priority', '3')), 0),
                'direction': evt_dir,
                'description': self._get_eng_text(item.get('description', ''), False),
                'infourl': self._get_eng_text(item.get('infourl', ''), False),
                'data': []
            }

            item_data = item.get('data', [])
            if isinstance(item_data, dict):
                item_data = [item_data]

            for d in item_data:
                if 'xml' == self.source:
                    d = cast(Dict[str, Any], self._normalize_xml_keys(d))
                    for key in text_keys:
                        if key in d:
                            d[key] = self._normalize_xml_values(d[key])
                    # Normalize nested valuelist/bits
                    if 'valuelist' in d:
                        d['valuelist'] = self._normalize_xml_valuelist(d['valuelist'])
                    if 'bit' in d:
                        if isinstance(d['bit'], dict):
                            d['bit'] = [d['bit']]
                        for idx, b in enumerate(d['bit']):
                            d['bit'][idx] = cast(Dict[str, Any], self._normalize_xml_keys(b))
                            b = d['bit'][idx] # update reference
                            for key in text_keys:
                                if key in b:
                                    d['bit'][idx][key] = self._normalize_xml_values(b[key])
                            if 'valuelist' in b:
                                d['bit'][idx]['valuelist'] = self._normalize_xml_valuelist(b['valuelist']) # pylint: disable=line-too-long

                d_rec = {
                    'name': self._get_eng_text(d.get('name', ''), False),
                    'offset': int(str(d.get('offset', '0')), 0),
                    'description': self._get_eng_text(d.get('description', ''), False),
                    'infourl': self._get_eng_text(d.get('infourl', ''), False)
                }

                vl = self._process_valuelist(d)
                if vl:
                    d_rec['valuelist'] = vl

                bits = d.get('bit', [])
                if isinstance(bits, dict):
                    bits = [bits]

                if bits:
                    d_rec['bits'] = []
                    for b in bits:
                        b_rec = {
                            'name': self._get_eng_text(b.get('name', ''), False),
                            'pos': int(str(b.get('pos', '0')), 0),
                            'width': int(str(b.get('width', '1')), 0),
                            'description': self._get_eng_text(b.get('description', ''), False),
                            'infourl': self._get_eng_text(b.get('infourl', ''), False)
                        }
                        for opt in ['min', 'max', 'default', 'access']:
                            if opt in b:
                                b_rec[opt] = b[opt]

                        b_vl = self._process_valuelist(b)
                        if b_vl:
                            b_rec['valuelist'] = b_vl
                        d_rec['bits'].append(b_rec)
                rec['data'].append(d_rec)
            result.append(rec)

        return result


    def get_files_info(self) -> dict: # pylint: disable=too-many-branches
        """
        Parses the Files section from the MDF.
        Returns a dictionary with keys: 'firmware', 'picture', 'video', 'manual', 'driver', 'setup'.
        Each value is a list of file info dictionaries.
        """
        raw_files = self.mdf.get('files', {})
        if not raw_files:
            return {}

        if 'xml' == self.source:
            raw_files = cast(Dict[str, Any], self._normalize_xml_keys(raw_files))

        result = {}
        file_types = ['firmware', 'picture', 'video', 'manual', 'driver', 'setup']

        for ftype in file_types: # pylint: disable=too-many-nested-blocks
            items = raw_files.get(ftype, [])
            if isinstance(items, dict):
                items = [items]

            parsed_items = []
            for item in items:
                if 'xml' == self.source:
                    item = cast(Dict[str, Any], self._normalize_xml_keys(item))
                    # Normalize text fields
                    for key in ['description', 'infourl', 'url']: # url might be a child tag in XML
                        if key in item:
                            val = item[key]
                            # Special handling for url which might be string or dict in XML normalized # pylint: disable=line-too-long
                            if key == 'url' and isinstance(val, str):
                                pass
                            else:
                                item[key] = self._normalize_xml_values(val)

                rec = {}
                rec['name'] = item.get('name', '')

                # URL handling: attribute > child > path attribute
                url_val = item.get('url', '')
                # if url is a dict (from XML child tag normalization), get text
                if isinstance(url_val, dict):
                    url_val = self._get_eng_text(url_val, False)

                if not url_val:
                    url_val = item.get('path', '')

                rec['url'] = url_val
                rec['description'] = self._get_eng_text(item.get('description', ''), False)
                rec['infourl'] = self._get_eng_text(item.get('infourl', ''), False)
                rec['date'] = item.get('date', '')
                rec['format'] = item.get('format', '')

                rec['version_major'] = item.get('version_major', '')
                rec['version_minor'] = item.get('version_minor', '')
                rec['version_subminor'] = item.get('version_subminor', '')

                if ftype == 'firmware':
                    rec['target'] = item.get('target', '')
                    rec['targetcode'] = item.get('targetcode', '')
                    rec['size'] = item.get('size', '0')
                    rec['md5'] = item.get('md5', '')

                elif ftype == 'driver':
                    rec['type'] = item.get('type', '')
                    rec['os'] = item.get('os', '')
                    rec['osver'] = item.get('osver', '')
                    rec['architecture'] = item.get('architecture', '')
                    rec['md5'] = item.get('md5', '')

                elif ftype == 'manual':
                    rec['lang'] = item.get('lang', 'en')

                parsed_items.append(rec)
            result[ftype] = parsed_items

        return result


    def _parse_remote_vars_data(self) -> list: # pylint: disable=too-many-branches
        """
        Parses remote variables raw data.
        Handles normalization of XML keys/values similar to registers.
        """
        data: list[Any] = []
        match self.source:
            case 'xml':
                container = self.mdf.get('remotevars', {})
                if not container:
                    data = []
                else:
                    data = container.get('remotevar', [])
            case 'json':
                data = self.mdf.get('remotevar', []) # Assuming json key structure
            case _:
                data = []

        if isinstance(data, dict):
            data = [data]

        if 'xml' == self.source: # pylint: disable=too-many-nested-blocks
            for idx, item in enumerate(data):
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
                if value is not None:
                    if isinstance(value, dict):
                        value = [value]
                        data[idx]['bit'] = value

                    for subidx, subitem in enumerate(value):
                        data[idx]['bit'][subidx] = self._normalize_xml_keys(subitem)
                        subitem = data[idx]['bit'][subidx]

                        if 'valuelist' in subitem:
                            data[idx]['bit'][subidx]['valuelist'] = self._normalize_xml_valuelist(subitem['valuelist']) # pylint: disable=line-too-long

                        for key in keys:
                            subvalue = subitem.get(key, None)
                            if subvalue is not None:
                                data[idx]['bit'][subidx][key] = self._normalize_xml_values(subvalue)
        return data


    def _parse_alarm_data(self) -> list:
        """
        Parses alarm bit definitions from the MDF.
        Returns a list of processed bit dictionaries.
        """
        data: list[Any] = []
        match self.source:
            case 'xml':
                container = self.mdf.get('alarm', {})
                if not container:
                    data = []
                else:
                    data = container.get('bit', [])
            case 'json':
                data = self.mdf.get('alarm', {}).get('bit', [])
            case _:
                data = []

        if isinstance(data, dict):
            data = [data]

        if 'xml' == self.source:
            for idx, item in enumerate(data):
                data[idx] = self._normalize_xml_keys(item)

                keys = ['description', 'name', 'infourl']
                for key in keys:
                    value = data[idx].get(key, None)
                    if value is not None:
                        data[idx][key] = self._normalize_xml_values(value)

        result = []
        for item in data:
            try:
                rec = {
                    'name': self._get_eng_text(item.get('name', ''), False),
                    'pos': int(str(item.get('pos', '0')), 0),
                    'width': 1,
                    'description': self._get_eng_text(item.get('description', ''), False),
                }

                infourl = self._get_eng_text(item.get('infourl', ''), False)
                if infourl:
                    rec['infourl'] = infourl

                result.append(rec)
            except: # pylint: disable=bare-except
                pass
        return result


    def _process_valuelist(self, source_item: dict) -> list:
        """
        Helper method to extract and format a valuelist from a register or bit item.

        Args:
            source_item (dict): The dictionary containing the 'valuelist' key.

        Returns:
            list: A list of processed value dictionaries, or an empty list.
        """
        processed_list = []
        valuelist = source_item.get('valuelist', None)
        if valuelist:
            for v_item in valuelist:
                v_rec = {
                    'value': v_item.get('value', ''),
                    'name':  self._get_eng_text(v_item.get('name', ''), False),
                    'description': self._get_eng_text(v_item.get('description', ''), False)
                }
                infourl = self._get_eng_text(v_item.get('infourl', ''), False)
                if infourl:
                    v_rec['infourl'] = infourl
                processed_list.append(v_rec)
        return processed_list


    def _isrgbcolor(self, value: str) -> bool:
        if not isinstance(value, str):
            return False
        rgbstring = re.compile(r'0[xX][a-fA-F0-9]{6}$')
        return bool(rgbstring.match(value))


    def _parse_registers_data(self) -> list: # pylint: disable=too-many-branches
        """
        Parses register data from internal MDF structure.
        Handles both single dict (one register) and list of dicts (multiple registers).
        """
        data: list[Any] = []
        match self.source:
            case 'xml':
                regs_container = self.mdf.get('registers', {})
                if not regs_container:
                    data = []
                else:
                    data = regs_container.get('reg', [])
            case 'json':
                data = self.mdf.get('register', [])
            case _:
                data = []

        # Ensure we always return a list, even if xmltodict returned a single dict
        if isinstance(data, dict):
            data = [data]

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
                if value is not None:
                    if isinstance(value, dict):
                        value = [value]
                        data[idx]['bit'] = value

                    for subidx, subitem in enumerate(value):
                        data[idx]['bit'][subidx] = self._normalize_xml_keys(subitem)
                        subitem = data[idx]['bit'][subidx]

                        if 'valuelist' in subitem:
                            data[idx]['bit'][subidx]['valuelist'] = self._normalize_xml_valuelist(subitem['valuelist']) # pylint: disable=line-too-long

                        for key in keys:
                            subvalue = subitem.get(key, None)
                            if subvalue is not None:
                                data[idx]['bit'][subidx][key] = self._normalize_xml_values(subvalue)
        return data


    def _normalize_xml_keys(self, obj):
        """
        Recursively removes '@' (attributes) and '#' (text content) prefixes
        introduced by xmltodict to create a clean dictionary structure.
        """
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                clean_key = key.replace('@', '').replace('#', '')
                normalized_val = self._normalize_xml_keys(value)
                new_obj[clean_key] = normalized_val
            return new_obj
        if isinstance(obj, list):
            return [self._normalize_xml_keys(item) for item in obj]
        return obj


    def _normalize_xml_values(self, obj):
        """
        Normalizes multilingual XML values or nested structures.
        Tries to extract 'en' or 'text' fields if present.
        """
        if not isinstance(obj, list):
            obj = [obj]
        result = {}
        for _, item in enumerate(obj):
            if isinstance(item, dict):
                if 'lang' in item or 'text' in item:
                    key = item['lang'] if 'lang' in item else 'en'
                    val = item['text'] if 'text' in item else ''
                    try:
                        result[key] = val
                    except KeyError:
                        pass
                else:
                    return self._normalize_xml_keys(item)
            elif isinstance(item, list):
                self._normalize_xml_values(item)
            else:
                result = item
        return result


    def _normalize_xml_valuelist(self, obj):
        obj = self._normalize_xml_keys(obj)
        if isinstance(obj, dict):
            result = obj.get('item', [])
        else:
            result = obj if isinstance(obj, list) else []

        if isinstance(result, dict):
            result = [result]

        for idx, item in enumerate(result):
            result[idx] = cast(Any, self._normalize_xml_keys(item))
            keys = ['description', 'name', 'infourl']
            for key in keys:
                value = result[idx].get(key, None)
                if value is not None:
                    result[idx][key] = self._normalize_xml_values(value)
        return result


    def _normalize_access_value(self, access: str) -> str:
        if not isinstance(access, str):
            return '--'
        result = ''
        if 'r' in access.lower():
            result += 'r'
        if 'w' in access.lower():
            result += 'w'
        if not result:
            result = '--'
        return result


    def _get_eng_text(self, item: Any, last: bool) -> str:
        """
        Attempts to retrieve English text from a dictionary of language options.
        Falls back to the first or last available language if English is missing.
        """
        result = ''
        if isinstance(item, dict):
            try:
                lang = ['en', 'eng', 'gb']
                found = False
                val = ''
                for key in lang:
                    if key in item:
                        val = item[key]
                        found = True
                        break
                if found is False and item:
                    position = -1 if last else 0
                    keys = list(item.keys())
                    if keys:
                        val = item[keys[position]]
                result = val
            except: # pylint: disable=bare-except
                pass
        else:
            result = str(item) if item is not None else ''

        # Clean up whitespace/indentation from XML multi-line strings
        if result:
            result = result.strip()
            lines = result.splitlines()
            lines = [line.strip() for line in lines]
            result = '\n'.join(lines)

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
