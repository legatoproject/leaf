'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from enum import IntEnum, unique


@unique
class Scope(IntEnum):
    LEAF = 0
    USER = 1
    WORKSPACE = 2
    PROFILE = 3
    PACKAGE = 4


class JsonObject():
    '''
    Represent a json object
    '''

    def __init__(self, json):
        self.json = json

    def jsonget(self, key, default=None, mandatory=False):
        '''
        Utility to browse json and reduce None testing
        '''
        if key not in self.json:
            if mandatory:
                raise ValueError("Missing mandatory json field %s" % key)
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
        return JsonObject(child).jsonpath(path[1:], default)
