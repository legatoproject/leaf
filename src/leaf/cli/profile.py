'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from leaf.cli.cliutils import LeafCommand, initCommonArgs, LeafMetaCommand
from leaf.core.coreutils import retrievePackageIdentifier


class ProfileMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(
            self,
            "profile",
            "command to manage profiles")

    def getDefaultSubCommand(self):
        return ProfileListCommand()

    def getSubCommands(self):
        return [ProfileCreateCommand(),
                ProfileRenameCommand(),
                ProfileDeleteCommand(),
                ProfileSwitchCommand(),
                ProfileSyncCommand(),
                ProfileConfigCommand()]


class AbstractProfileCommand(LeafCommand):
    def __init__(self, name, description, profileRequired=None):
        LeafCommand.__init__(self, name, description)
        self.profileRequired = profileRequired

    def getProfileName(self, args, defaultProvider=None):
        out = None
        if hasattr(args, 'profiles'):
            if self.profileRequired == True:
                out = args.profiles[0]
            elif self.profileRequired == False:
                out = args.profiles

        if out is None and defaultProvider is not None:
            out = defaultProvider()
        return out

    def initArgs(self, parser):
        super().initArgs(parser)
        if self.profileRequired == False:
            parser.add_argument('profiles', nargs=argparse.OPTIONAL,
                                metavar='PROFILE', help='the profile name')
        elif self.profileRequired == True:
            parser.add_argument('profiles', nargs=1,
                                metavar='PROFILE', help='the profile name')


class ProfileListCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "list",
            "list profiles",
            profileRequired=False)

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)
        name = self.getProfileName(args)
        if name is None:
            for profile in workspace.listProfiles().values():
                logger.displayItem(profile)
        else:
            logger.displayItem(workspace.getProfile(name))


class ProfileCreateCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "create",
            "create a profile",
            profileRequired=True)

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)
        profile = workspace.createProfile(self.getProfileName(args))
        workspace.switchProfile(profile)
        logger.printDefault("Profile %s created" % profile.name)


class ProfileRenameCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "rename",
            "rename current profile",
            profileRequired=None)

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('profiles', nargs=1,
                            metavar='NEWNAME', help='the new profile name')

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)

        oldName = workspace.getCurrentProfileName()
        profile = workspace.renameProfile(oldName, args.profiles[0])
        logger.printDefault("Profile %s renamed to %s" %
                            (oldName, profile.name))


class ProfileDeleteCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "delete",
            "delete profile",
            profileRequired=False)

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)
        pfname = self.getProfileName(args, workspace.getCurrentProfileName)
        workspace.deleteProfile(pfname)
        logger.printDefault("Profile %s deleted" % pfname)


class ProfileSwitchCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "switch",
            "set current profile",
            profileRequired=True)

    def execute(self, args):
        logger = self.getLogger(args)
        workspace = self.getWorkspace(args)
        profile = workspace.getProfile(self.getProfileName(args))
        workspace.switchProfile(profile)
        logger.printVerbose("Profile package folder:", profile.folder)


class ProfileSyncCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "sync",
            "install packages needed for current or given profile",
            profileRequired=False)

    def execute(self, args):
        workspace = self.getWorkspace(args)
        pfname = self.getProfileName(args, workspace.getCurrentProfileName)
        profile = workspace.getProfile(pfname)
        workspace.provisionProfile(profile)


class ProfileConfigCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "config",
            "configure profile to add and remove packages",
            profileRequired=False)

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       addRemovePackages=True)

    def execute(self, args):
        packageManager = self.getPackageManager(args)
        workspace = self.getWorkspace(args)

        pfname = self.getProfileName(args, workspace.getCurrentProfileName)
        profile = workspace.getProfile(pfname)

        if args.pkgAddList is not None:
            validPiList = list(packageManager.listAvailablePackages().keys()) + \
                list(packageManager.listInstalledPackages().keys())
            profile.addPackages([retrievePackageIdentifier(
                motif, validPiList) for motif in args.pkgAddList])
        if args.pkgRmList is not None:
            validPiList = profile.getPackagesMap().values()
            profile.removePackages([retrievePackageIdentifier(
                motif, validPiList) for motif in args.pkgRmList])

        workspace.updateProfile(profile)
