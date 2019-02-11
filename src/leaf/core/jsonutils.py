'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import json
from collections import OrderedDict


def jsonToString(data, pp=False):
    kw = {}
    if pp:
        kw.update({'indent': 4,
                   'separators': (',', ': ')})
    return json.dumps(data, **kw)


def jsonWriteFile(file, data, pp=False):
    with open(str(file), 'w') as fp:
        fp.write(jsonToString(data, pp=pp))


def jsonLoadFile(file):
    with open(str(file), 'r') as fp:
        return jsonLoad(fp)


def jsonLoad(fp):
    return json.load(fp, object_pairs_hook=OrderedDict)


def layerModelUpdate(left, right, listAppend=False):
    '''
    Update the *left* model with values from *right*
    Both left & right have to be dict objects
    '''
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
                layerModelUpdate(left[key], right[key], listAppend=listAppend)
            elif listAppend and isinstance(left[key], list) and isinstance(right[key], list):
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


def layerModelDiff(left, right):
    '''
    Compute the difference between the *left* and *right* model
    Both left & right have to be dict objects
    '''
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
                out[key] = layerModelDiff(left[key], right[key])
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


class JsonObject():
    '''
    Represent a json object
    '''

    def __init__(self, json):
        self.json = json

    def has(self, *keys):
        for key in keys:
            if key not in self.json:
                return False
        return True

    def jsonget(self, key, default=None, mandatory=False):
        '''
        Utility to browse json and reduce None testing
        '''
        if key not in self.json:
            if mandatory:
                raise ValueError("Missing mandatory json field '%s'" % key)
            if default is not None:
                self.json[key] = default
        return self.json.get(key)

    def jsonpath(self, path, default=None, mandatory=False):
        '''
        Utility to browse json and reduce None testing
        '''
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
