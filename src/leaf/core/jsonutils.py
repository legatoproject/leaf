"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import json
from collections import OrderedDict
from pathlib import Path

__JSON_LOAD_ARGS = {"object_pairs_hook": OrderedDict}
__JSON_DUMP_PP = {"indent": 4, "separators": (",", ": ")}


def jtostring(data: dict, pp: bool = False):
    kw = __JSON_DUMP_PP if pp else {}
    return json.dumps(data, **kw)


def jwritefile(file: Path, data: dict, pp: bool = False):
    with file.open("w") as fp:
        fp.write(jtostring(data, pp=pp))


def jloadfile(file: Path):
    with file.open() as fp:
        return jload(fp)


def jload(fp):
    return json.load(fp, **__JSON_LOAD_ARGS)


def jloads(s):
    return json.loads(s, **__JSON_LOAD_ARGS)


def jlayer_update(left: dict, right: dict, list_append: bool = False):
    """
    Update the *left* model with values from *right*
    Both left & right have to be dict objects
    """
    if not isinstance(left, dict):
        raise ValueError("Problem with json layer")
    if not isinstance(right, dict):
        raise ValueError("Problem with json layer")

    for key in list(left.keys()):
        if key in right:
            if right[key] is None:
                # Delete value
                del left[key]
            elif isinstance(left[key], dict) and isinstance(right[key], dict):
                # Reccursive update
                jlayer_update(left[key], right[key], list_append=list_append)
            elif list_append and isinstance(left[key], list) and isinstance(right[key], list):
                # Handle list append if option is set
                left[key] += right[key]
            else:
                # Replace
                left[key] = right[key]
    for key in right.keys():
        if key not in left and right[key] is not None:
            # Add it
            left[key] = right[key]
    return left


def jlayer_diff(left: dict, right: dict):
    """
    Compute the difference between the *left* and *right* model
    Both left & right have to be dict objects
    """
    if not isinstance(left, dict):
        raise ValueError("Problem with json layer")
    if not isinstance(right, dict):
        raise ValueError("Problem with json layer")
    # Special case, diff is empty
    if left == right:
        return OrderedDict()

    out = OrderedDict()
    for key in left.keys():
        if key in right:
            if left[key] == right[key]:
                # Same value, do nothing
                pass
            elif isinstance(left[key], dict) and isinstance(right[key], dict):
                # Recursive diff
                out[key] = jlayer_diff(left[key], right[key])
            else:
                # Value has been updated
                out[key] = right[key]
        else:
            # Delete value
            out[key] = None
    for key in right.keys():
        if key not in left:
            # New value
            out[key] = right[key]

    return out


class JsonObject:

    """
    Represent a json object
    """

    def __init__(self, json: dict):
        self.__json = json

    @property
    def json(self):
        return self.__json

    def jsonget(self, key: str, default=None, mandatory: bool = False):
        """
        Utility to browse json and reduce None testing
        """
        if key not in self.__json:
            if mandatory:
                raise ValueError("Missing mandatory json field '{key}'".format(key=key))
            if default is not None:
                self.__json[key] = default
        return self.__json.get(key)

    def jsonpath(self, path: list, default=None, mandatory: bool = False):
        """
        Utility to browse json and reduce None testing
        """
        if not isinstance(path, (list, tuple)):
            raise ValueError(type(path))
        if len(path) == 0:
            raise ValueError()
        if len(path) == 1:
            return self.jsonget(path[0], default=default, mandatory=mandatory)
        child = self.jsonget(path[0], mandatory=mandatory)
        if not isinstance(child, dict):
            raise ValueError()
        return JsonObject(child).jsonpath(path[1:], default=default, mandatory=mandatory)

    def has(self, *keys: str) -> bool:
        out = 0
        for key in keys:
            if key in self.__json:
                out += 1
        return out
