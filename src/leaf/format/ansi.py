'''
Fake Ansi module to manage the lack of colorama module

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import re
from leaf.format.formatutils import isatty

# Ansi chars regex
ansiCharsRegex = re.compile(r'\x1b[^m]*m')


def removeAnsiChars(text):
    return ansiCharsRegex.sub('', text)


class _FakeAnsiFore():
    '''
    Optional module colorama is not installed, let's use dummy implementation
    '''
    BLACK = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    RESET = ""

    # These are fairly well supported, but not part of the standard.
    LIGHTBLACK_EX = ""
    LIGHTRED_EX = ""
    LIGHTGREEN_EX = ""
    LIGHTYELLOW_EX = ""
    LIGHTBLUE_EX = ""
    LIGHTMAGENTA_EX = ""
    LIGHTCYAN_EX = ""
    LIGHTWHITE_EX = ""


class _FakeAnsiBack():
    '''
    Optional module colorama is not installed, let's use dummy implementation
    '''
    BLACK = ""
    RED = ""
    GREEN = ""
    YELLOW = ""
    BLUE = ""
    MAGENTA = ""
    CYAN = ""
    WHITE = ""
    RESET = ""

    # These are fairly well supported, but not part of the standard.
    LIGHTBLACK_EX = ""
    LIGHTRED_EX = ""
    LIGHTGREEN_EX = ""
    LIGHTYELLOW_EX = ""
    LIGHTBLUE_EX = ""
    LIGHTMAGENTA_EX = ""
    LIGHTCYAN_EX = ""
    LIGHTWHITE_EX = ""


class _FakeAnsiStyle():
    '''
    Optional module colorama is not installed, let's use dummy implementation
    '''
    BRIGHT = ""
    DIM = ""
    NORMAL = ""
    RESET_ALL = ""


class _Ansi():
    def __init__(self):
        self.force = False
        self._fakeFore = _FakeAnsiFore()
        self._fakeBack = _FakeAnsiBack()
        self._fakeStyle = _FakeAnsiStyle()
        try:
            from colorama import Fore as ColoramaFore, Back as ColoramaBack, Style as ColoramaStyle
            self._coloramaFore = ColoramaFore
            self._coloramaBack = ColoramaBack
            self._coloramaStyle = ColoramaStyle
            self.moduleLoaded = True
        except ImportError:
            self.moduleLoaded = False

    def _useActualModule(self):
        return self.moduleLoaded and (self.force or isatty())

    def fore(self):
        if self._useActualModule():
            return self._coloramaFore
        return self._fakeFore

    def back(self):
        if self._useActualModule():
            return self._coloramaBack
        return self._fakeBack

    def style(self):
        if self._useActualModule():
            return self._coloramaStyle
        return self._fakeStyle


ANSI = _Ansi()
