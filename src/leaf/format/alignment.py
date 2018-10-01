'''
Vertical and horizontal alignment code

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import math
from enum import unique, Enum
from leaf.format.ansi import removeAnsiChars


def _topAlign(lines, height):
    '''
    Vertical align a list of string based on the given height
    '''
    out = lines.copy()
    out.extend([""] * (height - len(lines)))
    return out


def _middleAlign(lines, height):
    '''
    Vertical align a list of string based on the given height
    '''
    # Calculate lines above and under
    diff = height - len(lines)
    aboveLinesCount = underLinesCount = math.floor(diff / 2)
    if diff % 2 != 0:
        underLinesCount += 1

    # Add blank lines
    out = [""] * aboveLinesCount
    out.extend(lines)
    out.extend([""] * underLinesCount)
    return out


def _bottomAlign(lines, height):
    '''
    Vertical align a list of string based on the given height
    '''
    out = [""] * (height - len(lines))
    out.extend(lines)
    return out


def _alignWithoutAnsiChars(hAlignFunct):
    def wrap(text, size, spanChar):
        extraSize = len(text) - len(removeAnsiChars(text))
        return hAlignFunct(text, size + extraSize, spanChar)
    return wrap


@unique
class HAlign(Enum):
    '''
    Types of Horizontal alignment
    '''
    LEFT = _alignWithoutAnsiChars(str.ljust)
    CENTER = _alignWithoutAnsiChars(str.center)
    RIGHT = _alignWithoutAnsiChars(str.rjust)


@unique
class VAlign(Enum):
    '''
    Types of Vertical alignment
    '''
    TOP = _topAlign
    MIDDLE = _middleAlign
    BOTTOM = _bottomAlign
