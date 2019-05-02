"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import operator
import os
import platform
from collections import OrderedDict
from pathlib import Path

from leaf import __version__
from leaf.core.constants import LeafFiles, LeafSettings
from leaf.core.error import LeafException, UserCancelException
from leaf.core.logger import TextLogger, print_trace
from leaf.core.utils import is_folder_ignored, mkdirs
from leaf.model.base import Scope
from leaf.model.config import ConfigContextManager, UserConfiguration
from leaf.model.environment import Environment
from leaf.model.modelutils import keep_latest
from leaf.model.package import InstalledPackage, ScopeSetting
from leaf.rendering.renderer.error import HintsRenderer, LeafExceptionRenderer
from leaf.rendering.renderer.question import QuestionRenderer
from leaf.rendering.theme import ThemeManager


class ConfigurationManager:
    @property
    def configuration_folder(self):
        return mkdirs(LeafSettings.CONFIG_FOLDER.as_path())

    @property
    def cache_folder(self):
        return mkdirs(LeafSettings.CACHE_FOLDER.as_path())

    @property
    def configuration_file(self):
        return self.find_configuration_file(LeafFiles.CONFIG_FILENAME)

    @property
    def install_folder(self):
        return mkdirs(LeafSettings.USER_PKG_FOLDER.as_path())

    def init_leaf_settings(self):
        userenvmap = self.read_user_configuration()._getenvmap()
        for s in LeafSettings.values():
            if s.key in userenvmap:
                try:
                    user_value = userenvmap[s.key]
                    s.value = user_value
                except ValueError:
                    print_trace("Invalid value in user scope for setting {s.identifier}: {s.key}={value}".format(s=s, value=user_value))

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

    def open_user_configuration(self):
        return ConfigContextManager(self.read_user_configuration, self.write_user_configuration)

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
        with self.open_user_configuration() as config:
            config.update_environment(set_map, unset_list)

    def _list_installed_packages(self, root_folder: Path, read_only: bool) -> dict:
        """
        Return all installed packages in given folder
        @return: PackageIdentifier/InstalledPackage dict
        """
        out = {}
        if root_folder is not None and root_folder.is_dir():
            for folder in root_folder.iterdir():
                # iterate over non ignored sub folders
                if folder.is_dir() and not is_folder_ignored(folder):
                    # test if a manifest exists
                    mffile = folder / LeafFiles.MANIFEST
                    if mffile.is_file():
                        try:
                            ip = InstalledPackage(mffile, read_only=read_only)
                            out[ip.identifier] = ip
                        except BaseException:
                            print_trace("Invalid manifest found: {mf}".format(mf=mffile))
        return out

    def list_installed_packages(self, only_latest=False, alt_user_root_folder: Path = None) -> dict:
        out = {}
        # Scan readonly system folder
        if LeafSettings.SYSTEM_PKG_FOLDERS.as_boolean():
            for system_root in LeafSettings.SYSTEM_PKG_FOLDERS.value.split(os.pathsep):
                out.update(self._list_installed_packages(Path(os.path.expanduser(system_root)), True))

        # Scan user root folder
        out.update(self._list_installed_packages(alt_user_root_folder or self.install_folder, False))

        # only keep latest if needed
        if only_latest:
            latest_pi_list = keep_latest(out.keys())
            out = {pi: ip for pi, ip in out.items() if pi in latest_pi_list}

        # sort dict by package identifier
        return OrderedDict(sorted(out.items(), key=operator.itemgetter(0)))

    def get_setting(self, setting_id: str) -> ScopeSetting:
        out = self.get_settings().get(setting_id)
        if out is None:
            raise LeafException("Unknown setting setting '{id}'".format(id=setting_id))
        return out

    def get_settings(self) -> dict:
        out = OrderedDict()

        # Leaf python settings
        for s in sorted(LeafSettings.values(), key=lambda s: s.identifier):
            out[s.identifier] = ScopeSetting(s.identifier, s.key, s.description, [Scope.USER], default=s.default, validator=s.is_valid)

        # Search settings in installed packages
        for ip in self.list_installed_packages(only_latest=True).values():
            for sid, setting in ip.settings.items():
                if sid not in out:
                    # Prevent setting shadowing
                    out[sid] = setting

        return out


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
        renderer = HintsRenderer()
        renderer.extend(hints)
        self.print_renderer(renderer)

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
