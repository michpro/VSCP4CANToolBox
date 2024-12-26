# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring, line-too-long

import numpy as np
import can
import phy
from .dictionary import Dictionary


VSCP_MSG_CLASS_SHIFT        = 16
VSCP_MSG_CLASS_MASK         = 0x000001FF << VSCP_MSG_CLASS_SHIFT
VSCP_MSG_TYPE_SHIFT         = 8
VSCP_MSG_TYPE_MASK          = 0x000000FF << VSCP_MSG_TYPE_SHIFT
VSCP_MSG_NICKNAME_SHIFT     = 0
VSCP_MSG_NICKNAME_MASK      = 0x000000FF << VSCP_MSG_NICKNAME_SHIFT
VSCP_MSG_HARCODED_BIT_SHIFT = 25
VSCP_MSG_HARCODED_BIT_MASK  = 0x00000001 << VSCP_MSG_HARCODED_BIT_SHIFT
VSCP_MSG_PRIORITY_SHIFT     = 26
VSCP_MSG_PRIORITY_MASK      = 0x00000007 << VSCP_MSG_PRIORITY_SHIFT

_messages: list = []
_feeder_allowed: bool = False

def feeder(msg: dict):
    if _feeder_allowed is True and msg['dir'] == 'RX':
        _messages.append(msg)

class Message:
    dictionary = Dictionary()

    def __init__(self) -> None:
        pass


    def parse_id(self, can_id: np.uint32) -> dict:
        vscp_class  = int  ((can_id & VSCP_MSG_CLASS_MASK)          >> VSCP_MSG_CLASS_SHIFT)
        vscp_type   = int  ((can_id & VSCP_MSG_TYPE_MASK)           >> VSCP_MSG_TYPE_SHIFT)
        nickname    = int  ((can_id & VSCP_MSG_NICKNAME_MASK)       >> VSCP_MSG_NICKNAME_SHIFT)
        hard_coded  = 1 == ((can_id & VSCP_MSG_HARCODED_BIT_MASK)   >> VSCP_MSG_HARCODED_BIT_SHIFT)
        priority    = int  ((can_id & VSCP_MSG_PRIORITY_MASK)       >> VSCP_MSG_PRIORITY_SHIFT)

        return {
            'class':    {'id': vscp_class,  'name': self.dictionary.class_name(vscp_class)},
            'type':     {'id': vscp_type,   'name': self.dictionary.type_name(vscp_class, vscp_type)},
            'priority': {'id': priority,    'name': self.dictionary.priority_name(priority)},
            'nickName': nickname,
            'isHardCoded': hard_coded
            }


    def prepare_id(self, msg: dict) -> np.uint32:
        result: np.uint32 = 0
        try:
            vscp_class  = self.dictionary.class_id(msg['class']['name']) if msg['class']['name'] is not None else msg['class']['id']
            vscp_type   = self.dictionary.type_id(vscp_class, msg['type']['name']) if msg['type']['name'] is not None else msg['type']['id']
            nickname    = msg['nickName']
            hard_coded  = 1 if msg['isHardCoded'] is True else 0
            priority    = self.dictionary.priority_id(msg['priority']['name']) if msg['priority']['name'] is not None else msg['priority']['id']

            result = np.uint32(   ((nickname    << VSCP_MSG_NICKNAME_SHIFT)     & VSCP_MSG_NICKNAME_MASK)
                                | ((vscp_type   << VSCP_MSG_TYPE_SHIFT)         & VSCP_MSG_TYPE_MASK)
                                | ((vscp_class  << VSCP_MSG_CLASS_SHIFT)        & VSCP_MSG_CLASS_MASK)
                                | ((hard_coded  << VSCP_MSG_HARCODED_BIT_SHIFT) & VSCP_MSG_HARCODED_BIT_MASK)
                                | ((priority    << VSCP_MSG_PRIORITY_SHIFT)     & VSCP_MSG_PRIORITY_MASK))
        except Exception as e: # pylint: disable=broad-exception-caught
            print("exception", e)
        return result


    def enable_feeder(self):
        global _feeder_allowed # pylint: disable=global-statement
        _feeder_allowed = True


    def disable_feeder(self, flush: bool = False):
        global _feeder_allowed # pylint: disable=global-statement
        _feeder_allowed = False
        if flush is True:
            self.flush()


    def available(self) -> int:
        return len(_messages)


    def push_back(self, msg):
        _messages.append(msg)


    def pop_back(self) -> dict:
        return _messages.pop(-1) if len(_messages) > 0 else None


    def pop_front(self) -> dict:
        return _messages.pop(0) if len(_messages) > 0 else None


    def peek(self) -> list:
        return _messages


    def peek_front(self) -> dict:
        return _messages[0] if len(_messages) > 0 else None


    def flush(self):
        _messages.clear()


    def send(self, msg: dict) -> bool:
        result = False
        vscp_msg_id = self.prepare_id(msg)
        try:
            # bus = phy.driver.bus()
            bus = phy.driver.bus
            if bus.state == can.bus.BusState.ACTIVE:
                bus.send(can.Message(arbitration_id=vscp_msg_id, is_extended_id=True, data=msg['data']))
            result = True
        except Exception: # pylint: disable=broad-exception-caught
            pass
        return result
