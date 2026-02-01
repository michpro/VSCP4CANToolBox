"""
VSCP Callback Module.

This module defines the Callback class which acts as a handler for incoming
CAN messages, parsing them into VSCP format and distributing them to
registered callback functions.
"""

from can.message import Message
from can.io.generic import MessageWriter
from .message import Message as VSCPMsg


class Callback(MessageWriter):
    """
    Handles incoming CAN messages and invokes registered callbacks.

    Inherits from can.io.generic.MessageWriter to integrate with python-can's
    notifier system.
    """
    cb_func = None
    file = None


    def __init__(self, cb: list = None) -> None:
        """
        Initializes the Callback instance.

        Args:
            cb (list, optional): A list of callback functions to be triggered
                upon message reception. Defaults to None.
        """
        self.write_to_file = False
        self.cb_func = cb
        super().__init__(file=self.file)


    def on_message_received(self, msg: Message) -> None:
        """
        Processes a received CAN message.

        Parses the extended CAN ID into VSCP attributes (class, type, etc.)
        and passes the resulting dictionary to all registered callback functions.

        Args:
            msg (can.message.Message): The received CAN message.
        """
        if msg.is_extended_id is True:
            message = VSCPMsg()
            vscp_msg = message.parse_id(msg.arbitration_id)
            vscp_msg['dataLen'] = msg.dlc
            vscp_msg['data'] = list(msg.data)
            vscp_msg['timestamp'] = msg.timestamp
            vscp_msg['dir'] = 'RX' if msg.is_rx else 'TX'
            try:
                for func in self.cb_func:
                    if func is not None:
                        try:
                            func(vscp_msg)
                        except Exception as e: # pylint: disable=broad-exception-caught
                            print("exception:", e)
            except Exception as e: # pylint: disable=broad-exception-caught
                print("exception:", e)


    def on_error(self, exc: Exception) -> None:
        """
        Handles errors that occur during message processing.

        Args:
            exc (Exception): The exception that was raised.
        """
        pass
