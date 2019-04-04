"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""


from leaf.core.constants import JsonConstants
from leaf.core.jsonutils import JsonObject
from leaf.core.settings import LeafSetting, RegexValidator
from leaf.model.base import Scope


class ScopeSetting(LeafSetting):

    __SCOPES = {"user": Scope.USER, "workspace": Scope.WORKSPACE, "profile": Scope.PROFILE}

    @staticmethod
    def from_json(identifier: str, json: dict):
        jo = JsonObject(json)
        key = jo.jsonget(JsonConstants.SETTING_KEY, mandatory=True)
        description = jo.jsonget(JsonConstants.SETTING_DESCRIPTION)

        scopes = []
        if jo.has(JsonConstants.SETTING_SCOPES):
            for scope_str in jo.jsonget(JsonConstants.SETTING_SCOPES):
                if scope_str in ScopeSetting.__SCOPES:
                    scopes.append(ScopeSetting.__SCOPES[scope_str])
        else:
            scopes += ScopeSetting.__SCOPES.values()

        validator = None
        if jo.has(JsonConstants.SETTING_REGEX):
            validator = RegexValidator(jo.jsonget(JsonConstants.SETTING_REGEX))

        return ScopeSetting(identifier, key, description, scopes, validator=validator)

    def __init__(self, identifier: str, key: str, description: str, scopes: list, default: str = None, validator: callable = None):
        LeafSetting.__init__(self, identifier, key, description=description, default=default, validator=validator)
        self.__scopes = tuple(set(filter(lambda s: isinstance(s, Scope), scopes)))

        if len(self.__scopes) == 0:
            raise ValueError()

    @property
    def scopes(self):
        return self.__scopes

    def find_value(self, *env_providers):
        for env_provider in env_providers:
            out = env_provider.find_value(self.key)
            if out is not None:
                return out
