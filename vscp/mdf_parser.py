# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import pprint # TODO remove
import re
import json
import xmltodict


class MdfParser:
    def __init__(self):
        self.mdf = {}
        self.source = 'none'
        self.sync_sign = '●'


    def parse(self, data: str) -> None:
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
        return self.mdf


    def parse_variable(self, lang: str, var) -> str:
        result = var.get(lang, '') if isinstance(var, dict) else var
        return result

    def get_module_info(self) -> dict:
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
        result = self.mdf.get('manufacturer', {})
        return result


    def get_boot_algorithm(self) -> dict:
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
                            'access':       self._normalize_access_value(item['access']), # TODO dmatrix fail
                            'value':        f"0x{max(min(0xFF, int(str(item.get('default', '0xFF')), 0)), 0):02X}", # pylint: disable=line-too-long
                            'to_sync':      self.sync_sign,
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


    def _get_standard_registers(self) -> dict: # TODO implement
        return {}


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


mdf = MdfParser()
