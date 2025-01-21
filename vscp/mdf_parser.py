# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import json
import xmltodict


class MdfParser:
    def __init__(self):
        self.mdf = {}


    def parse(self, data: str) -> None:
        try:
            substr = str(data[:32])
            pos_xml = substr.find('<')
            pos_json = substr.find('{')
            if -1 != pos_xml:
                self.mdf = xmltodict.parse(data, xml_attribs=False)
            elif -1 != pos_json:
                self.mdf = json.loads(data)
            else:
                self.mdf = {}
        except ValueError:
            self.mdf = {}


    def get(self) -> dict:
        return self.mdf


mdf = MdfParser()
