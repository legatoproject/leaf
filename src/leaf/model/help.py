"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.core.jsonutils import JsonObject


class HelpTopic(JsonObject):
    def __init__(self, payload: dict, name: str, parent: object):
        JsonObject.__init__(self, payload)
        self.__name = name
        self.__parent = parent

    @property
    def name(self):
        return self.__name

    @property
    def installed_package(self):
        return self.__parent

    @property
    def resources(self):
        return self.json

    @property
    def full_name(self):
        return "{ip.name}/{name}".format(ip=self.installed_package, name=self.name)
