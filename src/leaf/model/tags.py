"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from profile import Profile

from leaf.model.modelutils import group_package_identifiers_by_name
from leaf.model.package import IDENTIFIER_GETTER


class TagUtils:

    """
    Class used to tag packages
    """

    LATEST = "latest"
    INSTALLED = "installed"
    CURRENT = "current"

    @staticmethod
    def tag_latest(mflist: list):
        """
        Add the 'latest' tag to packages with the latest version
        """
        latest_pilist = []
        for pkg_versions in group_package_identifiers_by_name(map(IDENTIFIER_GETTER, mflist)).values():
            latest_pilist.append(pkg_versions[-1])
        for mf in mflist:
            if mf.identifier in latest_pilist:
                mf.custom_tags.append(TagUtils.LATEST)

    @staticmethod
    def tag_installed(mflist: list, installed_pilist: list):
        """
        Tag packages from given mfList as installed if they are in the given piList
        """
        for mf in filter(lambda mf: mf.identifier in installed_pilist, mflist):
            mf.custom_tags.append(TagUtils.INSTALLED)

    @staticmethod
    def tag_current(mflist: list, pf: Profile):
        """
        Tag packages in mfList as current if they are in the given profile
        """
        for mf in filter(lambda mf: str(mf.identfier) in pf.packages, mflist):
            mf.custom_tags.append(TagUtils.CURRENT)
