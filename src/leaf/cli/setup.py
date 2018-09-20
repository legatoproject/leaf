'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse

from leaf.cli.cliutils import LeafCommand, LeafCommandGenerator, \
    initCommonArgs
from leaf.core.coreutils import groupPackageIdentifiersByName
from leaf.core.error import InvalidPackageNameException
from leaf.core.workspacemanager import WorkspaceManager
from leaf.model.package import PackageIdentifier
from leaf.model.workspace import Profile


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
        pm = self.getPackageManager(args)

        cmdGenerator = LeafCommandGenerator()
        cmdGenerator.initCommonArgs(args)

        # Checks
        if args.pkgAddList is None:
            raise ValueError(
                "You need to add at least one package to your profile")

        # Compute PackageIdentifiers
        piList = self.resolveLatest(args.pkgAddList, pm)

        # Find or create workspace
        workspaceRoot = WorkspaceManager.findRoot(customPath=args.workspace)
        if not WorkspaceManager.isWorkspaceRoot(workspaceRoot):
            pm.logger.confirm(question="Cannot find workspace, initialize one in %s?" % workspaceRoot,
                              failOnDecline=True)
            self.leafExec(cmdGenerator, "init",
                          logger=pm.logger)

        # Profile name
        profileName = args.profiles
        if profileName is None:
            profileName = Profile.genDefaultName(piList)
            pm.logger.printDefault(
                "No profile name given, the new profile will be automatically named %s" % profileName)

        # Create profile
        self.leafExec(cmdGenerator, ("profile", "create"),
                      [profileName],
                      logger=pm.logger)

        # Update profile with packages
        configArgs = [profileName]
        for pi in piList:
            configArgs += ["-p", str(pi)]
        self.leafExec(cmdGenerator, ("profile", "config"),
                      configArgs,
                      logger=pm.logger)

        # Set profile env
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
                          logger=pm.logger)

        # Run sync command
        self.leafExec(cmdGenerator, ("profile", "sync"),
                      [profileName],
                      logger=pm.logger)

    def resolveLatest(self, pkgMotifList, pm):
        out = []
        groupedPackages = groupPackageIdentifiersByName(
            pm.listInstalledPackages().keys())
        groupedPackages = groupPackageIdentifiersByName(
            pm.listAvailablePackages().keys(),
            pkgMap=groupedPackages)

        for pkgMotif in pkgMotifList:
            pi = None
            if PackageIdentifier.isValidIdentifier(pkgMotif):
                pi = PackageIdentifier.fromString(pkgMotif)
                if pi.name not in groupedPackages or pi not in groupedPackages[pi.name]:
                    # Unknwon package
                    pi = None
            elif pkgMotif in groupedPackages:
                    # Get latest of the sorted list
                pi = groupedPackages[pkgMotif][-1]

            # Check if package identifier has been found
            if pi is None:
                raise InvalidPackageNameException(pkgMotif)

            out.append(pi)

        return out
