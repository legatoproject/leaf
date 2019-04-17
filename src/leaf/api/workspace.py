"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import os
import shutil
from builtins import Exception, property
from collections import OrderedDict
from pathlib import Path

from leaf.api.packages import PackageManager
from leaf.core.constants import LeafFiles, LeafSettings
from leaf.core.error import (
    InvalidProfileNameException,
    LeafException,
    NoProfileSelected,
    ProfileNameAlreadyExistException,
    ProfileOutOfSyncException,
    ProfileProvisioningException,
    WorkspaceNotInitializedException,
)
from leaf.core.logger import print_trace
from leaf.core.utils import mkdirs
from leaf.model.base import Scope
from leaf.model.config import ConfigContextManager, WorkspaceConfiguration
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.model.settings import ScopeSetting
from leaf.model.workspace import Profile


class WorkspaceManager(PackageManager):

    """
    Represent a workspace, where leaf profiles apply
    """

    @staticmethod
    def is_workspace_root(folder):
        return folder is not None and (folder / LeafFiles.WS_CONFIG_FILENAME).is_file()

    @staticmethod
    def find_root(check_parents=True):
        # Check env if no custom path given
        if LeafSettings.WORKSPACE.as_boolean():
            return LeafSettings.WORKSPACE.as_path()

        # Check parents using PWD to respect symlinks
        if check_parents and LeafSettings.PWD.as_boolean():
            current_folder = LeafSettings.PWD.as_path()
            if WorkspaceManager.is_workspace_root(current_folder):
                return current_folder
            else:
                for parent in current_folder.parents:
                    if WorkspaceManager.is_workspace_root(parent):
                        return parent

        # Use process current directory
        return Path(os.getcwd())

    def __init__(self, ws_root_folder: Path):
        PackageManager.__init__(self)
        self.__ws_root = ws_root_folder

    @property
    def ws_root_folder(self):
        return self.__ws_root

    @property
    def ws_config_file(self):
        return self.__ws_root / LeafFiles.WS_CONFIG_FILENAME

    @property
    def ws_data_folder(self):
        return mkdirs(self.__ws_root / LeafFiles.WS_DATA_FOLDERNAME)

    @property
    def ws_current_link(self):
        return self.ws_data_folder / LeafFiles.CURRENT_PROFILE_LINKNAME

    @property
    def is_initialized(self):
        return WorkspaceManager.is_workspace_root(self.ws_root_folder)

    def init_ws(self):
        if self.is_initialized:
            raise LeafException("Workspace is already initialized")
        self.write_ws_configuration(WorkspaceConfiguration())

    def read_ws_configuration(self, init_if_needed: bool = False) -> WorkspaceConfiguration:
        """
        Return the configuration and if current leaf version is supported
        """
        if not self.is_initialized:
            if not init_if_needed:
                raise WorkspaceNotInitializedException()
            self.init_ws()
        return WorkspaceConfiguration(self.ws_config_file)

    def write_ws_configuration(self, wsc: WorkspaceConfiguration):
        """
        Write the configuration and set the min leaf version to current version
        """
        tmpfile = self.ws_data_folder / ("tmp-" + LeafFiles.WS_CONFIG_FILENAME)
        wsc.write_layer(tmpfile, pp=True)
        tmpfile.rename(self.ws_config_file)

    def open_ws_configuration(self):
        return ConfigContextManager(self.read_ws_configuration, self.write_ws_configuration)

    def build_ws_environment(self) -> Environment:
        out = self.read_ws_configuration().build_environment()
        out.set_variable(LeafSettings.WORKSPACE.key, str(self.ws_root_folder), replace=True, prepend=True)
        return out

    def update_ws_environment(self, set_map=None, unset_list=None):
        with self.open_ws_configuration() as config:
            config.update_environment(set_map, unset_list)

    def list_profiles(self) -> dict:
        """
        Return a map(name/profile) of all profiles
        """
        wsc = self.read_ws_configuration()
        out = OrderedDict()
        for name, json in wsc.profiles.items():
            out[name] = Profile(name, self.ws_data_folder / name, json)
        # Try to find current profile
        try:
            out[self.current_profile_name].is_current = True
        except Exception:
            pass
        return out

    def get_current_profile(self, name: str) -> Profile:
        return self.get_profile(self.current_profile_name)

    def get_profile(self, name: str) -> Profile:
        if name is None:
            raise LeafException("Cannot find profile")
        pfmap = self.list_profiles()
        if name not in pfmap:
            raise InvalidProfileNameException(name)
        return pfmap[name]

    def create_profile(self, name: str) -> Profile:
        name = Profile.check_valid_name(name)
        with self.open_ws_configuration() as wsc:
            if name in wsc.profiles:
                raise ProfileNameAlreadyExistException(name)
            wsc.profiles[name] = {}
        return self.get_profile(name)

    def rename_profile(self, old_name: str, new_name: str) -> Profile:
        new_name = Profile.check_valid_name(new_name)

        # Delete data folder
        old_pf = self.get_profile(old_name)
        if old_pf.is_current:
            self.update_current_link(None)

        with self.open_ws_configuration() as wsc:
            if old_name not in wsc.profiles:
                raise InvalidProfileNameException(old_name)
            if new_name in wsc.profiles:
                raise ProfileNameAlreadyExistException(new_name)
            wsc.profiles[new_name] = wsc.profiles[old_name]
            del wsc.profiles[old_name]

        new_pf = self.get_profile(new_name)
        # Rename old folder
        if new_pf.folder.exists():
            shutil.rmtree(str(new_pf.folder))
        if old_pf.folder.exists():
            old_pf.folder.rename(new_pf.folder)
        # Update current link
        if old_pf.is_current:
            self.switch_profile(new_pf)
        return new_pf

    def update_profile(self, profile: Profile):
        with self.open_ws_configuration() as wsc:
            if profile.name not in wsc.profiles:
                raise LeafException("Cannot update profile {pf.name}".format(pf=profile))
            wsc.profiles[profile.name] = profile.json

    def delete_profile(self, name: str):
        # Clean files
        profile = self.get_profile(name)
        if profile.folder.exists():
            shutil.rmtree(str(profile.folder))
        if profile.is_current:
            self.update_current_link(None)
        # Update configuration
        with self.open_ws_configuration() as wsc:
            del wsc.profiles[name]

    def switch_profile(self, profile: Profile):
        # Check folder exist
        mkdirs(profile.folder)
        # Update symlink
        self.update_current_link(profile.name)
        self.logger.print_default("Current profile is now {pf.name}".format(pf=profile))

    def is_profile_sync(self, profile: Profile, raise_if_not_sync=False):
        """
        Check if a profile contains all needed links to all contained packages
        """
        try:
            linked_pi_list = [ip.identifier for ip in profile.list_linked_packages()]
            needed_pi_list = [ip.identifier for ip in self.get_profile_dependencies(profile)]
            for pi in needed_pi_list:
                if pi not in linked_pi_list:
                    raise LeafException("Missing package link for {pi}".format(pi=pi))
            for pi in linked_pi_list:
                if pi not in needed_pi_list:
                    raise LeafException("Package should not be linked: {pi}".format(pi=pi))
        except Exception as e:
            if raise_if_not_sync:
                raise ProfileOutOfSyncException(profile, cause=e)
            self.logger.print_verbose(str(e))
            return False
        return True

    @property
    def current_profile_name(self):
        if self.ws_current_link.is_symlink():
            try:
                return self.ws_current_link.resolve().name
            except Exception:
                self.ws_current_link.unlink()
                raise NoProfileSelected()
        else:
            raise NoProfileSelected()

    def update_current_link(self, name: str):
        """
        Update the current link without any check
        """
        lnk = self.ws_current_link
        if lnk.is_symlink():
            lnk.unlink()
        if name is not None:
            lnk.symlink_to(name)
            self.ws_config_file.touch(exist_ok=True)

    def provision_profile(self, profile):
        if not profile.folder.is_dir():
            # Create folder if needed
            profile.folder.mkdir(parents=True)
        else:
            # Clean folder content
            for item in profile.folder.glob("*"):
                if item.is_symlink():
                    item.unlink()
                else:
                    shutil.rmtree(str(item))

        # Check if all needed packages are installed
        missing_packages = DependencyUtils.install(
            PackageIdentifier.parse_list(profile.packages),
            self.list_available_packages(),
            self.list_installed_packages(),
            env=self.build_pf_environment(profile),
        )
        if len(missing_packages) == 0:
            self.logger.print_verbose("All packages are already installed")
        else:
            self.logger.print_default("Profile is out of sync")
            try:
                self.install_packages(PackageIdentifier.parse_list(profile.packages), env=self.build_pf_environment(profile))
            except Exception as e:
                raise ProfileProvisioningException(e)

        # Do all needed links
        errors = 0
        for ip in self.get_profile_dependencies(profile):
            pi_folder = profile.folder / ip.identifier.name
            if pi_folder.exists():
                pi_folder = profile.folder / str(ip.identifier)
            try:
                env = self.build_pf_environment(profile)
                self.sync_packages([ip.identifier], env=env)
                pi_folder.symlink_to(ip.folder)
            except Exception as e:
                errors += 1
                self.logger.print_error("Error while sync operation on {ip.identifier}".format(ip=ip))
                self.logger.print_error(str(e))
                print_trace()

        # Touch folder when provisionning is done without error
        if errors == 0:
            profile.folder.touch(exist_ok=True)

    def build_full_environment(self, profile: Profile):
        self.is_profile_sync(profile, raise_if_not_sync=True)
        out = self.build_pf_environment(profile)
        ipmap = self.list_installed_packages(alt_user_root_folder=None if LeafSettings.PROFILE_NORELATIVE.as_boolean() else profile.folder)
        out.append(self.build_packages_environment(self.get_profile_dependencies(profile, ipmap=ipmap), ipmap=ipmap))
        return out

    def build_pf_environment(self, profile: Profile):
        return Environment.build(self.build_builtin_environment(), self.build_user_environment(), self.build_ws_environment(), profile.build_environment())

    def get_profile_dependencies(self, profile, ipmap=None):
        """
        Returns all latest packages needed by a profile
        """
        return DependencyUtils.installed(PackageIdentifier.parse_list(profile.packages), ipmap or self.list_installed_packages(), only_keep_latest=True, env=self.build_pf_environment(profile))

    def get_settings_value(self, *settings_id: str) -> dict:
        out = OrderedDict()
        for i in settings_id:
            out[i] = self.get_setting_value(i)
        return out

    def get_setting_value(self, setting_id: str, user_env=None, ws_env=None, pf_env=None) -> str:
        setting = self.get_setting(setting_id)

        # build env
        env = Environment()
        if Scope.USER in setting.scopes:
            env.append(user_env or self.build_user_environment())
        if self.is_initialized:
            if Scope.WORKSPACE in setting.scopes:
                env.append(ws_env or self.build_ws_environment())
            if Scope.PROFILE in setting.scopes:
                try:
                    env.append(pf_env or self.get_profile(self.current_profile_name).build_environment())
                except NoProfileSelected:
                    pass
        # Search the setting value
        return env.find_setting(setting)

    def unset_setting(self, setting_id: str):
        self.__unset_setting(self.get_setting(setting_id))

    def __unset_setting(self, setting: ScopeSetting):
        # Remove setting from user scope if needed
        if Scope.USER in setting.scopes:
            with self.open_user_configuration() as config:
                config.update_environment(unset_list=[setting.key])

        # Remove setting from workspace/profile scopes if ws initialized
        if self.is_initialized:
            if Scope.WORKSPACE in setting.scopes:
                with self.open_ws_configuration() as config:
                    config.update_environment(unset_list=[setting.key])
            if Scope.PROFILE in setting.scopes:
                try:
                    profile = self.get_profile(self.current_profile_name)
                    profile.update_environment(unset_list=[setting.key])
                    self.update_profile(profile)
                except NoProfileSelected:
                    pass

    def set_setting(self, setting_id: str, value: str, scope: Scope = None):
        # Retrieve setting
        setting = self.get_setting(setting_id)

        if value is None:
            # If value is None, unset setting
            self.__unset_setting(setting)
        else:
            # In case of enum, resolve value
            if not setting.is_valid(value):
                raise LeafException("Value for setting {id} must match '{validator}'".format(id=setting_id, validator=setting.is_valid))

            # If no scope specified, use setting only scope if it is unique
            if scope is None:
                if len(setting.scopes) == 1:
                    scope = setting.scopes[0]
                else:
                    raise LeafException("No scope specified to update setting {id}".format(id=setting_id))

            # Check taht the setting can be set in given scope
            if scope not in setting.scopes:
                raise LeafException("Cannot set '{id}' in scope {scope}".format(id=setting_id, scope=scope.name.lower()))

            # Set the setting in expected scope
            if scope == Scope.USER:
                with self.open_user_configuration() as config:
                    config.update_environment(set_map={setting.key: value})
            elif scope == Scope.WORKSPACE:
                with self.open_ws_configuration() as config:
                    config.update_environment(set_map={setting.key: value})
            elif scope == Scope.PROFILE:
                profile = self.get_profile(self.current_profile_name)
                profile.update_environment(set_map={setting.key: value})
                self.update_profile(profile)
            else:
                raise LeafException("Cannot update setting {id} in scope {scope}".format(id=setting.identifier, scope=scope))
