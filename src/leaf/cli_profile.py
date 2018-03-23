'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import abstractmethod
from leaf.cli import LeafCli, LeafCommand
from leaf.constants import LeafConstants
from leaf.core import Workspace
from leaf.utils import envListToMap, findWorkspaceRoot
import os
from pathlib import Path
import shutil


def main():
    return ProfileCli().run()


class ProfileCli (LeafCli):
    def __init__(self):
        LeafCli.__init__(self,
                         ListSubCommand(),
                         InitSubCommand(),
                         CreateSubCommand(),
                         UpdateSubCommand(),
                         DeleteSubCommand(),
                         SwitchSubCommand(),
                         EnvSubCommand())
        self.parser.add_argument("-w", "--workspace",
                                 dest="workspace",
                                 type=Path,
                                 help="use given workspace")


class AbstractSubCommand(LeafCommand):
    def __init__(self, commandName, commandDescription, autoFindWorkspace=True):
        LeafCommand.__init__(self,
                             commandName,
                             commandDescription)
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
                                   metavar='ENV_VAR',
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
        ws.dataFolder.mkdir()
        ws.createProfile(LeafConstants.DEFAULT_PROFILE,
                         initConfigFile=True)
        ws.switchProfile(LeafConstants.DEFAULT_PROFILE)
        logger.printDefault("Workspace initialized", ws.rootFolder)
        if args.packages is not None or args.envvars is not None:
            ws.updateProfile(LeafConstants.DEFAULT_PROFILE,
                             args.packages,
                             envListToMap(args.envvars))
            ws.switchProfile(LeafConstants.DEFAULT_PROFILE)


class CreateSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "create",
                                    "create a profile")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs=1,
                                          withPackages=True,
                                          withEnvvars=True)

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.createProfile(args.profiles[0],
                              args.packages,
                              envListToMap(args.envvars))
        logger.printDefault("Profile created")
        logger.displayItem(pf)


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

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.updateProfile(args.profiles,
                              args.packages,
                              envListToMap(args.envvars))
        logger.printDefault("Profile updated")
        logger.displayItem(pf)


class DeleteSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "delete",
                                    "delete a profile")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='+',
                                          withPackages=False,
                                          withEnvvars=False)

    def internalExecute2(self, ws, app, logger, args):
        for p in args.profiles:
            pf = ws.deleteProfile(p)
            if pf.folder.exists():
                shutil.rmtree(str(pf.folder))
            logger.printDefault("Profile deleted", pf.name)


class ListSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "list",
                                    "list profiles")

    def internalInitArgs(self, subparser):
        pass

    def internalExecute2(self, ws, app, logger, args):
        pfMap = ws.getProfileMap()
        logger.printVerbose("List of profiles in", ws.rootFolder)
        current = ws.getCurrentProfileName()
        for name, pf in pfMap.items():
            if name == current:
                name += " [current]"
            logger.displayItem(pf)


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

    def internalExecute2(self, ws, app, logger, args):
        env = ws.getProfileEnv(args.profiles)
        for k, v in env:
            logger.printQuiet('export %s="%s"' % (k, v))


class SwitchSubCommand(AbstractSubCommand):
    def __init__(self):
        AbstractSubCommand.__init__(self,
                                    "switch",
                                    "switch current profile and install packages if needed")

    def internalInitArgs(self, subparser):
        AbstractSubCommand.initCommonArgs(subparser,
                                          profileNargs='?',
                                          withPackages=False,
                                          withEnvvars=False)

    def internalExecute2(self, ws, app, logger, args):
        pf = ws.switchProfile(args.profiles)
        logger.printQuiet("Switched to profile", pf.name)
        logger.printVerbose(pf.folder)
