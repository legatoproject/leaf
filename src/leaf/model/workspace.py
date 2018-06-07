'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from collections import OrderedDict
from leaf.constants import JsonConstants, LeafFiles, LeafConstants

from leaf.model.base import JsonObject, Environment
from leaf.model.package import InstalledPackage, PackageIdentifier


class Profile(JsonObject):
    '''
    Represent a profile inside a workspace
    '''

    @staticmethod
    def genDefaultName(piList):
        if piList is not None and len(piList) > 0:
            return Profile.checkValidName("_".join([pi.name.upper() for pi in piList]))
        return LeafConstants.DEFAULT_PROFILE

    @staticmethod
    def checkValidName(name):
        if not isinstance(name, str):
            raise ValueError("Profile name must be a string")
        if name in ["", LeafFiles.CURRENT_PROFILE_LINKNAME]:
            raise ValueError("'%s' is not a valid profile name" % name)
        return name

    @staticmethod
    def emptyProfile(name, folder):
        out = Profile(Profile.checkValidName(name), folder, OrderedDict())
        out.getPackages()
        out.getEnvMap()
        return out

    def __init__(self, name, folder, json):
        JsonObject.__init__(self, json)
        self.name = name
        self.folder = folder
        self.isCurrentProfile = False

    def getEnvMap(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILE_ENV,
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
        return Environment("Exported by profile %s" % self.name,
                           self.getEnvMap())

    def getPackages(self):
        return self.jsoninit(key=JsonConstants.WS_PROFILE_PACKAGES,
                             value=[])

    def getPackageIdentifiers(self):
        return list(map(PackageIdentifier.fromString,
                        self.getPackages()))

    def getPackageMap(self):
        out = OrderedDict()
        for pi in self.getPackageIdentifiers():
            if pi.name not in out:
                out[pi.name] = pi
        return out

    def setPackages(self, piList):
        self.json[JsonConstants.WS_PROFILE_PACKAGES] = [str(pi)
                                                        for pi in piList]

    def getLinkedPackages(self):
        '''
        Return a list of linked packages
        '''
        out = []
        for link in self.folder.iterdir():
            if link.is_symlink():
                try:
                    out.append(InstalledPackage(link / LeafFiles.MANIFEST))
                except:
                    pass
        return out
