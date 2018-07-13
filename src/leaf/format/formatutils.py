'''
Utils to format logger output

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from math import log

'''
Units used to show file size with their respective decimal count
'''
unit_list = [
    ('bytes', 0),
    ('kB', 0),
    ('MB', 1),
    ('GB', 2),
    ('TB', 2),
    ('PB', 2)
]


def sizeof_fmt(num):
    '''
    Human friendly file size
    '''
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        format_string = '{:.%sf} {}' % (num_decimals)
        return format_string.format(quotient, unit)
    if num == 0:
        return '0 bytes'
    if num == 1:
        return '1 byte'
