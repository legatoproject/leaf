"""
Error management

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from builtins import Exception
from pathlib import Path

from leaf.core.settings import LeafSetting
from leaf.rendering.formatutils import sizeof_fmt

HINTS_CMD_DELIMITER = "'"


class LeafException(Exception):

    """
    Base class for exceptions in leaf app
    """

    def __init__(self, message: str = None, cause: Exception = None, hints=None, exitcode: int = 2):
        """
        Constructor
        """
        Exception.__init__(self, message)
        self.__message = message
        self.__cause = cause
        self.__hints = []
        self.__exitcode = exitcode
        if isinstance(hints, str):
            self.__hints.append(hints)
        elif hints is not None:
            self.__hints += hints

    @property
    def exit_code(self):
        return self.__exitcode

    @property
    def message(self):
        return self.__message

    @property
    def hints(self):
        return self.__hints

    @property
    def cause(self):
        return self.__cause

    def get_hints(self):
        out = []
        if isinstance(self.cause, LeafException):
            out += self.cause.get_hints()
        out += self.__hints
        return out


class UserCancelException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "Operation canceled by user")


class NoRemoteException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No remote defined", hints=["try 'leaf remote add' to add some", "see 'leaf help remote' for some documentation"])


class NoEnabledRemoteException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "All remotes are disabled", hints="try 'leaf remote list' then 'leaf remote enable XXX' to enable some")


class NoPackagesInCacheException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No package in cache", hints="try 'leaf remote fetch' to trigger packages information refresh")


class RemoteFetchException(LeafException):
    def __init__(self, remote, cause=None):
        LeafException.__init__(
            self,
            "Can't fetch remote {0}".format(remote.alias),
            cause=cause,
            hints=[
                "please check your network connection,",
                "or check the remote URL in 'leaf remote list',",
                "or you can disable the remote with 'leaf remote disable {0}'".format(remote.alias),
            ],
        )


class PackageInstallInterruptedException(LeafException):
    def __init__(self, packages, cause=None):
        LeafException.__init__(self, "Package install interrupted", cause=cause, hints="try 'leaf package install {0}' to resume".format(" ".join(packages)))


class WorkspaceNotInitializedException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "Worskpace not initialized", hints="You can initialize a workspace with 'leaf init")


class ProfileProvisioningException(LeafException):
    def __init__(self, cause=None):
        LeafException.__init__(self, "Profile provisioning interrupted", cause=cause, hints="try 'leaf profile sync' to resume")


class ProfileOutOfSyncException(LeafException):
    def __init__(self, pf, cause=None):
        LeafException.__init__(
            self, "Profile {pf.name} is not sync".format(pf=pf), cause=cause, hints="try 'leaf profile sync {pf.name}' to synchronise it".format(pf=pf)
        )


class InvalidPackageNameException(LeafException):
    def __init__(self, pkgname):
        LeafException.__init__(self, "Unknown package {0}".format(pkgname), hints="check available packages with 'leaf search'")


class InvalidProfileNameException(LeafException):
    def __init__(self, pkgname):
        LeafException.__init__(self, "Unknown profile {0}".format(pkgname), hints="check available profiles with 'leaf profile list'")


class ProfileNameAlreadyExistException(LeafException):
    def __init__(self, pkgname):
        LeafException.__init__(
            self,
            "Profile name {0} already exists in current workspace".format(pkgname),
            hints=[
                "try 'leaf select {0} && leaf update -p xxx' if you want to update profile {0} with package xxx".format(pkgname),
                "try 'leaf setup -p xxx {0}_1' if you want to create a new profile with package xxx".format(pkgname),
            ],
        )


class NoProfileSelected(LeafException):
    def __init__(self):
        LeafException.__init__(
            self, "No current profile, you need to select to a profile first", hints="try 'leaf select xxx' if you want to select profile xxx"
        )


class InvalidHashException(LeafException):
    def __init__(self, file, actual, expected):
        LeafException.__init__(
            self,
            "The file {file} hash could not be verified, expecting {expected} but was {actual}".format(file=file, expected=expected, actual=actual),
            hints="try to download the file again, or contact the package owner",
        )


class LockException(LeafException):
    def __init__(self, lockfile):
        LeafException.__init__(self, "leaf is already running another operation (lock: {file})".format(file=lockfile))


class LeafOutOfDateException(LeafException):
    def __init__(self, message):
        LeafException.__init__(self, message, hints="You may want to update leaf with 'sudo apt-get install --only-upgrade leaf'")


class UnknownArgsException(LeafException):
    def __init__(self, uargs):
        LeafException.__init__(self, "Unknown arguments {uargs}".format(uargs=" ".join(uargs)))


class NotEnoughSpaceException(LeafException):
    def __init__(self, folder: Path, freespace: int, neededspace: int):
        LeafException.__init__(self, "Not enough space in folder {folder}, missing {size}".format(folder=folder, size=sizeof_fmt(neededspace - freespace)))


class InvalidSettingException(LeafException):
    def __init__(self, setting: LeafSetting, bad_value: str):
        LeafException.__init__(
            self,
            'Invalid value for setting {setting.identifier}: "{value}"'.format(setting=setting, value=bad_value),
            hints="You can reset the setting with 'leaf config reset {setting.identifier}'".format(setting=setting),
        )
