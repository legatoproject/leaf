'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import argparse
import os
import subprocess
from collections import OrderedDict

from leaf.cli.plugins import LeafPluginCommand
from leaf.core.constants import LeafSettings
from leaf.model.modelutils import groupPackageIdentifiersByName
from leaf.core.error import InvalidPackageNameException, LeafException
from leaf.model.package import PackageIdentifier
from leaf.model.workspace import Profile


class SetupPlugin(LeafPluginCommand):

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('-p', '--add-package',
                            dest='packages',
                            action='append',
                            metavar='PKG_NAME',
                            help="add a package to profile")
        parser.add_argument('--set',
                            dest='envVars',
                            action='append',
                            metavar='KEY=VALUE',
                            help="add environment variable to profile")
        parser.add_argument('profiles', nargs=argparse.OPTIONAL,
                            metavar='PROFILE', help='the profile name')

    def execute(self, args, uargs):
        wm = self.getWorkspaceManager(autoFindWorkspace=False,
                                      checkInitialized=False)
        cmdGenerator = LeafCommandGenerator()
        cmdGenerator.initCommonArgs(args)

        # Checks
        if args.packages is None or len(args.packages) == 0:
            raise LeafException(
                "You need to add at least one package to your profile")

        # Compute PackageIdentifiers
        piList = resolveLatest(args.packages, wm)

        # Find or create workspace
        if not wm.isWorkspaceInitialized():
            wm.confirm("Cannot find workspace, initialize one in %s?" % wm.workspaceRootFolder,
                       raiseOnDecline=True)
            leafExec(cmdGenerator, wm.logger, "init")

        # Profile name
        profileName = args.profiles
        if profileName is None:
            profileName = Profile.genDefaultName(piList)
            wm.logger.printDefault(
                "No profile name given, the new profile will be automatically named %s" % profileName)

        # Create profile
        leafExec(cmdGenerator, wm.logger,
                 ("profile", "create"),
                 [profileName])

        # Update profile with packages
        configArgs = [profileName]
        for pi in piList:
            configArgs += ["-p", str(pi)]
        leafExec(cmdGenerator, wm.logger,
                 ("profile", "config"),
                 configArgs)

        # Set profile env
        if args.envVars is not None:
            configArgs = [profileName]
            for e in args.envVars:
                configArgs += ["--set", e]
            leafExec(cmdGenerator, wm.logger,
                     ("env", "profile"),
                     configArgs)

        # Run sync command
        leafExec(cmdGenerator, wm.logger,
                 ("profile", "sync"),
                 [profileName])


class LeafCommandGenerator():

    def __init__(self):
        self.preVerbArgs = OrderedDict()
        self.postVerbArgs = OrderedDict()

    def initCommonArgs(self, args):
        # Verbose, Quiet
        if LeafSettings.VERBOSITY.value == "verbose":
            self.postVerbArgs["--verbose"] = None
        elif LeafSettings.VERBOSITY.value == "quiet":
            self.postVerbArgs["--quiet"] = None

    def genCommand(self, verb, arguments=None):
        command = ['leaf']
        for k, v in self.preVerbArgs.items():
            if v is None:
                command.append(k)
            else:
                command += [k, str(v)]
        if isinstance(verb, (list, tuple)):
            command += verb
        else:
            command.append(verb)
        for k, v in self.postVerbArgs.items():
            if v is None:
                command.append(k)
            else:
                command += [k, str(v)]
        if arguments is not None:
            command += list(map(str, arguments))
        return command


def resolveLatest(pkgMotifList, pm):
    out = []
    groupedPackages = {}
    groupPackageIdentifiersByName(pm.listInstalledPackages().keys(),
                                  pkgMap=groupedPackages)
    groupPackageIdentifiersByName(pm.listAvailablePackages().keys(),
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


def leafExec(cmdGenerator, logger, verb, arguments=None):
    command = cmdGenerator.genCommand(verb, arguments=arguments)
    logger.printQuiet("  -> Execute:", *command)
    rc = subprocess.call(command,
                         env=os.environ,
                         stdout=None,
                         stderr=subprocess.STDOUT)
    if rc != 0:
        logger.printError("Command exited with %d" % rc)
        raise LeafException("Sub command failed: '%s'" % (" ".join(command)))
