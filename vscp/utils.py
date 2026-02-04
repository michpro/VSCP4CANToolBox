"""
Utility functions module.

Provides general-purpose helper functions used across the VSCP package.

@file utils.py
@copyright SPDX-FileCopyrightText: Copyright 2024-2026 by Michal Protasowicki
@license SPDX-License-Identifier: MIT
"""

# pylint: disable=line-too-long


def search(var, var_key, default_key: str, lst: list):
    """
    Searches a list of dictionaries for a specific value associated with a key.

    If the value is found, returns the value associated with `default_key`.
    If not found, returns None.

    Args:
        var: The value to search for.
        var_key (str): The key in the dictionary to check against `var`.
        default_key (str): The key whose value should be returned if found.
        lst (list): A list of dictionaries to search.

    Returns:
        The value associated with `default_key` in the matching dictionary, or None.
    """
    return next((element for element in lst if element[var_key] == var), {default_key: None})[default_key]
