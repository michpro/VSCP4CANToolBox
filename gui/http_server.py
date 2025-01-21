# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring

import threading
import http.server
import socketserver


class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): # pylint: disable=redefined-builtin
        pass


    def do_GET(self):
        if '/favicon.ico' == self.path:
            self.path = '/gui/icons/vscp_logo.ico' # pylint: disable=attribute-defined-outside-init
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


class HttpLocalServer:
    def __init__(self):
        self.thread = None
        port = 80
        http_handler = HttpRequestHandler
        self.server = socketserver.TCPServer(("", port), http_handler)


    def _run(self):
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server.server_close()


    def start(self):
        self.thread = threading.Thread(None, self._run)
        self.thread.start()


    def stop(self):
        self.server.shutdown()
        self.thread.join()


server = HttpLocalServer()
