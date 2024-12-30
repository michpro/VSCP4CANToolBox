# pylint: disable=missing-module-docstring, missing-function-docstring

_set_scan_widget_state_cb: object = None
_neighbours_handle: object = None
_event_info_handle: object = None
_nodes: dict = {}

def add_set_state_callback(callback) -> None:
    if callable(callback):
        global _set_scan_widget_state_cb # pylint: disable=global-statement
        _set_scan_widget_state_cb = callback


def call_set_scan_widget_state(state) -> None:
    if callable(_set_scan_widget_state_cb):
        _set_scan_widget_state_cb(state)


def add_neighbours_handle(handle) -> None:
    if isinstance(handle, object):
        global _neighbours_handle # pylint: disable=global-statement
        _neighbours_handle = handle


def neighbours_handle() -> object:
    return _neighbours_handle


def add_event_info_handle(handle) -> None:
    if isinstance(handle, object):
        global _event_info_handle # pylint: disable=global-statement
        _event_info_handle = handle


def event_info_handle() -> object:
    return _event_info_handle


def set_node_info(key: int, value: any) -> None:
    # global _nodes # pylint: disable=global-statement
    _nodes[key] = value


def get_node_info(key) -> any:
    return _nodes.get(key, None)


def get_nodes() -> dict:
    return _nodes
