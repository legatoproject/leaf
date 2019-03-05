"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from enum import IntEnum, unique


@unique
class Scope(IntEnum):
    LEAF = 0
    USER = 1
    WORKSPACE = 2
    PROFILE = 3
    PACKAGE = 4
