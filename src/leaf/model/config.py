'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict
from leaf.constants import JsonConstants, LeafFiles
from pathlib import Path

from leaf.model.base import JsonObject
from leaf.model.environment import IEnvObject


class UserConfiguration(JsonObject, IEnvObject):
    '''
    Represent a user configuration
    '''

    def __init__(self, json):
        JsonObject.__init__(self, json)
        IEnvObject.__init__(self, "user configuration")

    def getEnvMap(self):
        if JsonConstants.CONFIG_ENV not in self.json:
            self.json[JsonConstants.CONFIG_ENV] = OrderedDict()
        return self.json[JsonConstants.CONFIG_ENV]

    def getRemotesMap(self):
        if JsonConstants.CONFIG_REMOTES not in self.json:
            self.json[JsonConstants.CONFIG_REMOTES] = OrderedDict()
        return self.json[JsonConstants.CONFIG_REMOTES]

    def getRootFolder(self):
        if JsonConstants.CONFIG_ROOT in self.json:
            return Path(self.json[JsonConstants.CONFIG_ROOT])
        # Default value
        return LeafFiles.DEFAULT_LEAF_ROOT

    def setRootFolder(self, folder):
        self.json[JsonConstants.CONFIG_ROOT] = str(folder)


class WorkspaceConfiguration(JsonObject, IEnvObject):
    '''
    Represent a workspace configuration, ie Profiles, env ...
    '''

    def __init__(self, json):
        JsonObject.__init__(self, json)
        IEnvObject.__init__(self, "workspace")

    def getEnvMap(self):
        if JsonConstants.WS_ENV not in self.json:
            self.json[JsonConstants.WS_ENV] = OrderedDict()
        return self.json[JsonConstants.WS_ENV]

    def getProfilesMap(self):
        if JsonConstants.WS_PROFILES not in self.json:
            self.json[JsonConstants.WS_PROFILES] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILES]
