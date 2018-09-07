'''
Error management

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from builtins import Exception
import os
import sys
import traceback

from leaf.constants import EnvConstants


HINTS_CMD_DELIMITER = '\''


def printTrace():
    if EnvConstants.DEBUG_MODE in os.environ and sys.exc_info()[0] is not None:
        traceback.print_exc(file=sys.stderr)


class LeafException(Exception):
    '''
    Base class for exceptions in leaf app
    '''

    def __init__(self, msg=None, cause=None):
        '''
        Constructor
        '''
        Exception.__init__(self, msg)
        self.msg = msg
        self.cause = cause
        self.hints = []


class UserCancelException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "Operation canceled by user")


class NoRemoteException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No remote defined")
        self.hints.append("try 'leaf remote add' to add some")


class NoEnabledRemoteException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "All remotes are disabled")
        self.hints.append(
            "try 'leaf remote list' then 'leaf remote enable XXX' to enable some")


class NoPackagesInCacheException(LeafException):
    def __init__(self):
        LeafException.__init__(self, "No package in cache")
        self.hints.append(
            "try 'leaf remote fetch' to trigger packages information refresh")


class BadRemoteUrlException(LeafException):
    def __init__(self, remote, cause=None):
        LeafException.__init__(
            self, "Can't reach remote {0}".format(remote.alias), cause)
        self.hints.append("please check your network connection,")
        self.hints.append("or check the remote URL in 'leaf remote list',")
        self.hints.append(
            "or you can disable the remote with 'leaf remote disable {0}'".format(remote.alias))


class PackageInstallInterruptedException(LeafException):
    def __init__(self, packages, cause=None):
        LeafException.__init__(self, "Package install interrupted", cause)
        self.hints.append(
            "try 'leaf package install {0}' to resume".format(' '.join(packages)))


class ProfileProvisioningException(LeafException):
    def __init__(self, cause=None):
        LeafException.__init__(self, "Profile provisioning interrupted", cause)
        self.hints.append("try 'leaf profile sync' to resume")


class InvalidPackageNameException(LeafException):
    def __init__(self, unknownName):
        LeafException.__init__(self, "Unknown package {0}".format(unknownName))
        self.hints.append("check available packages with 'leaf search'")


class InvalidProfileNameException(LeafException):
    def __init__(self, unknownName):
        LeafException.__init__(self, "Unknown profile {0}".format(unknownName))
        self.hints.append("check available profiles with 'leaf profile list'")


class ProfileNameAlreadyExistException(LeafException):
    def __init__(self, unknownName):
        LeafException.__init__(
            self, "Profile name {0} already exists in current workspace".format(unknownName))
        self.hints.append(
            "try 'leaf select {0} && leaf update -p xxx' if you want to update profile {0} with package xxx".format(unknownName))
        self.hints.append(
            "try 'leaf setup -p xxx {0}_1' if you want to create a new profile with package xxx".format(unknownName))
