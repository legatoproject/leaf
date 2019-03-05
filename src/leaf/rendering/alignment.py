"""
Vertical and horizontal alignment code

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import math
from enum import Enum, unique

from leaf.rendering.ansi import remove_ansi_chars


def _top_align(lines: list, height: int) -> list:
    """
    Vertical align a list of string based on the given height
    """
    out = lines.copy()
    out.extend([""] * (height - len(lines)))
    return out


def _middle_align(lines: list, height: int) -> list:
    """
    Vertical align a list of string based on the given height
    """
    # Calculate lines above and under
    diff = height - len(lines)
    above_lines_count = under_lines_count = math.floor(diff / 2)
    if diff % 2 != 0:
        under_lines_count += 1

    # Add blank lines
    out = [""] * above_lines_count
    out.extend(lines)
    out.extend([""] * under_lines_count)
    return out


def _bottom_align(lines: list, height: int) -> list:
    """
    Vertical align a list of string based on the given height
    """
    out = [""] * (height - len(lines))
    out.extend(lines)
    return out


def _align_without_ansi_chars(h_align_funct: callable):
    def wrap(text, size, spanchar):
        extrasize = len(text) - len(remove_ansi_chars(text))
        return h_align_funct(text, size + extrasize, spanchar)

    return wrap


@unique
class HAlign(Enum):

    """
    Types of Horizontal alignment
    """

    LEFT = _align_without_ansi_chars(str.ljust)
    CENTER = _align_without_ansi_chars(str.center)
    RIGHT = _align_without_ansi_chars(str.rjust)


@unique
class VAlign(Enum):

    """
    Types of Vertical alignment
    """

    TOP = _top_align
    MIDDLE = _middle_align
    BOTTOM = _bottom_align
