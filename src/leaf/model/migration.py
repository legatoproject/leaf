"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.core.constants import LeafSettings


class LegacyJsonConstants:
    CONFIG_ROOTFOLDER = "rootfolder"


def update_root_folder(user_config):
    if LegacyJsonConstants.CONFIG_ROOTFOLDER in user_config.json:
        user_config._getenvmap()[LeafSettings.USER_PKG_FOLDER.key] = user_config.json[LegacyJsonConstants.CONFIG_ROOTFOLDER]
        del user_config.json[LegacyJsonConstants.CONFIG_ROOTFOLDER]
