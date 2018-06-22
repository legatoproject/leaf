'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict
from leaf.constants import JsonConstants, LeafFiles
from leaf.model.base import JsonObject, Environment
from pathlib import Path


class UserConfiguration(JsonObject):
    '''
    Represent a user configuration
    '''

    def __init__(self, json):
        JsonObject.__init__(self, json)

    def getEnvMap(self):
        return self.jsoninit(key=JsonConstants.CONFIG_ENV,
                             value=OrderedDict())

    def updateEnv(self, setMap=None, unsetList=None):
        envMap = self.getEnvMap()
        if setMap is not None:
            envMap.update(setMap)
        if unsetList is not None:
            for k in unsetList:
                if k in envMap:
                    del envMap[k]

    def getEnvironment(self):
        return Environment("Exported by user configuration",
                           self.getEnvMap())

    def getRemotes(self):
        return self.jsoninit(key=JsonConstants.CONFIG_REMOTES, value=OrderedDict())

    def getRootFolder(self):
        return Path(self.jsoninit(key=JsonConstants.CONFIG_ROOT,
                                  value=str(LeafFiles.DEFAULT_LEAF_ROOT)))

    def setRootFolder(self, folder):
        self.jsoninit(key=JsonConstants.CONFIG_ROOT,
                      value=str(folder),
                      force=True)


class WorkspaceConfiguration(JsonObject):
    '''
    Represent a workspace configuration, ie Profiles, env ...
    '''

    def __init__(self, json):
        JsonObject.__init__(self, json)

    def getEnvMap(self):
        return self.jsoninit(key=JsonConstants.WS_ENV,
                             value=OrderedDict())

    def updateEnv(self, setMap=None, unsetList=None):
        envMap = self.getEnvMap()
        if setMap is not None:
            envMap.update(setMap)
        if unsetList is not None:
            for k in unsetList:
                if k in envMap:
                    del envMap[k]

    def getEnvironment(self):
        return Environment("Exported by workspace",
                           self.getEnvMap())

    def getProfiles(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILES,
                             value=OrderedDict())
