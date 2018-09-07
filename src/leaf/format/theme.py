'''
This module describe how colors and style applies to each kind of printed element

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
'''
Documentation printed at the beginning of the configuration file
'''

from _io import StringIO
from collections import OrderedDict
import configparser
import sys

from leaf.format.ansi import ANSI

'''
Map between configuration file and actual code
'''
THEME_GRAMAR = {
    "F_BLACK": (lambda: ANSI.fore().BLACK),
    "F_RED": (lambda: ANSI.fore().RED),
    "F_GREEN": (lambda: ANSI.fore().GREEN),
    "F_YELLOW": (lambda: ANSI.fore().YELLOW),
    "F_BLUE": (lambda: ANSI.fore().BLUE),
    "F_MAGENTA": (lambda: ANSI.fore().MAGENTA),
    "F_CYAN": (lambda: ANSI.fore().CYAN),
    "F_WHITE": (lambda: ANSI.fore().WHITE),
    "F_LIGHTBLACK": (lambda: ANSI.fore().LIGHTBLACK_EX),
    "F_LIGHTRED": (lambda: ANSI.fore().LIGHTRED_EX),
    "F_LIGHTGREEN": (lambda: ANSI.fore().LIGHTGREEN_EX),
    "F_LIGHTYELLOW": (lambda: ANSI.fore().LIGHTYELLOW_EX),
    "F_LIGHTBLUE": (lambda: ANSI.fore().LIGHTBLUE_EX),
    "F_LIGHTMAGENTA": (lambda: ANSI.fore().LIGHTMAGENTA_EX),
    "F_LIGHTCYAN": (lambda: ANSI.fore().LIGHTCYAN_EX),
    "F_LIGHTWHITE": (lambda: ANSI.fore().LIGHTWHITE_EX),
    "B_BLACK": (lambda: ANSI.back().BLACK),
    "B_RED": (lambda: ANSI.back().RED),
    "B_GREEN": (lambda: ANSI.back().GREEN),
    "B_YELLOW": (lambda: ANSI.back().YELLOW),
    "B_BLUE": (lambda: ANSI.back().BLUE),
    "B_MAGENTA": (lambda: ANSI.back().MAGENTA),
    "B_CYAN": (lambda: ANSI.back().CYAN),
    "B_WHITE": (lambda: ANSI.back().WHITE),
    "B_LIGHTBLACK": (lambda: ANSI.back().LIGHTBLACK_EX),
    "B_LIGHTRED": (lambda: ANSI.back().LIGHTRED_EX),
    "B_LIGHTGREEN": (lambda: ANSI.back().LIGHTGREEN_EX),
    "B_LIGHTYELLOW": (lambda: ANSI.back().LIGHTYELLOW_EX),
    "B_LIGHTBLUE": (lambda: ANSI.back().LIGHTBLUE_EX),
    "B_LIGHTMAGENTA": (lambda: ANSI.back().LIGHTMAGENTA_EX),
    "B_LIGHTCYAN": (lambda: ANSI.back().LIGHTCYAN_EX),
    "B_LIGHTWHITE": (lambda: ANSI.back().LIGHTWHITE_EX),
    "BRIGHT": (lambda: ANSI.style().BRIGHT),
    "DIM": (lambda: ANSI.style().DIM),
    "NORMAL": (lambda: ANSI.style().NORMAL)
}


class _Theme():
    '''
    This enum list the available themes that can be used all over the application
    '''

    def __init__(self, themeManager, name):
        self.tm = themeManager
        self.name = name

    def __call__(self, text):
        '''
        Each theme can be used as a function
        '''
        text = str(text)
        if self == self.tm.VOID:
            return text
        if self == self.tm.RESET:
            raise ValueError("ThemeManager.RESET cannot be used as a function")
        return self.tm._decorate(self.name, text)

    def __str__(self):
        '''
        Let use a theme directly inside a string
        '''
        if self == self.tm.VOID:
            return ""
        if self == self.tm.RESET:
            return ANSI.style().RESET_ALL
        return self.tm._toString(self.name)

    def __add__(self, other):
        '''
        Combine 2 themes by using '+'
        '''
        return lambda text: other(self(text))


class ThemedIOWrapper(StringIO):
    '''
    Encapsulate stream with ansi chars of the give theme
    '''

    def __init__(self, stream, theme):
        self.stream = stream
        self.theme = theme

    def write(self, txt):
        self.stream.write(self.theme(txt))


class ThemeManager():
    '''
    Manage theme configuration file and overriding behavior
    '''

    def __init__(self, themesFile):
        '''
        Write configuration file if it does'nt exist the load it
        '''
        self.theme = None
        if themesFile is not None and themesFile.exists():
            themeConfig = configparser.ConfigParser()
            themeConfig.read(str(themesFile))
            # Pick the default theme
            self.theme = themeConfig["DEFAULT"]
            # if a selected entry is detected
            if "selected" in self.theme:
                selThemeName = themeConfig["DEFAULT"]["selected"]
                # check if it have it's own section
                if selThemeName in themeConfig:
                    # Get the corresponding theme
                    self.theme = themeConfig[selThemeName]

        if self.theme is None:
            self.theme = self._getDefaultTheme()

        self._createThemes()

        # Let's set the right theme on all stderr
        sys.stderr = ThemedIOWrapper(sys.stderr, self.ERROR)

    def _decorate(self, styleKey, text):
        '''
        Encapsulate text in appropriate ansi chars (if in tty and lib is available)
        '''
        combinedThemes = self._toString(styleKey)
        if len(combinedThemes) > 0:
            return combinedThemes + text + ANSI.style().RESET_ALL
        return text

    def _toString(self, styleKey):
        '''
        Convert theme to a string
        '''
        combinedThemes = ""
        styleKey = styleKey.lower()
        if styleKey in self.theme:
            # Get the value of the property of the theme
            eltValue = self.theme[styleKey]
            for style in eltValue.split('+'):
                style = style.strip()  # remove left and right spaces
                if style in THEME_GRAMAR:
                    # Translate it to code using grammar dict
                    themeProvider = THEME_GRAMAR[style]
                    combinedThemes += themeProvider()
        return combinedThemes

    def colorizeTag(self, text):
        '''
        Encapsulate tag in appropriate ansi chars (if in tty and lib is available)
        '''
        return self._decorate("tag." + text, text)

    def _getDefaultTheme(self):
        '''
        Write default theme configuration file
        '''
        return OrderedDict((
            ("error", "BRIGHT + F_RED"),
            ("hints", "F_GREEN"),
            ("hints_commands", "BRIGHT + B_GREEN"),
            ("label", "BRIGHT"),
            ("table_separator", "F_LIGHTBLACK"),
            ("tag.current", "F_GREEN"),
            ("tag.installed", "F_GREEN"),
            ("tag.latest", "F_CYAN"),
            ("remote_disabled", "F_LIGHTBLACK"),
            ("profile_current", "F_GREEN")))

    def _createThemes(self):
        # Special instances
        self.VOID = _Theme(self, "void")  # Used as a default/identity function
        self.RESET = _Theme(self, "reset")  # Used to end a theme

        # Error messages
        self.ERROR = _Theme(self, "error")  # Used for error messages
        self.HINTS = _Theme(self, "hints")  # Used for hints
        self.HINTS_COMMANDS = _Theme(
            self, "hints_commands")  # Used for commands in hints

        # Tables
        self.LABEL = _Theme(self, "label")
        self.TABLE_SEPARATOR = _Theme(self, "table_separator")

        # Remote
        self.REMOTE_DISABLED = _Theme(self, "remote_disabled")

        # Profile
        self.PROFILE_CURRENT = _Theme(self, "profile_current")
