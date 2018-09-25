'''
Used chars

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import sys

'''
Char used to align each cell vertically and horizontally
'''
PADDING_CHAR = ' '

'''
Dictionary of separator chars
keys are in that exact order: up, right, down, left
EXTENDED ASCII chars
'''
_SEPARATORS_EXTENDED_ASCII = {
    (0, 1, 1, 0): '┌',
    (0, 1, 1, 1): '┬',
    (0, 0, 1, 1): '┐',
    (1, 1, 1, 0): '├',
    (1, 1, 1, 1): '┼',
    (1, 0, 1, 1): '┤',
    (1, 1, 0, 0): '└',
    (1, 1, 0, 1): '┴',
    (1, 0, 0, 1): '┘',
    (0, 1, 0, 1): '─',
    (0, 0, 0, 1): '─',
    (0, 1, 0, 0): '─',
    (1, 0, 1, 0): '│',
    (0, 0, 1, 0): '│',
    (1, 0, 0, 0): '│',
    (0, 2, 2, 0): '╔',
    (0, 2, 2, 2): '╦',
    (0, 0, 2, 2): '╗',
    (2, 2, 2, 0): '╠',
    (2, 2, 2, 2): '╬',
    (2, 0, 2, 2): '╣',
    (2, 2, 0, 0): '╚',
    (2, 2, 0, 2): '╩',
    (2, 0, 0, 2): '╝',
    (0, 2, 0, 2): '═',
    (0, 0, 0, 2): '═',
    (0, 2, 0, 0): '═',
    (2, 0, 2, 0): '║',
    (0, 0, 2, 0): '║',
    (2, 0, 0, 0): '║',
    (1, 0, 1, 2): '╡',
    (0, 0, 1, 2): '╕',
    (1, 0, 0, 2): '╛',
    (1, 2, 1, 0): '╞',
    (1, 2, 0, 2): '╧',
    (0, 2, 1, 2): '╤',
    (1, 2, 0, 0): '╘',
    (0, 2, 1, 0): '╒',
    (1, 2, 1, 2): '╪',
    (2, 0, 2, 1): '╢',
    (0, 0, 2, 1): '╖',
    (2, 0, 0, 1): '╜',
    (2, 1, 2, 0): '╟',
    (2, 1, 0, 1): '╨',
    (0, 1, 2, 1): '╥',
    (2, 1, 0, 0): '╙',
    (0, 1, 2, 0): '╓',
    (2, 1, 2, 1): '╫'
}

_SEPARATORS_ASCII = {
    (0, 1, 1, 0): '+',
    (0, 1, 1, 1): '+',
    (0, 0, 1, 1): '+',
    (1, 1, 1, 0): '+',
    (1, 1, 1, 1): '+',
    (1, 0, 1, 1): '+',
    (1, 1, 0, 0): '+',
    (1, 1, 0, 1): '+',
    (1, 0, 0, 1): '+',
    (0, 1, 0, 1): '-',
    (0, 0, 0, 1): '-',
    (0, 1, 0, 0): '-',
    (1, 0, 1, 0): '|',
    (0, 0, 1, 0): '|',
    (1, 0, 0, 0): '|',
    (0, 2, 2, 0): '+',
    (0, 2, 2, 2): '+',
    (0, 0, 2, 2): '+',
    (2, 2, 2, 0): '+',
    (2, 2, 2, 2): '+',
    (2, 0, 2, 2): '+',
    (2, 2, 0, 0): '+',
    (2, 2, 0, 2): '+',
    (2, 0, 0, 2): '+',
    (0, 2, 0, 2): '=',
    (0, 0, 0, 2): '=',
    (0, 2, 0, 0): '=',
    (2, 0, 2, 0): '|',
    (0, 0, 2, 0): '|',
    (2, 0, 0, 0): '|',
    (1, 0, 1, 2): '+',
    (0, 0, 1, 2): '+',
    (1, 0, 0, 2): '+',
    (1, 2, 1, 0): '+',
    (1, 2, 0, 2): '+',
    (0, 2, 1, 2): '+',
    (1, 2, 0, 0): '+',
    (0, 2, 1, 0): '+',
    (1, 2, 1, 2): '+',
    (2, 0, 2, 1): '+',
    (0, 0, 2, 1): '+',
    (2, 0, 0, 1): '+',
    (2, 1, 2, 0): '+',
    (2, 1, 0, 1): '+',
    (0, 1, 2, 1): '+',
    (2, 1, 0, 0): '+',
    (0, 1, 2, 0): '+',
    (2, 1, 2, 1): '+'
}


def getSeparators():
    try:
        # Try to read current encoding detected by Python
        encoding = sys.stdout.encoding
    except Exception:
        # We cannot determine the encoding (probably piped to a file), let's
        # use the best one
        return _SEPARATORS_EXTENDED_ASCII
    try:
        # try to convert the extended ASCII table dictionary to the target
        # encoding
        for c in _SEPARATORS_EXTENDED_ASCII.values():
            c.encode(encoding)
        # No exception ? We can use the extended ASCII dictionary
        return _SEPARATORS_EXTENDED_ASCII
    except Exception:
        # Exception during encoding ? Let's fallback to the ASCII dictionary
        return _SEPARATORS_ASCII
