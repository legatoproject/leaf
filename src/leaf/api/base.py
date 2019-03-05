"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import platform
from pathlib import Path

from leaf import __version__
from leaf.core.constants import LeafFiles, LeafSettings
from leaf.core.error import LeafException, UserCancelException
from leaf.core.logger import TextLogger
from leaf.core.utils import mkdirs
from leaf.model.config import UserConfiguration
from leaf.model.environment import Environment
from leaf.rendering.renderer.error import HintsRenderer, LeafExceptionRenderer
from leaf.rendering.renderer.question import QuestionRenderer
from leaf.rendering.theme import ThemeManager


class ConfigurationManager:
    @property
    def configuration_folder(self):
        return mkdirs(Path(LeafSettings.CONFIG_FOLDER.value))

    @property
    def cache_folder(self):
        return mkdirs(Path(LeafSettings.CACHE_FOLDER.value))

    @property
    def configuration_file(self):
        return self.find_configuration_file(LeafFiles.CONFIG_FILENAME)

    def init_leaf_settings(self):
        userenvmap = self.read_user_configuration()._getenvmap()
        for s in LeafSettings.values():
            if s.key in userenvmap:
                s.value = userenvmap[s.key]

    def find_configuration_file(self, filename, check_exists=False):
        """
        Return the path of a configuration file.
        If check_exists arg is True and the file does not exists, returns None
        """
        out = self.configuration_folder / filename
        if check_exists and not out.exists():
            return None
        return out

    def read_user_configuration(self) -> UserConfiguration:
        """
        Read the configuration if it exists, else return the the default configuration
        """
        return UserConfiguration(LeafFiles.ETC_PREFIX / LeafFiles.CONFIG_FILENAME, self.configuration_file)

    def write_user_configuration(self, usrc: UserConfiguration):
        """
        Write the given configuration
        """
        usrc.write_layer(self.configuration_file, previous_layer=LeafFiles.ETC_PREFIX / LeafFiles.CONFIG_FILENAME, pp=True)

    def build_builtin_environment(self):
        out = Environment("Leaf built-in variables")
        out.set_variable("LEAF_VERSION", str(__version__))
        out.set_variable("LEAF_PLATFORM_SYSTEM", platform.system())
        out.set_variable("LEAF_PLATFORM_MACHINE", platform.machine())
        out.set_variable("LEAF_PLATFORM_RELEASE", platform.release())
        return out

    def build_user_environment(self):
        return self.read_user_configuration().build_environment()

    def update_user_environment(self, set_map=None, unset_list=None):
        usrc = self.read_user_configuration()
        usrc.update_environment(set_map, unset_list)
        self.write_user_configuration(usrc)


class LoggerManager(ConfigurationManager):
    def __init__(self):
        ConfigurationManager.__init__(self)
        # If the theme file does not exists, try to find a skeleton
        self.__tm = ThemeManager(self.find_configuration_file(LeafFiles.THEMES_FILENAME, check_exists=True) or LeafFiles.ETC_PREFIX / LeafFiles.THEMES_FILENAME)
        self.__logger = TextLogger()

    @property
    def logger(self):
        return self.__logger

    def print_hints(self, *hints):
        tr = HintsRenderer()
        tr.extend(hints)
        self.print_renderer(tr)

    def print_exception(self, ex):
        if isinstance(ex, LeafException):
            self.print_renderer(LeafExceptionRenderer(ex))
        else:
            self.logger.print_error(str(ex))

    def print_renderer(self, renderer, verbosity=None):
        renderer.verbosity = verbosity if verbosity is not None else self.__logger.verbosity
        renderer.tm = self.__tm
        renderer.print_renderer()

    def print_with_confirm(self, question="Do you want to continue?", raise_on_decline=False):
        out = None
        while out is None:
            self.print_renderer(QuestionRenderer(question + " (Y/n)"))
            if LeafSettings.NON_INTERACTIVE.as_boolean():
                out = True
            else:
                answer = input().strip()
                if answer == "" or answer.lower() == "y":
                    out = True
                elif answer.lower() == "n":
                    out = False
        if not out and raise_on_decline:
            raise UserCancelException()
        return out
