"""
Local HTTP Server Module.

This module implements a simple, threaded HTTP server to serve static resources
(like icons) to the application if needed, or to act as a local web interface endpoint.
It provides a mechanism to start and stop the server in a separate thread.
"""

# pylint: disable=

import threading
import http.server
import socketserver


class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Custom HTTP Request Handler.

    Extends SimpleHTTPRequestHandler to suppress logging and handle specific
    resource paths (e.g., redirecting favicon requests).
    """

    def log_message(self, format, *args): # pylint: disable=redefined-builtin
        """
        Overrides log_message to suppress standard logging to stderr.
        """
        pass


    def do_GET(self):
        """
        Handles GET requests.

        Redirects '/favicon.ico' requests to the correct local path for the
        VSCP logo icon before delegating to the superclass handler.
        """
        if '/favicon.ico' == self.path:
            self.path = '/gui/icons/vscp_logo.ico' # pylint: disable=attribute-defined-outside-init
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


class HttpLocalServer:
    """
    Manages a local threaded HTTP server.

    This class wraps socketserver.TCPServer to run it within a separate thread,
    allowing non-blocking execution alongside the main application.
    """

    def __init__(self):
        """
        Initializes the HttpLocalServer.

        Sets up the TCP server on port 80 with the custom HttpRequestHandler.
        """
        self.thread = None
        port = 80
        http_handler = HttpRequestHandler
        self.server = socketserver.TCPServer(("", port), http_handler)


    def _run(self):
        """
        Internal method to run the server loop.

        Handles the serve_forever loop and ensures the server is closed properly
        upon termination.
        """
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.server.server_close()


    def start(self):
        """
        Starts the HTTP server in a separate daemon thread.
        """
        self.thread = threading.Thread(None, self._run)
        self.thread.start()


    def stop(self):
        """
        Stops the HTTP server.

        Shuts down the server socket and waits for the server thread to join.
        """
        self.server.shutdown()
        self.thread.join()


server = HttpLocalServer()
