"""
GUI Common Utilities Module.

This module provides common utility functions and shared state management
for the GUI application. It handles callback registration for scan widget updates,
stores references to main UI handles (neighbours, event info), and maintains
a local dictionary of node information.

@file common.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""
# pylint: disable=line-too-long

from typing import Any


_set_scan_widget_state_cb: object = None
_neighbours_handle: object = None
_event_info_handle: object = None
_nodes: dict = {}
_progress_observers: list = []


def add_progress_observer(observer) -> None:
    """
    Registers a callback function to observe scan or operation progress.

    Args:
        observer (callable): A function that accepts a float (0.0 to 1.0).
    """
    if callable(observer):
        _progress_observers.append(observer)


def update_progress(progress_val) -> None:
    """
    Notifies all registered observers of the current progress.

    Args:
        progress_val (float): Progress value between 0.0 and 1.0.
    """
    for observer in _progress_observers:
        observer(progress_val)


def add_set_state_callback(callback) -> None:
    """
    Registers a callback function to update the scan widget state.

    Args:
        callback (callable): The function to call when the scan state changes.
    """
    if callable(callback):
        global _set_scan_widget_state_cb # pylint: disable=global-statement
        _set_scan_widget_state_cb = callback


def call_set_scan_widget_state(state) -> None:
    """
    Invokes the registered scan widget state callback.

    Args:
        state: The new state to set for the scan widget.
    """
    if callable(_set_scan_widget_state_cb):
        _set_scan_widget_state_cb(state)


def add_neighbours_handle(handle) -> None:
    """
    Stores a reference to the neighbours UI component handle.

    Args:
        handle (object): The neighbours UI object.
    """
    if isinstance(handle, object):
        global _neighbours_handle # pylint: disable=global-statement
        _neighbours_handle = handle


def neighbours_handle() -> object:
    """
    Retrieves the stored neighbours UI component handle.

    Returns:
        object: The neighbours UI object, or None if not set.
    """
    return _neighbours_handle


def add_event_info_handle(handle) -> None:
    """
    Stores a reference to the event info UI component handle.

    Args:
        handle (object): The event info UI object.
    """
    if isinstance(handle, object):
        global _event_info_handle # pylint: disable=global-statement
        _event_info_handle = handle


def event_info_handle() -> object:
    """
    Retrieves the stored event info UI component handle.

    Returns:
        object: The event info UI object, or None if not set.
    """
    return _event_info_handle


def set_node_info(key: int, value: Any) -> None:
    """
    Updates or adds information for a specific node in the local cache.

    Args:
        key (int): The node ID (nickname).
        value (Any): The node information structure.
    """
    _nodes[key] = value


def get_node_info(key) -> Any:
    """
    Retrieves information for a specific node from the local cache.

    Args:
        key (int): The node ID (nickname).

    Returns:
        Any: The node information structure, or None if not found.
    """
    return _nodes.get(key, None)


def get_nodes() -> dict:
    """
    Retrieves the entire dictionary of cached node information.

    Returns:
        dict: The dictionary containing all node info.
    """
    return _nodes
