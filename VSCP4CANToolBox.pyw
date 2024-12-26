# pylint: disable=missing-module-docstring, missing-function-docstring, invalid-name

import tk_async_execute as tae
from gui import app

def main():
    tae.start()
    app.mainloop()
    tae.stop()

if __name__ == "__main__":
    main()
