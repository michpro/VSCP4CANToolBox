# pylint: disable=missing-module-docstring, missing-function-docstring, invalid-name

import tk_async_execute as tae
from gui import app, server

def main():
    server.start()
    tae.start()
    app.mainloop()
    tae.stop()
    server.stop()

if __name__ == "__main__":
    main()
