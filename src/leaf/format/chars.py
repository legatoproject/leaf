'''
Used chars

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

'''
Char used to align each cell vertically and horizontally
'''
_PADDING_CHAR = ' '

'''
Dictionary of separator chars
keys are in that exact order: up, right, down, left
'''
_SEPARATORS_DICT = {
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
