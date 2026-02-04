"""
VSCP Message Module.

This module provides the Message class for handling VSCP (Very Simple Control Protocol)
messages over CAN. It includes utilities for parsing CAN IDs into VSCP attributes,
preparing CAN IDs from VSCP message structures, and managing a simple message queue.

@file message.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

# pylint: disable=line-too-long


from typing import cast
import numpy as np
import can
import phy
from .dictionary import dictionary


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
    """
    Feeds a received message into the internal message queue.

    This function checks if the feeder is allowed and if the message direction
    is 'RX' before appending it to the global `_messages` list.

    Args:
        msg (dict): The message dictionary containing message details and direction.
    """
    if _feeder_allowed is True and msg['dir'] == 'RX':
        _messages.append(msg)


class Message:
    """
    Manages VSCP message creation, parsing, transmission, and buffering.

    This class provides methods to convert between raw CAN IDs and structured
    VSCP message dictionaries. It also manages a global message queue (feeder)
    for received messages.
    """

    def __init__(self) -> None:
        """Initializes the Message instance."""


    def parse_id(self, can_id: np.uint32) -> dict:
        """
        Parses a 29-bit extended CAN ID into VSCP message attributes.

        Extracts the VSCP Class, Type, Nickname, Hardcoded bit, and Priority
        from the given CAN Identifier.

        Args:
            can_id (np.uint32): The 29-bit extended CAN identifier.

        Returns:
            dict: A dictionary containing the parsed VSCP attributes:
                - 'class': {'id': int, 'name': str}
                - 'type': {'id': int, 'name': str}
                - 'priority': {'id': int, 'name': str}
                - 'nickName': int
                - 'isHardCoded': bool
        """
        vscp_class  = int  ((can_id & VSCP_MSG_CLASS_MASK)          >> VSCP_MSG_CLASS_SHIFT)
        vscp_type   = int  ((can_id & VSCP_MSG_TYPE_MASK)           >> VSCP_MSG_TYPE_SHIFT)
        nickname    = int  ((can_id & VSCP_MSG_NICKNAME_MASK)       >> VSCP_MSG_NICKNAME_SHIFT)
        hard_coded  = 1 == ((can_id & VSCP_MSG_HARCODED_BIT_MASK)   >> VSCP_MSG_HARCODED_BIT_SHIFT)
        priority    = int  ((can_id & VSCP_MSG_PRIORITY_MASK)       >> VSCP_MSG_PRIORITY_SHIFT)

        return {
            'class':    {'id': vscp_class,  'name': dictionary.class_name(vscp_class)},
            'type':     {'id': vscp_type,   'name': dictionary.type_name(vscp_class, vscp_type)},
            'priority': {'id': priority,    'name': dictionary.priority_name(priority)},
            'nickName': nickname,
            'isHardCoded': hard_coded
            }


    def prepare_id(self, msg: dict) -> np.uint32:
        """
        Constructs a 29-bit CAN ID from a VSCP message dictionary.

        Combines the VSCP Class, Type, Nickname, Hardcoded bit, and Priority
        into a single integer suitable for the CAN arbitration ID.

        Args:
            msg (dict): A dictionary containing VSCP message attributes.

        Returns:
            np.uint32: The constructed 29-bit CAN identifier, or 0 if an error occurs.
        """
        result: np.uint32 = cast(np.uint32, 0)
        try:
            vscp_class  = dictionary.class_id(msg['class']['name']) if msg['class']['name'] is not None else msg['class']['id']
            vscp_type   = dictionary.type_id(vscp_class, msg['type']['name']) if msg['type']['name'] is not None else msg['type']['id']

            nickname    = msg['nickName']
            hard_coded  = 1 if msg['isHardCoded'] is True else 0
            priority    = dictionary.priority_id(msg['priority']['name']) if msg['priority']['name'] is not None else msg['priority']['id']

            result = np.uint32(   ((nickname    << VSCP_MSG_NICKNAME_SHIFT)     & VSCP_MSG_NICKNAME_MASK)
                                | ((vscp_type   << VSCP_MSG_TYPE_SHIFT)         & VSCP_MSG_TYPE_MASK)
                                | ((vscp_class  << VSCP_MSG_CLASS_SHIFT)        & VSCP_MSG_CLASS_MASK)
                                | ((hard_coded  << VSCP_MSG_HARCODED_BIT_SHIFT) & VSCP_MSG_HARCODED_BIT_MASK)
                                | ((priority    << VSCP_MSG_PRIORITY_SHIFT)     & VSCP_MSG_PRIORITY_MASK))
        except Exception as e: # pylint: disable=broad-exception-caught
            print("exception", e)
        return result


    def enable_feeder(self):
        """
        Enables the global message feeder.

        Allows incoming messages to be appended to the internal queue.
        """
        global _feeder_allowed # pylint: disable=global-statement
        _feeder_allowed = True


    def disable_feeder(self, flush: bool = False):
        """
        Disables the global message feeder.

        Stops incoming messages from being appended to the internal queue.

        Args:
            flush (bool, optional): If True, clears the existing message queue. Defaults to False.
        """
        global _feeder_allowed # pylint: disable=global-statement
        _feeder_allowed = False
        if flush is True:
            self.flush()


    def available(self) -> int:
        """
        Checks the number of messages currently in the queue.

        Returns:
            int: The number of messages in the queue.
        """
        return len(_messages)


    def push_back(self, msg):
        """
        Manually appends a message to the end of the queue.

        Args:
            msg: The message object/dictionary to append.
        """
        _messages.append(msg)


    def pop_back(self) -> dict | None:
        """
        Removes and returns the last message from the queue.

        Returns:
            dict: The last message in the queue, or None if the queue is empty.
        """
        return _messages.pop(-1) if len(_messages) > 0 else None


    def pop_front(self) -> dict | None:
        """
        Removes and returns the first message from the queue.

        Returns:
            dict: The first message in the queue, or None if the queue is empty.
        """
        return _messages.pop(0) if len(_messages) > 0 else None


    def peek(self) -> list:
        """
        Returns a reference to the entire message list.

        Returns:
            list: The list of messages.
        """
        return _messages


    def peek_front(self) -> dict | None:
        """
        Returns the first message in the queue without removing it.

        Returns:
            dict: The first message, or None if the queue is empty.
        """
        return _messages[0] if len(_messages) > 0 else None


    def flush(self):
        """
        Clears all messages from the queue.
        """
        _messages.clear()


    def send(self, msg: dict) -> bool:
        """
        Sends a VSCP message over the CAN bus.

        Prepares the CAN ID from the message dictionary and transmits it using
        the underlying physical driver if the bus is active.

        Args:
            msg (dict): The VSCP message dictionary to send. Should contain 'data'
                        and other VSCP attributes.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        result = False
        vscp_msg_id = self.prepare_id(msg)
        try:
            bus = phy.driver.bus
            if bus is not None and bus.state == can.bus.BusState.ACTIVE:
                bus.send(can.Message(arbitration_id=int(vscp_msg_id), is_extended_id=True, data=msg['data']))
            result = True
        except Exception: # pylint: disable=broad-exception-caught
            pass
        return result
