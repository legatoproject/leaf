"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from profile import Profile

from leaf.model.modelutils import keep_latest
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
        # Split packages into groups based on tags
        tag_groups = {}
        for mf in mflist:
            tag = tuple(sorted(mf.tags))
            pi = IDENTIFIER_GETTER(mf)
            if tag not in tag_groups:
                tag_groups[tag] = [pi]
            else:
                tag_groups[tag].append(pi)

        # Gather latest packages from each group
        latest_pilist = []
        for _, packages in tag_groups.items():
            latest_pilist += keep_latest(packages)

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
        for mf in filter(lambda mf: mf.identfier in pf.packages, mflist):
            mf.custom_tags.append(TagUtils.CURRENT)
