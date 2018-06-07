'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.constants import LeafFiles
from leaf.utils import envListToMap, findWorkspaceRoot
import os
from pathlib import Path

from leaf.cli.cliutils import LeafCommand, initCommonArgs, LeafCommandGenerator
from leaf.core.workspacemanager import WorkspaceManager
from leaf.model.workspace import Profile


class UserConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "config:user",
                             "update user configuration",
                             cmdAliases=["config:u"])

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       withEnv=True,
                       withRemotes=True)
        parser.add_argument('--root',
                            dest='rootFolder',
                            type=Path,
                            metavar='DIR',
                            help="set the root folder, default: %s" % LeafFiles.DEFAULT_LEAF_ROOT)

    def execute(self, args):
        self.getApp(args).updateUserConfiguration(args.rootFolder,
                                                  envListToMap(
                                                      args.setEnvList),
                                                  args.unsetEnvList,
                                                  args.addRemoteList,
                                                  args.rmRemoteList)


class StatusCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "status",
                             "print leaf status",
                             cmdAliases=["s"])

    def execute(self, args):
        wspath = findWorkspaceRoot(currentFolder=args.workspace,
                                   failIfNoWs=False)
        if wspath is not None:
            ws = WorkspaceManager(wspath, self.getApp(args))
            self.getLogger(args).displayItem(ws)
        else:
            self.getLogger(args).printDefault(
                "Not in a workspace, use 'leaf init' to create one")


class SetupCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "setup",
                             "all in one command to create a profile in a workspace")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       withEnv=True,
                       withPackages=True,
                       profileNargs='?')

    def leafExec(self, cmdGenerator, verb, arguments=None, logger=None):
        command = cmdGenerator.genCommand(verb,
                                          arguments=arguments)
        if logger is not None:
            logger.printQuiet("  -> Execute command:", "leaf", *command)
        from leaf.cli.cli import LeafCli
        return LeafCli().run(customArgs=command,
                             handleExceptions=False)

    def execute(self, args):

        logger = self.getLogger(args)
        app = self.getApp(args, logger=logger)

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
