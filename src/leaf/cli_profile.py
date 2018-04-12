'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import abstractmethod
import argparse
from leaf.cli import LeafCli, LeafCommand
from leaf.core import Workspace
from leaf.coreutils import TagManager, genEnvScript
from leaf.filtering import AndPackageFilter, MasterPackageFilter, PkgNamePackageFilter, ModulePackageFilter,\
    KeywordPackageFilter
from leaf.model import PackageIdentifier, Manifest
from leaf.utils import envListToMap, findWorkspaceRoot
import os
from pathlib import Path


def main():
    return ProfileCli().run()


class ProfileCli (LeafCli):
    def __init__(self):
        LeafCli.__init__(self,
                         ListSubCommand(),
                         InitSubCommand(),
                         WorkspaceSubCommand(),
                         CreateSubCommand(),
                         UpdateSubCommand(),
                         UpgradeSubCommand(),
                         RenameSubCommand(),
                         DeleteSubCommand(),
                         SwitchSubCommand(),
                         SearchSubCommand(),
                         EnvSubCommand())
        self.parser.add_argument("-w", "--workspace",
                                 dest="workspace",
                                 type=Path,
                                 help="use given workspace")


class AbstractSubCommand(LeafCommand):
    def __init__(self, commandName, commandDescription, autoFindWorkspace=True, commandAlias=None):
        LeafCommand.__init__(self,
                             commandName,
                             commandDescription,
                             commandAlias=commandAlias)
        self.autoFindWorkspace = autoFindWorkspace

    def initArgs(self, subparser):
        LeafCommand.initArgs(self, subparser)

    @abstractmethod
    def internalExecute2(self, ws, app, logger, args):
        pass

    def internalExecute(self, app, logger, args):
        wspath = None
        if args.workspace is not None:
            wspath = args.workspace
        elif self.autoFindWorkspace:
            wspath = findWorkspaceRoot()
        else:
            wspath = Path(os.getcwd())
        ws = Workspace(wspath, app)
        return self.internalExecute2(ws, app, logger, args)

    @staticmethod
    def initCommonArgs(subparser, profileNargs=None, withPackages=True, withEnvvars=True):
        if profileNargs is not None:
            subparser.add_argument('profiles',
                                   metavar='PROFILE_NAME',
                                   nargs=profileNargs,
                                   help='the profile name')
        if withPackages:
            subparser.add_argument('-p', '--package',
                                   dest='packages',
                                   action='append',
                                   metavar='PACKAGE_IDENTIFIER',
                                   help='use given packages in profile')
        if withEnvvars:
            subparser.add_argument('-e', '--env',
                                   dest='envvars',
                                   action='append',
                                   metavar='KEY=VALUE',
                                   help='use given env variable in profile')


class InitSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "init",
                                    "initialize workspace",
                                    autoFindWorkspace=False)

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs=None,
                                          withPackages=True,
                                          withEnvvars=True)
        pass

    def internalExecute2(self, ws, app, logger, args):
        if ws.configFile.exists():
            raise ValueError("File %s already exist" % str(ws.configFile))
        if ws.dataFolder.exists():
            raise ValueError("Folder %s already exist" % str(ws.dataFolder))
        ws.readConfiguration(initIfNeeded=True)
        logger.printDefault("Workspace initialized", ws.rootFolder)
        if args.packages is not None or args.envvars is not None:
            pf = ws.createProfile(motifList=args.packages,
                                  envMap=envListToMap(args.envvars))
            logger.printDefault("Profile created %s" % pf.name)
            ws.switchProfile(pf.name)


class CreateSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "create",
                                    "create a profile")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='?',
                                          withPackages=True,
                                          withEnvvars=True)
        subparser.add_argument("--nosync",
                               dest="noAutoSync",
                               action="store_true",
                               help="do not auto sync new profile")

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.createProfile(args.profiles,
                              args.packages,
                              envListToMap(args.envvars))
        logger.printDefault("Profile %s created" % pf.name)
        if not args.noAutoSync:
            ws.switchProfile(pf.name)
            logger.printQuiet("Current profile is now %s" % pf.name)


class UpdateSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "update",
                                    "update a profile")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='?',
                                          withPackages=True,
                                          withEnvvars=True)
        subparser.add_argument("--nosync",
                               dest="noAutoSync",
                               action="store_true",
                               help="do not auto sync the modified profile")

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.updateProfile(name=args.profiles,
                              motifList=args.packages,
                              envMap=envListToMap(args.envvars))
        logger.printDefault("Profile %s updated" % pf.name)
        if not args.noAutoSync:
            ws.switchProfile(pf.name)
            logger.printQuiet("Current profile is now %s" % pf.name)


class UpgradeSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "upgrade",
                                    "update all packages of a profile")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='?',
                                          withPackages=False,
                                          withEnvvars=False)
        subparser.add_argument("--nosync",
                               dest="noAutoSync",
                               action="store_true",
                               help="do not auto sync the modified profile")

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.retrieveProfile(name=args.profiles)
        pf = ws.updateProfile(pf.name,
                              motifList=pf.getPfPackageIdentifierMap().keys())
        logger.printDefault("Profile %s upgraded" % pf.name)
        if not args.noAutoSync:
            ws.switchProfile(pf.name)
            logger.printQuiet("Current profile is now %s" % pf.name)


class RenameSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "rename",
                                    "rename a profile",
                                    commandAlias='mv')

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs=2,
                                          withPackages=False,
                                          withEnvvars=False)

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.updateProfile(name=args.profiles[0],
                              newName=args.profiles[1])
        logger.printDefault("Profile %s renamed to %s" %
                            (args.profiles[0], pf.name))


class DeleteSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "delete",
                                    "delete a profile",
                                    commandAlias="rm")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='+',
                                          withPackages=False,
                                          withEnvvars=False)

    def internalExecute2(self, ws, app, logger, args):
        for p in args.profiles:
            pf = ws.deleteProfile(p)
            if pf is not None:
                logger.printDefault("Profile deleted", pf.name)


class ListSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "list",
                                    "list profiles",
                                    commandAlias="ls")

    def internalInitArgs(self, subparser):
        pass

    def internalExecute2(self, ws, app, logger, args):
        logger.displayItem(ws)


class EnvSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "env",
                                    "display profile environment")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='?',
                                          withPackages=False,
                                          withEnvvars=False)
        subparser.add_argument('--activate-script',
                               dest='activateScript',
                               type=Path,
                               help="create a script to activate the env variables of the profile")
        subparser.add_argument('--deactivate-script',
                               dest='deactivateScript',
                               type=Path,
                               help="create a script to deactivate the env variables of the profile")

    def internalExecute2(self, ws, app, logger, args):
        env = ws.getProfileEnv(args.profiles)
        logger.displayItem(env)
        genEnvScript(env, args.activateScript, args.deactivateScript)


class SwitchSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "sync",
                                    "set current profile (if specified), install packages (if needed) and synchronize leaf-data tree")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='?',
                                          withPackages=False,
                                          withEnvvars=False)

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.switchProfile(args.profiles)
        logger.printQuiet("Current profile is now %s" % pf.name)
        logger.printVerbose(pf.folder)


class WorkspaceSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "workspace",
                                    "configure the workspace",
                                    commandAlias="ws")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs=None,
                                          withPackages=False,
                                          withEnvvars=True)
        subparser.add_argument('--remote',
                               dest='remotes',
                               action='append',
                               metavar='URL',
                               help='add given remote url')
        subparser.add_argument('--module',
                               dest='modules',
                               action='append',
                               metavar='MODULE',
                               help='add supported modules')

    def internalExecute2(self, ws, app, logger, args):
        ws.updateWorkspace(remotes=args.remotes,
                           envMap=envListToMap(args.envvars),
                           modules=args.modules)
        logger.printQuiet("Workspace updated")


class SearchSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "search",
                                    "search packages")

    def internalInitArgs(self, subparser):
        subparser.add_argument('-P', "--profile",
                               dest='searchCurrentProfile',
                               action='store_true',
                               help='filter packages from current profile')
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument('keywords',
                               nargs=argparse.ZERO_OR_MORE)

    def internalExecute2(self, ws, app, logger, args):
        pkgFilter = AndPackageFilter()
        pf = None
        if not args.allPackages:
            pkgFilter.addFilter(MasterPackageFilter())
            pass
        if args.searchCurrentProfile:
            pf = ws.retrieveProfile()
            logger.printDefault("Filter packages from profile %s" % pf.name)
            pkgFilter.addFilter(PkgNamePackageFilter([PackageIdentifier.fromString(pis).name
                                                      for pis in pf.getPfPackages()]))
        else:
            wsModules = ws.readConfiguration().getWsSupportedModules()
            if len(wsModules) > 0:
                logger.printDefault("Filter by modules:",
                                    ", ".join(wsModules))
                pkgFilter.addFilter(ModulePackageFilter(wsModules))

        if args.keywords is not None and len(args.keywords) > 0:
            logger.printDefault("Filter by keywords:",
                                ", ".join(args.keywords))
            pkgFilter.addFilter(KeywordPackageFilter(args.keywords))

        # Pkg list
        mfList = sorted(app.listAvailablePackages().values(),
                        key=Manifest.getIdentifier)
        # manage tags
        TagManager().tagLatest(mfList)
        if pf is not None:
            TagManager().tagCurrent(mfList, pf)

        # Print filtered packages
        for mf in mfList:
            if pkgFilter.matches(mf):
                logger.displayItem(mf)
