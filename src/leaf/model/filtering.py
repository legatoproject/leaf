'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import ABC, abstractmethod


class PackageFilter(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def matches(self, mf):
        pass


class MetaPackageFilter(PackageFilter):

    def __init__(self):
        self.filter = AndPackageFilter()

    def matches(self, mf):
        return self.filter.matches(mf)

    def onlyMasterPackages(self):
        self.filter.addFilter(MasterPackageFilter())
        return self

    def withTag(self, tag):
        if "," in tag:
            orFilter = OrPackageFilter()
            self.filter.addFilter(orFilter)
            for ortag in tag.split(","):
                orFilter.addFilter(TagPackageFilter(ortag))
        else:
            self.filter.addFilter(TagPackageFilter(tag))
        return self

    def withKeyword(self, kw):
        if "," in kw:
            orFilter = OrPackageFilter()
            self.filter.addFilter(orFilter)
            for orkw in kw.split(","):
                orFilter.addFilter(KeywordPackageFilter(orkw))
        else:
            self.filter.addFilter(KeywordPackageFilter(kw))
        return self

    def withNames(self, nameList):
        orFilter = OrPackageFilter()
        self.filter.addFilter(orFilter)
        for name in nameList:
            orFilter.addFilter(PkgNamePackageFilter(name))
        return self

    def __str__(self):
        if len(self.filter.filters) == 0:
            return "no filter"
        return str(self.filter)


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

    def __str__(self):
        out = " or ".join(map(str, self.filters))
        if len(self.filters) > 1:
            out = "(%s)" % out
        return out


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

    def __str__(self):
        return " and ".join(map(str, self.filters))


class MasterPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)

    def matches(self, mf):
        return mf.isMaster()

    def __str__(self):
        return "only master"


class PkgNamePackageFilter(PackageFilter):
    def __init__(self, name):
        PackageFilter.__init__(self)
        self.name = name

    def matches(self, mf):
        return mf.getIdentifier().name == self.name

    def __str__(self):
        return "'%s'" % self.name


class TagPackageFilter(PackageFilter):
    def __init__(self, tag):
        PackageFilter.__init__(self)
        self.tag = tag

    def matches(self, mf):
        return self.tag.lower() in map(str.lower, mf.getAllTags())

    def __str__(self):
        return "+%s" % self.tag


class KeywordPackageFilter(PackageFilter):
    def __init__(self, kw):
        PackageFilter.__init__(self)
        self.kw = kw

    def matches(self, mf):
        if self.kw.lower() in str(mf.getIdentifier()).lower():
            return True
        if mf.getDescription() is not None and self.kw.lower() in str(mf.getDescription()).lower():
            return True
        return False

    def __str__(self):
        return "\"%s\"" % self.kw
