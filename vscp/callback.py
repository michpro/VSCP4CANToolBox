# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

from can.message import Message
from can.io.generic import MessageWriter
from .message import Message as VSCPMsg

class Callback(MessageWriter):
    cb_func = None
    file = None

    def __init__(self, cb: list = None) -> None:
        self.write_to_file = False
        self.cb_func = cb
        super().__init__(file=self.file)


    def on_message_received(self, msg: Message) -> None:
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
            except Exception: # pylint: disable=broad-exception-caught
                print("exception:", e)


    def on_error(self, exc: Exception) -> None:
        pass
