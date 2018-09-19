'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict
from pathlib import Path

from leaf import __version__
from leaf.constants import JsonConstants, LeafFiles
from leaf.model.base import ConfigFileWithLayer
from leaf.model.environment import IEnvObject
from leaf.utils import checkSupportedLeaf


class UserConfiguration(ConfigFileWithLayer, IEnvObject):
    '''
    Represent a user configuration
    '''

    def __init__(self, *layers):
        ConfigFileWithLayer.__init__(self, *layers)
        IEnvObject.__init__(self, "user configuration")

    def _checkModel(self):
        super()._checkModel()
        # Check that all remotes have an URL
        if JsonConstants.CONFIG_REMOTES in self.json:
            remotes = self.json[JsonConstants.CONFIG_REMOTES]
            for alias in [alias
                          for alias, value in remotes.items()
                          if JsonConstants.CONFIG_REMOTE_URL not in value]:
                del remotes[alias]

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


class WorkspaceConfiguration(ConfigFileWithLayer, IEnvObject):
    '''
    Represent a workspace configuration, ie Profiles, env ...
    '''

    def __init__(self, *layers):
        ConfigFileWithLayer.__init__(self, *layers)
        IEnvObject.__init__(self, "workspace")

    def _checkModel(self):
        checkSupportedLeaf(self.jsonget(JsonConstants.INFO_LEAF_MINVER),
                           exceptionMessage="Leaf has to be updated to work with this workspace")
        self.json[JsonConstants.INFO_LEAF_MINVER] = __version__

    def getEnvMap(self):
        if JsonConstants.WS_ENV not in self.json:
            self.json[JsonConstants.WS_ENV] = OrderedDict()
        return self.json[JsonConstants.WS_ENV]

    def getProfilesMap(self):
        if JsonConstants.WS_PROFILES not in self.json:
            self.json[JsonConstants.WS_PROFILES] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILES]
