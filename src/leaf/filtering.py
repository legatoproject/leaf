'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import ABC, abstractmethod


class PackageFilter(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def matches(self, mf):
        pass


class OrPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)
        self.filters = []

    def addFilter(self, *filters):
        self.filters += filters

    def matches(self, mf):
        if len(self.filters) == 0:
            return True
        for f in self.filters:
            if f.matches(mf):
                return True
        return False


class AndPackageFilter(OrPackageFilter):
    def __init__(self):
        OrPackageFilter.__init__(self)

    def matches(self, mf):
        if len(self.filters) == 0:
            return True
        for f in self.filters:
            if not f.matches(mf):
                return False
        return True


class SupportedOsPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)

    def matches(self, mf):
        return mf.isSupportedOs()


class MasterPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)

    def matches(self, mf):
        return mf.isMaster()


class PkgNamePackageFilter(PackageFilter):
    def __init__(self, pkgNameList):
        PackageFilter.__init__(self)
        self.pkgNameList = pkgNameList

    def matches(self, mf):
        if self.pkgNameList is not None:
            return mf.getIdentifier().name in self.pkgNameList
        return True


class ModulePackageFilter(PackageFilter):
    def __init__(self, moduleList):
        PackageFilter.__init__(self)
        self.moduleList = moduleList

    def matches(self, mf):
        if self.moduleList is not None:
            if mf.getSupportedModules() is not None:
                for module in self.moduleList:
                    for supportedModule in mf.getSupportedModules():
                        if module.lower() in supportedModule.lower():
                            return True
            return False
        return True


class KeywordPackageFilter(PackageFilter):
    def __init__(self, kwList):
        PackageFilter.__init__(self)
        self.kwList = kwList

    def matches(self, mf):
        if self.kwList is not None:
            for m in self.kwList:
                if m.lower() in str(mf.getIdentifier()).lower():
                    return True
            return False
        return True
