"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from abc import ABC, abstractmethod

from leaf.model.package import Manifest


class PackageFilter(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def matches(self, mf: Manifest):
        pass


class MetaPackageFilter(PackageFilter):
    def __init__(self):
        self.__filter = AndPackageFilter()

    def matches(self, mf: Manifest):
        return self.__filter.matches(mf)

    def only_master_packages(self):
        self.__filter.add_filter(MasterPackageFilter())
        return self

    def with_tag(self, tags: str):
        if "," in tags:
            orfilter = OrPackageFilter()
            self.__filter.add_filter(orfilter)
            for tag in tags.split(","):
                orfilter.add_filter(TagPackageFilter(tag))
        else:
            self.__filter.add_filter(TagPackageFilter(tags))
        return self

    def with_keyword(self, keywords: str):
        if "," in keywords:
            orfilter = OrPackageFilter()
            self.__filter.add_filter(orfilter)
            for orkw in keywords.split(","):
                orfilter.add_filter(KeywordPackageFilter(orkw))
        else:
            self.__filter.add_filter(KeywordPackageFilter(keywords))
        return self

    def with_names(self, names: list):
        orfilter = OrPackageFilter()
        self.__filter.add_filter(orfilter)
        for name in names:
            orfilter.add_filter(PkgNamePackageFilter(name))
        return self

    def __str__(self):
        if self.__filter.size == 0:
            return "no filter"
        return str(self.__filter)


class OrPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)
        self.__filters = []

    @property
    def size(self):
        return len(self.__filters)

    def add_filter(self, *filters):
        self.__filters += filters

    def matches(self, mf: Manifest):
        if len(self.__filters) == 0:
            return True
        for f in self.__filters:
            if f.matches(mf):
                return True
        return False

    def __str__(self):
        out = " or ".join(map(str, self.__filters))
        if len(self.__filters) > 1:
            out = "({out})".format(out=out)
        return out


class AndPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)
        self.__filters = []

    @property
    def size(self):
        return len(self.__filters)

    def add_filter(self, *filters):
        self.__filters += filters

    def matches(self, mf: Manifest):
        if len(self.__filters) == 0:
            return True
        for f in self.__filters:
            if not f.matches(mf):
                return False
        return True

    def __str__(self):
        return " and ".join(map(str, self.__filters))


class MasterPackageFilter(PackageFilter):
    def __init__(self):
        PackageFilter.__init__(self)

    def matches(self, mf: Manifest):
        return mf.master

    def __str__(self):
        return "only master"


class PkgNamePackageFilter(PackageFilter):
    def __init__(self, name):
        PackageFilter.__init__(self)
        self.__name = name

    def matches(self, mf: Manifest):
        return mf.identifier.name == self.__name

    def __str__(self):
        return "'{name}'".format(name=self.__name)


class TagPackageFilter(PackageFilter):
    def __init__(self, tag):
        PackageFilter.__init__(self)
        self.__tag = tag

    def matches(self, mf: Manifest):
        return self.__tag.lower() in map(str.lower, mf.all_tags)

    def __str__(self):
        return "+{tag}".format(tag=self.__tag)


class KeywordPackageFilter(PackageFilter):
    def __init__(self, kw):
        PackageFilter.__init__(self)
        self.__kw = kw

    def matches(self, mf: Manifest):
        if self.__kw.lower() in str(mf.identifier).lower():
            return True
        if mf.description is not None:
            if self.__kw.lower() in str(mf.description).lower():
                return True
        return False

    def __str__(self):
        return '"{kw}"'.format(kw=self.__kw)
