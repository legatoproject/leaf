"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import argparse
import os
import subprocess
from collections import OrderedDict

from leaf.cli.completion import complete_available_packages
from leaf.cli.plugins import LeafPluginCommand
from leaf.core.constants import LeafSettings
from leaf.core.error import InvalidPackageNameException, LeafException
from leaf.model.modelutils import group_package_identifiers_by_name
from leaf.model.package import PackageIdentifier
from leaf.model.workspace import Profile


class SetupPlugin(LeafPluginCommand):
    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument(
            "-p", "--add-package", dest="packages", action="append", metavar="PKG_NAME", help="add a package to profile"
        ).completer = complete_available_packages
        parser.add_argument("--set", dest="env_vars", action="append", metavar="KEY=VALUE", help="add environment variable to profile")
        parser.add_argument("profiles", nargs=argparse.OPTIONAL, metavar="PROFILE", help="the profile name")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_parents=True, check_initialized=False)
        cmd_generator = LeafCommandGenerator()
        cmd_generator.init_common_args(args)

        # Checks
        if args.packages is None or len(args.packages) == 0:
            raise LeafException("You need to add at least one package to your profile")

        # Compute PackageIdentifiers
        pilist = resolve_latest(args.packages, wm)

        # Find or create workspace
        if not wm.is_initialized:
            wm.print_with_confirm("Cannot find workspace, initialize one in {wm.ws_root_folder}?".format(wm=wm), raise_on_decline=True)
            leaf_exec(cmd_generator, wm.logger, "init")

        # Profile name
        pfname = args.profiles
        if pfname is None:
            pfname = Profile.generate_default_name(pilist)
            wm.logger.print_default("No profile name given, the new profile will be automatically named {name}".format(name=pfname))

        # Create profile
        leaf_exec(cmd_generator, wm.logger, ("profile", "create"), [pfname])

        # Update profile with packages
        config_args = [pfname]
        for pi in pilist:
            config_args += ["-p", str(pi)]
        leaf_exec(cmd_generator, wm.logger, ("profile", "config"), config_args)

        # Set profile env
        if args.env_vars is not None:
            config_args = [pfname]
            for e in args.env_vars:
                config_args += ["--set", e]
            leaf_exec(cmd_generator, wm.logger, ("env", "profile"), config_args)

        # Run sync command
        leaf_exec(cmd_generator, wm.logger, ("profile", "sync"), [pfname])


class LeafCommandGenerator:
    def __init__(self):
        self.preVerbArgs = OrderedDict()
        self.postVerbArgs = OrderedDict()

    def init_common_args(self, args):
        # Verbose, Quiet
        if LeafSettings.VERBOSITY.value == "verbose":
            self.postVerbArgs["--verbose"] = None
        elif LeafSettings.VERBOSITY.value == "quiet":
            self.postVerbArgs["--quiet"] = None

    def gen_command(self, verb, arguments=None):
        command = ["leaf"]
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


def resolve_latest(motif_list, pm):
    out = []
    grouped_packages = {}
    group_package_identifiers_by_name(pm.list_installed_packages().keys(), pkgmap=grouped_packages)
    group_package_identifiers_by_name(pm.list_available_packages().keys(), pkgmap=grouped_packages)

    for motif in motif_list:
        pi = None
        if PackageIdentifier.is_valid_identifier(motif):
            pi = PackageIdentifier.parse(motif)
            if pi.name not in grouped_packages or pi not in grouped_packages[pi.name]:
                # Unknwon package
                pi = None
        elif motif in grouped_packages:
            # Get latest of the sorted list
            pi = grouped_packages[motif][-1]

        # Check if package identifier has been found
        if pi is None:
            raise InvalidPackageNameException(motif)

        out.append(pi)

    return out


def leaf_exec(generator, logger, verb, arguments=None):
    command = generator.gen_command(verb, arguments=arguments)
    logger.print_quiet("  -> Execute:", *command)
    rc = subprocess.call(command, env=os.environ, stdout=None, stderr=subprocess.STDOUT)
    if rc != 0:
        logger.print_error("Command exited with {rc}".format(rc=rc))
        raise LeafException("Sub command failed: '{cmd}'".format(cmd=" ".join(command)))
