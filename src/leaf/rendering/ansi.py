"""
Fake Ansi module to manage the lack of colorama module

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import re

from leaf.core.constants import LeafConstants
from leaf.rendering.formatutils import isatty
from leaf.core.utils import version_comparator_lt

# Ansi chars regex
ANSI_CHARS_PATTERN = re.compile(r"\x1b[^m]*m")


def remove_ansi_chars(text):
    return ANSI_CHARS_PATTERN.sub("", text)


class _FakeAnsiFore:

    """
    Optional module colorama is not installed, let's use dummy implementation
    """

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


class _FakeAnsiBack:

    """
    Optional module colorama is not installed, let's use dummy implementation
    """

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


class _FakeAnsiStyle:

    """
    Optional module colorama is not installed, let's use dummy implementation
    """

    BRIGHT = ""
    DIM = ""
    NORMAL = ""
    RESET_ALL = ""


class _Ansi:
    @staticmethod
    def __get_colorama():
        try:
            import colorama

            if "__version__" in dir(colorama) and version_comparator_lt(colorama.__version__, LeafConstants.COLORAMA_MIN_VERSION):
                return None
            elif "VERSION" in dir(colorama) and version_comparator_lt(colorama.VERSION, LeafConstants.COLORAMA_MIN_VERSION):
                return None
            return colorama
        except ImportError:
            return None

    def __init__(self):
        self.__force = False
        self.__colorama = _Ansi.__get_colorama()
        self.__fore, self.__back, self.__style = (_FakeAnsiFore(), _FakeAnsiBack(), _FakeAnsiStyle())

    @property
    def enabled(self):
        return self.__colorama is not None and (self.force or isatty())

    @property
    def force(self):
        return self.__force

    @force.setter
    def force(self, force):
        self.__force = force

    @property
    def fore(self):
        return self.__colorama.Fore if self.enabled else self.__fore

    @property
    def back(self):
        return self.__colorama.Back if self.enabled else self.__back

    @property
    def style(self):
        return self.__colorama.Style if self.enabled else self.__style


ANSI = _Ansi()
