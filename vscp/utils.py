# pylint: disable=line-too-long, missing-module-docstring, missing-function-docstring

def search(var, var_key, default_key: str, lst: list):
    return next((element for element in lst if element[var_key] == var), {default_key: None})[default_key]
