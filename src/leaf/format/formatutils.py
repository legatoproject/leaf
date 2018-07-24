'''
Utils to format logger output

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from math import log
from shutil import which
import os
import sys


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


def getPager():
    '''
    Return the appropriate pager
    Check $PAGER env var, if not set use less with some args
    If set to less without args; return less with args
    If set to empty or less with args or anything else, return None
    '''
    pager = os.getenv("PAGER", "less").split(' ')
    binName = pager[0]
    if which(binName) is None:
        pager = None
    elif len(pager) == 1:
        if binName == "":
            pager = None
        if binName == "less":
            pager = ("less", "-r", "-S", "-P", "Leaf -- Press q to exit")
    return pager


def isatty():
    '''
    Return true if we are in a tty context
    '''
    return sys.stdout.isatty()
