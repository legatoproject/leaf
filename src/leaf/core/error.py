'''
Error management

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import os
import sys
import traceback
from builtins import Exception

from leaf.constants import EnvConstants


HINTS_CMD_DELIMITER = '\''


def printTrace():
    if EnvConstants.DEBUG_MODE in os.environ and sys.exc_info()[0] is not None:
        traceback.print_exc(file=sys.stderr)


class LeafException(Exception):
    '''
    Base class for exceptions in leaf app
    '''

    def __init__(self, msg=None, cause=None, hints=None, exitCode=2):
        '''
        Constructor
        '''
        Exception.__init__(self, msg)
        self.msg = msg
        self.cause = cause
        self.hints = []
        self.exitCode = exitCode
        if isinstance(hints, str):
            self.hints.append(hints)
        elif hints is not None:
            self.hints += hints

    def getHints(self):
        out = []
        if isinstance(self.cause, LeafException):
            out += self.cause.getHints()
        out += self.hints
        return out


class UserCancelException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "Operation canceled by user")


class NoRemoteException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No remote defined",
                               hints="try 'leaf remote add' to add some")


class NoEnabledRemoteException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "All remotes are disabled",
                               hints="try 'leaf remote list' then 'leaf remote enable XXX' to enable some")


class NoPackagesInCacheException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No package in cache",
                               hints="try 'leaf remote fetch' to trigger packages information refresh")


class BadRemoteUrlException(LeafException):
    def __init__(self, remote, cause=None):
        LeafException.__init__(
            self, "Can't reach remote {0}".format(remote.alias),
            cause=cause,
            hints=["please check your network connection,",
                   "or check the remote URL in 'leaf remote list',",
                   "or you can disable the remote with 'leaf remote disable {0}'".format(remote.alias)])


class PackageInstallInterruptedException(LeafException):
    def __init__(self, packages, cause=None):
        LeafException.__init__(self, "Package install interrupted",
                               cause=cause,
                               hints="try 'leaf package install {0}' to resume".format(' '.join(packages)))


class ProfileProvisioningException(LeafException):
    def __init__(self, cause=None):
        LeafException.__init__(self, "Profile provisioning interrupted",
                               cause=cause,
                               hints="try 'leaf profile sync' to resume")


class InvalidPackageNameException(LeafException):
    def __init__(self, unknownName):
        LeafException.__init__(self, "Unknown package {0}".format(unknownName),
                               hints="check available packages with 'leaf search'")


class InvalidProfileNameException(LeafException):
    def __init__(self, unknownName):
        LeafException.__init__(self, "Unknown profile {0}".format(unknownName),
                               hints="check available profiles with 'leaf profile list'")


class ProfileNameAlreadyExistException(LeafException):
    def __init__(self, unknownName):
        LeafException.__init__(
            self, "Profile name {0} already exists in current workspace".format(
                unknownName),
            hints=[
                "try 'leaf select {0} && leaf update -p xxx' if you want to update profile {0} with package xxx".format(
                    unknownName),
                "try 'leaf setup -p xxx {0}_1' if you want to create a new profile with package xxx".format(unknownName)])


class NoProfileSelected(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No current profile, you need to select to a profile first",
                               hints="try 'leaf select xxx' if you want to select profile xxx")


class InvalidHashException(LeafException):
    def __init__(self, file, actual, expected):
        LeafException.__init__(
            self,
            "The file %s hash could not be verified, expecting %s but was %s" % (
                file, expected, actual),
            hints="try to download the file again, or contact the package owner")


class LockException(LeafException):
    def __init__(self, lockfile):
        LeafException.__init__(
            self,
            "leaf is already running another operation (lock: %s)" % lockfile)


class LeafOutOfDateException(LeafException):
    def __init__(self, message):
        LeafException.__init__(
            self,
            message,
            hints="You may want to update leaf with 'sudo apt-get install --only-upgrade leaf'")
