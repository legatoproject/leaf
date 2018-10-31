'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand, initCommonArgs, LeafMetaCommand
from leaf.core.coreutils import retrievePackageIdentifier
from leaf.format.renderer.profile import ProfileListRenderer


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
    def __init__(self, name, description, profileNargs=None):
        LeafCommand.__init__(self, name, description)
        self.profileNargs = profileNargs

    def getProfileName(self, args, defaultProvider=None):
        if hasattr(args, 'profiles'):
            if isinstance(args.profiles, list):
                if len(args.profiles) == 1:
                    return args.profiles[0]
            elif isinstance(args.profiles, str):
                return args.profiles

        if defaultProvider is not None:
            return defaultProvider()

    def initArgs(self, parser):
        super().initArgs(parser)
        if self.profileNargs is not None:
            parser.add_argument('profiles',
                                nargs=self.profileNargs,
                                metavar='PROFILE',
                                help='the profile name')


class ProfileListCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "list",
            "list profiles",
            profileNargs='*')

    def execute(self, args):
        wm = self.getWorkspaceManager(args)
        name = self.getProfileName(args)
        profileList = []
        if 'profiles' in vars(args) and len(args.profiles) > 0:
            for name in args.profiles:
                profileList.append(wm.getProfile(name))
        else:
            profileList.extend(wm.listProfiles().values())

        profilesInfoMap = dict([(p, computeProfileInfo(wm, p))
                                for p in profileList])
        rend = ProfileListRenderer(
            workspaceRootFolder=wm.workspaceRootFolder,
            profilesInfoMap=profilesInfoMap)
        wm.printRenderer(rend)


def computeProfileInfo(workspaceManager, profile):
    # Sync
    sync = workspaceManager.isProfileSync(profile)

    # Included Packages
    pi2pMap = workspaceManager.listInstalledPackages()
    includedPackIds = set(profile.getPackagesMap().values())
    ipMap = dict([(pi, pi2pMap.get(pi, None))
                  for pi in includedPackIds])

    # Dependencies
    if sync:
        depPacks = workspaceManager.getProfileDependencies(profile)
        depsMap = dict([(p.getIdentifier(), p) for p in depPacks])
        for ipId in includedPackIds:
            depsMap.pop(ipId, None)
    else:
        depsMap = {}

    return {"sync": sync,
            "includedPackagesMap": ipMap,
            "dependenciesMap": depsMap}


class ProfileCreateCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "create",
            "create a profile",
            profileNargs=1)

    def execute(self, args):
        wm = self.getWorkspaceManager(args)

        profile = wm.createProfile(self.getProfileName(args))
        wm.switchProfile(profile)
        wm.logger.printDefault("Profile %s created" % profile.name)


class ProfileRenameCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "rename",
            "rename current profile",
            profileNargs=None)

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('profiles',
                            nargs=1,
                            metavar='NEWNAME',
                            help='the new profile name')

    def execute(self, args):
        wm = self.getWorkspaceManager(args)

        oldName = wm.getCurrentProfileName()
        profile = wm.renameProfile(oldName, args.profiles[0])
        wm.logger.printDefault("Profile %s renamed to %s" %
                               (oldName, profile.name))


class ProfileDeleteCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "delete",
            "delete profile(s)",
            profileNargs='*')

    def execute(self, args):
        wm = self.getWorkspaceManager(args)

        if len(args.profiles) > 0:
            for pfname in args.profiles:
                wm.deleteProfile(pfname)
                wm.logger.printDefault("Profile %s deleted" % pfname)
        else:
            pfname = wm.getCurrentProfileName()
            wm.deleteProfile(pfname)
            wm.logger.printDefault("Profile %s deleted" % pfname)


class ProfileSwitchCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "switch",
            "set current profile",
            profileNargs=1)

    def execute(self, args):
        wm = self.getWorkspaceManager(args)

        profile = wm.getProfile(self.getProfileName(args))
        wm.switchProfile(profile)
        wm.logger.printVerbose("Profile package folder:", profile.folder)


class ProfileSyncCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "sync",
            "install packages needed for current or given profile",
            profileNargs='?')

    def execute(self, args):
        wm = self.getWorkspaceManager(args)

        pfname = self.getProfileName(args, wm.getCurrentProfileName)
        profile = wm.getProfile(pfname)
        wm.provisionProfile(profile)


class ProfileConfigCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            "config",
            "configure profile to add and remove packages",
            profileNargs='?')

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       addRemovePackages=True)

    def execute(self, args):
        wm = self.getWorkspaceManager(args)

        pfname = self.getProfileName(args, wm.getCurrentProfileName)
        profile = wm.getProfile(pfname)

        if args.pkgAddList is not None:
            validPiList = list(wm.listAvailablePackages().keys()) + \
                list(wm.listInstalledPackages().keys())
            profile.addPackages([retrievePackageIdentifier(
                motif, validPiList) for motif in args.pkgAddList])
        if args.pkgRmList is not None:
            validPiList = profile.getPackagesMap().values()
            profile.removePackages([retrievePackageIdentifier(
                motif, validPiList) for motif in args.pkgRmList])

        wm.updateProfile(profile)
