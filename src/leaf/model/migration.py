"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from collections import OrderedDict

from leaf.core.constants import JsonConstants, LeafSettings
from leaf.model.package import PackageIdentifier


class LegacyJsonConstants:
    CONFIG_ROOTFOLDER = "rootfolder"


def update_root_folder(user_config):
    if LegacyJsonConstants.CONFIG_ROOTFOLDER in user_config.json:
        user_config._getenvmap()[LeafSettings.USER_PKG_FOLDER.key] = user_config.json[LegacyJsonConstants.CONFIG_ROOTFOLDER]
        del user_config.json[LegacyJsonConstants.CONFIG_ROOTFOLDER]


def update_packages_map(ws_config):
    node_root = ws_config.json
    if JsonConstants.WS_PROFILES in node_root:
        for node_profile in node_root[JsonConstants.WS_PROFILES].values():
            if JsonConstants.WS_PROFILE_PACKAGES in node_profile:
                node_packages = node_profile[JsonConstants.WS_PROFILE_PACKAGES]
                if isinstance(node_packages, list):
                    # Proceed migration list -> map
                    packages_map = OrderedDict()
                    for pi in PackageIdentifier.parse_list(node_packages):
                        packages_map[pi.name] = pi.version
                    node_profile[JsonConstants.WS_PROFILE_PACKAGES] = packages_map
