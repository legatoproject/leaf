"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from collections import OrderedDict

from leaf.core.constants import JsonConstants, LeafConstants, LeafFiles
from leaf.core.error import LeafException
from leaf.core.jsonutils import JsonObject
from leaf.model.environment import Environment, IEnvProvider
from leaf.model.package import InstalledPackage, PackageIdentifier


class Profile(JsonObject, IEnvProvider):

    """
    Represent a profile inside a workspace
    """

    __RESERVED_NAMES = ("", LeafFiles.CURRENT_PROFILE_LINKNAME)

    @staticmethod
    def generate_default_name(pilist):
        if pilist is not None and len(pilist) > 0:
            return Profile.check_valid_name("_".join([pi.name.upper() for pi in pilist]))
        return LeafConstants.DEFAULT_PROFILE

    @staticmethod
    def check_valid_name(name):
        if not isinstance(name, str):
            raise LeafException("Profile name must be a string")
        if name in Profile.__RESERVED_NAMES:
            raise LeafException("'{name}' is not a valid profile name".format(name=name))
        if " " in name:
            raise LeafException("Profile cannot contain space")
        return name

    def __init__(self, name, folder, json):
        JsonObject.__init__(self, json)
        IEnvProvider.__init__(self, "profile {name}".format(name=name))
        self.__name = name
        self.__folder = folder
        self.__current = False

    @property
    def name(self):
        return self.__name

    @property
    def folder(self):
        return self.__folder

    @property
    def is_current(self):
        return self.__current

    @is_current.setter
    def is_current(self, value):
        self.__current = value

    def _getenvmap(self):
        if JsonConstants.WS_PROFILE_ENV not in self.json:
            self.json[JsonConstants.WS_PROFILE_ENV] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILE_ENV]

    @property
    def packages(self):
        out = []
        for pkgname, pkgversion in self.pkg_map.items():
            out.append(PackageIdentifier(pkgname, pkgversion))
        return out

    def add_packages(self, pilist):
        pkgmap = self.pkg_map
        for pi in pilist:
            pkgmap[pi.name] = pi.version

    def remove_packages(self, pilist):
        pkgmap = self.pkg_map
        for pi in self.packages:
            if pi in pilist:
                del pkgmap[pi.name]

    @property
    def pkg_map(self):
        if JsonConstants.WS_PROFILE_PACKAGES not in self.json:
            self.json[JsonConstants.WS_PROFILE_PACKAGES] = OrderedDict()
        return self.json[JsonConstants.WS_PROFILE_PACKAGES]

    def list_linked_packages(self) -> list:
        """
        Return a list of linked packages
        """
        out = []
        for link in self.__folder.iterdir():
            if link.is_symlink():
                try:
                    out.append(InstalledPackage(link / LeafFiles.MANIFEST))
                except Exception:
                    pass
        return out

    def build_environment(self) -> Environment:
        out = super().build_environment()
        out.set_variable("LEAF_PROFILE", self.name, replace=True, prepend=True)
        return out

    def __str__(self):
        return self.__name
