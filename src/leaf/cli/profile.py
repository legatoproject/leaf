'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafCommand, initCommonArgs
from leaf.core.coreutils import findLatestVersion
from leaf.format.renderer.profile import ProfileListRenderer
from leaf.model.package import PackageIdentifier


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

    def _configureParser(self, parser):
        super()._configureParser(parser)
        if self.profileNargs is not None:
            parser.add_argument('profiles',
                                nargs=self.profileNargs,
                                metavar='PROFILE',
                                help='the profile name')


class ProfileListCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            'list',
            "list profiles",
            profileNargs='*')

    def execute(self, args, uargs):
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
    ipMap = dict([(pi, pi2pMap.get(pi, None)) for pi in includedPackIds])

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
            'create',
            "create a profile",
            profileNargs=1)

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args)

        profile = wm.createProfile(self.getProfileName(args))
        wm.switchProfile(profile)
        wm.logger.printDefault("Profile %s created" % profile.name)


class ProfileRenameCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            'rename',
            "rename current profile",
            profileNargs=None)

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('profiles',
                            nargs=1,
                            metavar='NEWNAME',
                            help='the new profile name')

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args)

        oldName = wm.getCurrentProfileName()
        profile = wm.renameProfile(oldName, args.profiles[0])
        wm.logger.printDefault("Profile %s renamed to %s" %
                               (oldName, profile.name))


class ProfileDeleteCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            'delete',
            "delete profile(s)",
            profileNargs='*')

    def execute(self, args, uargs):
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
            'switch',
            "set current profile",
            profileNargs=1)

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args)

        profile = wm.getProfile(self.getProfileName(args))
        wm.switchProfile(profile)
        wm.logger.printVerbose("Profile package folder:", profile.folder)


class ProfileSyncCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            'sync',
            "install packages needed for current or given profile",
            profileNargs='?')

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args)

        pfname = self.getProfileName(args, wm.getCurrentProfileName)
        profile = wm.getProfile(pfname)
        wm.provisionProfile(profile)


class ProfileConfigCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(
            self,
            'config',
            "configure profile to add and remove packages",
            profileNargs='?')

    def _configureParser(self, parser):
        super()._configureParser(parser)
        initCommonArgs(parser,
                       addRemovePackages=True)

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(args)

        pfname = self.getProfileName(args, wm.getCurrentProfileName)
        profile = wm.getProfile(pfname)

        if args.pkgAddList is not None:
            validPiList = list(wm.listAvailablePackages().keys()) + \
                list(wm.listInstalledPackages().keys())
            piList = []
            for motif in args.pkgAddList:
                if PackageIdentifier.isValidIdentifier(motif):
                    piList.append(PackageIdentifier.fromString(motif))
                else:
                    piList.append(findLatestVersion(motif, validPiList))
            profile.addPackages(piList)
        if args.pkgRmList is not None:
            validPiList = profile.getPackagesMap().values()
            piList = []
            for motif in args.pkgRmList:
                if PackageIdentifier.isValidIdentifier(motif):
                    piList.append(PackageIdentifier.fromString(motif))
                else:
                    piList.append(findLatestVersion(motif, validPiList))
            profile.removePackages(piList)

        wm.updateProfile(profile)
