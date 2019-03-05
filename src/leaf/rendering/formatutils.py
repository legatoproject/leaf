"""
Utils to format logger output

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import shlex
import sys
from math import log

from leaf.core.constants import LeafConstants, LeafSettings

"""
Units used to show file size with their respective decimal count
"""
unit_list = [("bytes", 0), ("kB", 0), ("MB", 1), ("GB", 2), ("TB", 2), ("PB", 2)]


def sizeof_fmt(num):
    """
    Human friendly file size
    """
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024 ** exponent
        unit, num_decimals = unit_list[exponent]
        format_string = "{:.%sf} {}" % (num_decimals)  # noqa: P103,S001
        return format_string.format(quotient, unit)
    if num == 0:
        return "0 bytes"
    if num == 1:
        return "1 byte"


def get_leaf_pager():
    """
    Return the appropriate pager
    If the user uses a custom pager, use it.
    If the user sets empty string, pager is disabled
    Else use less as pager
    """
    pager = LeafSettings.PAGER.value
    if pager is None:
        # Default pager
        pager = LeafConstants.DEFAULT_PAGER
    elif pager == "":
        # Pager is disabled
        pager = None
    elif " " in pager:
        # Complex command
        pager = shlex.split(pager)
    return pager


def isatty():
    """
    Return true if we are in a tty context
    """
    return sys.stdout.isatty()
