'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
import os
from pathlib import Path

from leaf.cli.cliutils import LeafCommand, initCommonArgs, LeafCommandGenerator
from leaf.model.workspace import Profile
from leaf.utils import findWorkspaceRoot


class SetupCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self,
                             "setup",
                             "all in one command to create a profile in a workspace")

    def initArgs(self, parser):
        super().initArgs(parser)
        initCommonArgs(parser,
                       addRemoveEnv=True,
                       addRemovePackages=True)
        parser.add_argument('profiles', nargs=argparse.OPTIONAL,
                            metavar='PROFILE', help='the profile name'),

    def leafExec(self, cmdGenerator, verb, arguments=None, logger=None):
        command = cmdGenerator.genCommand(verb,
                                          arguments=arguments)
        if logger is not None:
            logger.printQuiet("  -> Execute command:", "leaf", *command)
        from leaf.cli.cli import LeafCli
        return LeafCli().run(command, handleExceptions=False)

    def execute(self, args):

        logger = self.getLogger(args)
        app = self.getPackageManager(args)

        cmdGenerator = LeafCommandGenerator()
        cmdGenerator.initCommonArgs(args)

        # Checks
        if args.pkgAddList is None:
            raise ValueError(
                "You need to add at least one package to your profile")

        # Find or create workspace
        wspath = findWorkspaceRoot(args.workspace, failIfNoWs=False)
        if wspath is None:
            wspath = args.workspace
            if wspath is None:
                wspath = Path(os.getcwd())
            logger.confirm(question="Cannot find workspace, initialize one in %s?" % wspath,
                           failOnDecline=True)
            self.leafExec(cmdGenerator, "init",
                          logger=logger)

        # Resolve packages
        piList = app.resolveLatest(args.pkgAddList, ipMap=True, apMap=True)

        # Profile name
        profileName = args.profiles
        if profileName is None:
            profileName = Profile.genDefaultName(piList)
            logger.printDefault(
                "No profile name given, the new profile will be automatically named %s" % profileName)

        self.leafExec(cmdGenerator, ("profile", "create"),
                      [profileName],
                      logger=logger)

        configArgs = [profileName]
        for m in args.pkgAddList:
            configArgs += ["-p", m]
        self.leafExec(cmdGenerator, ("profile", "config"),
                      configArgs,
                      logger=logger)

        if args.envAddList is not None or args.envRmList is not None:
            configArgs = [profileName]
            if args.envAddList is not None:
                for e in args.envAddList:
                    configArgs += ["--set", e]
            if args.envRmList is not None:
                for e in args.envRmList:
                    configArgs += ["--unset", e]
            self.leafExec(cmdGenerator, ("env", "profile"),
                          configArgs,
                          logger=logger)

        self.leafExec(cmdGenerator, ("profile", "sync"),
                      [profileName],
                      logger=logger)
