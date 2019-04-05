"""
This module describe how colors and style applies to each kind of printed element

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import configparser

from leaf.core.constants import LeafSettings
from leaf.rendering.ansi import ANSI

"""
Map between configuration file and actual code
"""
THEME_GRAMAR = {
    "F_BLACK": (lambda: ANSI.fore.BLACK),
    "F_RED": (lambda: ANSI.fore.RED),
    "F_GREEN": (lambda: ANSI.fore.GREEN),
    "F_YELLOW": (lambda: ANSI.fore.YELLOW),
    "F_BLUE": (lambda: ANSI.fore.BLUE),
    "F_MAGENTA": (lambda: ANSI.fore.MAGENTA),
    "F_CYAN": (lambda: ANSI.fore.CYAN),
    "F_WHITE": (lambda: ANSI.fore.WHITE),
    "F_LIGHTBLACK": (lambda: ANSI.fore.LIGHTBLACK_EX),
    "F_LIGHTRED": (lambda: ANSI.fore.LIGHTRED_EX),
    "F_LIGHTGREEN": (lambda: ANSI.fore.LIGHTGREEN_EX),
    "F_LIGHTYELLOW": (lambda: ANSI.fore.LIGHTYELLOW_EX),
    "F_LIGHTBLUE": (lambda: ANSI.fore.LIGHTBLUE_EX),
    "F_LIGHTMAGENTA": (lambda: ANSI.fore.LIGHTMAGENTA_EX),
    "F_LIGHTCYAN": (lambda: ANSI.fore.LIGHTCYAN_EX),
    "F_LIGHTWHITE": (lambda: ANSI.fore.LIGHTWHITE_EX),
    "B_BLACK": (lambda: ANSI.back.BLACK),
    "B_RED": (lambda: ANSI.back.RED),
    "B_GREEN": (lambda: ANSI.back.GREEN),
    "B_YELLOW": (lambda: ANSI.back.YELLOW),
    "B_BLUE": (lambda: ANSI.back.BLUE),
    "B_MAGENTA": (lambda: ANSI.back.MAGENTA),
    "B_CYAN": (lambda: ANSI.back.CYAN),
    "B_WHITE": (lambda: ANSI.back.WHITE),
    "B_LIGHTBLACK": (lambda: ANSI.back.LIGHTBLACK_EX),
    "B_LIGHTRED": (lambda: ANSI.back.LIGHTRED_EX),
    "B_LIGHTGREEN": (lambda: ANSI.back.LIGHTGREEN_EX),
    "B_LIGHTYELLOW": (lambda: ANSI.back.LIGHTYELLOW_EX),
    "B_LIGHTBLUE": (lambda: ANSI.back.LIGHTBLUE_EX),
    "B_LIGHTMAGENTA": (lambda: ANSI.back.LIGHTMAGENTA_EX),
    "B_LIGHTCYAN": (lambda: ANSI.back.LIGHTCYAN_EX),
    "B_LIGHTWHITE": (lambda: ANSI.back.LIGHTWHITE_EX),
    "BRIGHT": (lambda: ANSI.style.BRIGHT),
    "DIM": (lambda: ANSI.style.DIM),
    "NORMAL": (lambda: ANSI.style.NORMAL),
}


class _Theme:

    """
    This enum list the available themes that can be used all over the application
    """

    def __init__(self, tm, name):
        self.tm = tm
        self.name = name

    def __call__(self, text):
        """
        Each theme can be used as a function
        """
        text = str(text)
        if self == ThemeManager.VOID:
            return text
        if self == self.tm.RESET:
            raise ValueError("ThemeManager.RESET cannot be used as a function")
        return self.tm._decorate(self.name, text)

    def __str__(self):
        """
        Let use a theme directly inside a string
        """
        if self == ThemeManager.VOID:
            return ""
        if self == self.tm.RESET:
            return ANSI.style.RESET_ALL
        return self.tm._tostring(self.name)

    def __add__(self, other):
        """
        Combine 2 themes by using '+'
        """
        return lambda text: other(self(text))


class ThemeManager:

    """
    Manage theme configuration file and overriding behavior
    """

    VOID = _Theme(None, "void")  # Used as a default/identity function
    __DEFAULT_THEME = {
        "question": "F_YELLOW",
        "error": "F_RED",
        "error_title": "F_RED",
        "error_message": "F_RED + BRIGHT",
        "hints": "F_GREEN",
        "hints_commands": "BRIGHT + F_GREEN",
        "label": "BRIGHT",
        "table_separator": "F_LIGHTBLACK",
        "tag.current": "F_GREEN",
        "tag.installed": "F_GREEN",
        "tag.latest": "F_CYAN",
        "tag.system": "F_LIGHTRED",
        "remote_disabled": "F_LIGHTBLACK",
        "profile_current": "F_GREEN",
    }

    def __init__(self, themefile=None):
        """
        Write configuration file if it does'nt exist the load it
        """
        self.theme = ThemeManager.__DEFAULT_THEME
        if themefile is not None and themefile.exists():
            themeconfig = configparser.ConfigParser()
            themeconfig.read(str(themefile))
            custom_theme_name = LeafSettings.CUSTOM_THEME.value
            if custom_theme_name is not None and custom_theme_name in themeconfig:
                # Apply custom theme
                self.theme.update(themeconfig[custom_theme_name])
            elif "DEFAULT" in themeconfig:
                # Apply default theme
                self.theme.update(themeconfig["DEFAULT"])
        self._create_themes()

    def _decorate(self, style_key, text):
        """
        Encapsulate text in appropriate ansi chars (if in tty and lib is available)
        """
        combined_themes = self._tostring(style_key)
        if len(combined_themes) > 0:
            return combined_themes + text + ANSI.style.RESET_ALL
        return text

    def _tostring(self, style_key):
        """
        Convert theme to a string
        """
        combined_themes = ""
        style_key = style_key.lower()
        if style_key in self.theme:
            # Get the value of the property of the theme
            element_value = self.theme[style_key]
            for style in element_value.split("+"):
                style = style.strip()  # remove left and right spaces
                if style in THEME_GRAMAR:
                    # Translate it to code using grammar dict
                    theme_provider = THEME_GRAMAR[style]
                    combined_themes += theme_provider()
        return combined_themes

    def colorize_tag(self, text):
        """
        Encapsulate tag in appropriate ansi chars (if in tty and lib is available)
        """
        return self._decorate("tag." + text, text)

    def _create_themes(self):
        # Special instances
        self.RESET = _Theme(self, "reset")  # Used to end a theme

        # Error messages
        self.ERROR = _Theme(self, "error")  # Used for the syserr wrapper
        self.ERROR_TITLE = _Theme(self, "error_title")
        self.ERROR_MESSAGE = _Theme(self, "error_message")
        self.HINTS = _Theme(self, "hints")  # Used for hints
        self.HINTS_COMMANDS = _Theme(self, "hints_commands")  # Used for commands in hints

        # Tables
        self.LABEL = _Theme(self, "label")
        self.TABLE_SEPARATOR = _Theme(self, "table_separator")

        # Remote
        self.REMOTE_DISABLED = _Theme(self, "remote_disabled")

        # Profile
        self.PROFILE_CURRENT = _Theme(self, "profile_current")

        # Question
        self.QUESTION = _Theme(self, "question")
