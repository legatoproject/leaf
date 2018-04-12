'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.constants import LeafFiles
from leaf.core import Workspace
from leaf.model import Profile
from leaf.utils import envListToMap, findWorkspaceRoot
import os
from pathlib import Path

from leaf.cliutils import LeafCommand, initCommonArgs, LeafCommandGenerator


class UserConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "config:user",
                             "update user configuration",
                             cmdAliases=["config:u"])

    def internalInitArgs(self, subparser):
        initCommonArgs(subparser,
                       withEnv=True,
                       withRemotes=True)
        subparser.add_argument('--root',
                               dest='rootFolder',
                               type=Path,
                               metavar='DIR',
                               help="set the root folder, default: %s" % LeafFiles.DEFAULT_LEAF_ROOT)

    def internalExecute(self, app, logger, args):
        app.updateUserConfiguration(args.rootFolder,
                                    envListToMap(args.setEnvList),
                                    args.unsetEnvList,
                                    args.addRemoteList,
                                    args.rmRemoteList)


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "status",
                             "print leaf status",
                             cmdAliases=["s"])

    def internalInitArgs(self, subparser):
        pass

    def internalExecute(self, app, logger, args):
        wspath = findWorkspaceRoot(currentFolder=args.workspace,
                                   failIfNoWs=False)
        if wspath is not None:
            ws = Workspace(wspath, app)
            logger.displayItem(ws)
        else:
            logger.printDefault(
                "Not in a workspace, use 'leaf init' to create one")


class SetupCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "setup",
                             "all in one command to create a profile in a workspace")

    def internalInitArgs(self, subparser):
        initCommonArgs(subparser,
                       withEnv=True,
                       withPackages=True,
                       profileNargs='?')

    def leafExec(self, cmdGenerator, verb, arguments=None, logger=None):
        command = cmdGenerator.genCommand(verb,
                                          arguments=arguments)
        if logger is not None:
            logger.printQuiet("  -> Execute command:", "leaf", *command)
        from leaf.cli import LeafCli
        return LeafCli().run(customArgs=command,
                             handleExceptions=None)

    def internalExecute(self, app, logger, args):

        cmdGenerator = LeafCommandGenerator()
        cmdGenerator.initCommonArgs(args)

        # Checks
        if args.motifList is None:
            raise ValueError(
                "You need to add at least one package to your profile")

        # Find or create workspace
        wspath = findWorkspaceRoot(args.workspace, failIfNoWs=False)
        if wspath is None:
            wspath = args.workspace
            if wspath is None:
                wspath = Path(os.getcwd())
            logger.confirm(question="Cannot find workspace, initialize one in %s" % wspath,
                           failOnDecline=True)
            self.leafExec(cmdGenerator,
                          verb=["init"],
                          logger=logger)

        # Resolve packages
        piList = app.resolveLatest(args.motifList, ipMap=True, apMap=True)

        # Profile name
        profileName = args.profiles
        if profileName is None:
            profileName = Profile.genDefaultName(piList)
            logger.printDefault(
                "No profile name given, the new profile will be automatically named %s" % profileName)

        self.leafExec(cmdGenerator,
                      "create",
                      [profileName],
                      logger=logger)

        configArgs = []
        for m in args.motifList:
            configArgs += ["--package", m]
        if args.setEnvList is not None:
            for e in args.setEnvList:
                configArgs += ["--set", e]
        if args.unsetEnvList is not None:
            for e in args.unsetEnvList:
                configArgs += ["--unset", e]
        self.leafExec(cmdGenerator,
                      "config:profile",
                      configArgs,
                      logger=logger)

        self.leafExec(cmdGenerator,
                      "sync",
                      logger=logger)
