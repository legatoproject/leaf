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
from leaf.model.config import WorkspaceConfiguration
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
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
            return Path(LeafSettings.WORKSPACE.value)

        # Check parents using PWD to respect symlinks
        if check_parents and LeafSettings.PWD.as_boolean():
            current_folder = Path(LeafSettings.PWD.value)
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

    def build_ws_environment(self) -> Environment:
        out = self.read_ws_configuration().build_environment()
        out.set_variable(LeafSettings.WORKSPACE.key, str(self.ws_root_folder), replace=True, prepend=True)
        return out

    def update_ws_environment(self, set_map=None, unset_list=None):
        wsc = self.read_ws_configuration()
        wsc.update_environment(set_map, unset_list)
        self.write_ws_configuration(wsc)

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

    def get_profile(self, name: str) -> Profile:
        if name is None:
            raise LeafException("Cannot find profile")
        pfmap = self.list_profiles()
        if name not in pfmap:
            raise InvalidProfileNameException(name)
        return pfmap[name]

    def create_profile(self, name: str) -> Profile:
        name = Profile.check_valid_name(name)
        wsc = self.read_ws_configuration()
        if name in wsc.profiles:
            raise ProfileNameAlreadyExistException(name)
        wsc.profiles[name] = {}
        self.write_ws_configuration(wsc)
        return self.get_profile(name)

    def rename_profile(self, old_name: str, new_name: str) -> Profile:
        new_name = Profile.check_valid_name(new_name)

        # Delete data folder
        old_pf = self.get_profile(old_name)
        if old_pf.is_current:
            self.update_current_link(None)

        wsc = self.read_ws_configuration()
        if old_name not in wsc.profiles:
            raise InvalidProfileNameException(old_name)
        if new_name in wsc.profiles:
            raise ProfileNameAlreadyExistException(new_name)
        wsc.profiles[new_name] = wsc.profiles[old_name]
        del wsc.profiles[old_name]
        self.write_ws_configuration(wsc)

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
        wsc = self.read_ws_configuration()
        if profile.name not in wsc.profiles:
            raise LeafException("Cannot update profile {pf.name}".format(pf=profile))
        wsc.profiles[profile.name] = profile.json
        self.write_ws_configuration(wsc)

    def delete_profile(self, name: str):
        # Clean files
        profile = self.get_profile(name)
        if profile.folder.exists():
            shutil.rmtree(str(profile.folder))
        if profile.is_current:
            self.update_current_link(None)
        # Update configuration
        wsc = self.read_ws_configuration()
        del wsc.profiles[name]
        self.write_ws_configuration(wsc)

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
        out.append(self.build_packages_environment(self.get_profile_dependencies(profile)))
        return out

    def build_pf_environment(self, profile: Profile):
        return Environment.build(self.build_builtin_environment(), self.build_user_environment(), self.build_ws_environment(), profile.build_environment())

    def get_profile_dependencies(self, profile):
        """
        Returns all latest packages needed by a profile
        """
        return DependencyUtils.installed(
            PackageIdentifier.parse_list(profile.packages), self.list_installed_packages(), only_keep_latest=True, env=self.build_pf_environment(profile)
        )
