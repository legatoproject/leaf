"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import argparse

from leaf.cli.base import LeafCommand
from leaf.cli.completion import complete_binaries
from leaf.core.error import LeafException
from leaf.core.logger import Verbosity
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.modelutils import execute_command
from leaf.model.package import IDENTIFIER_GETTER, PackageIdentifier
from leaf.model.steps import VariableResolver
from leaf.rendering.renderer.entrypoint import EntrypointListRenderer


class RunCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "run", "execute binary provided by installed packages", allow_uargs=True)

    def _get_examples(self):
        return [("leaf run", "List all declared commands"), ("leaf run myCommand -- --help", "See help of a given binary")]

    def _configure_parser(self, parser):
        # Do not call super() to prevent --verbose/--quiet
        parser.add_argument(
            "-p", "--package", dest="package", metavar="PKG_IDENTIFIER", type=PackageIdentifier.parse, help="search binary in specified package"
        )
        parser.add_argument("--oneline", action="store_true", help="quiet output when listing available binaries")
        parser.add_argument("binary", metavar="BINARY_NAME", nargs=argparse.OPTIONAL, help="name of binary to execute").completer = complete_binaries

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)

        ipmap = wm.list_installed_packages()
        searching_iplist = None
        env = None

        if args.package is not None:
            # User forces the package
            env = Environment.build(wm.build_builtin_environment(), wm.build_user_environment())
            searching_iplist = DependencyUtils.installed([args.package], ipmap, env=env)
            env.append(wm.build_packages_environment(searching_iplist))
        elif wm.is_initialized:
            # We are in a workspace, use the current profile
            pfname = wm.current_profile_name
            profile = wm.get_profile(pfname)
            wm.is_profile_sync(profile, raise_if_not_sync=True)
            searching_iplist = wm.get_profile_dependencies(profile)
            env = wm.build_full_environment(profile)
        else:
            # Use installed packages
            searching_iplist = sorted(ipmap.values(), key=IDENTIFIER_GETTER)

        # Execute
        if args.binary is None:
            # Print mode
            scope = "installed packages"
            if args.package is not None:
                scope = args.package
            elif wm.is_initialized:
                scope = "workspace"
            rend = EntrypointListRenderer(scope)
            rend.extend(searching_iplist)
            wm.print_renderer(rend, verbosity=Verbosity.QUIET if args.oneline else Verbosity.DEFAULT)
        elif args.oneline:
            # User gave BIN and --oneline
            raise LeafException(
                "You must specify a binary or '--oneline', not both",
                hints=[
                    "Run 'leaf run --oneline' to list all binaries",
                    "Run 'leaf run {bin} -- --oneline {uargs}' pass --oneline to the binary".format(bin=args.binary, uargs=" ".join(uargs)),
                ],
            )
        else:
            # Search entry point
            candidate_ip = None
            for ip in searching_iplist:
                if args.binary in ip.binaries:
                    if candidate_ip is None:
                        candidate_ip = ip
                    elif candidate_ip.name != ip.name:
                        raise LeafException("Binary {bin} is declared by multiple packages".format(bin=args.binary))
                    elif ip.identifier > candidate_ip.identifier:
                        candidate_ip = ip
            if candidate_ip is None:
                raise LeafException("Cannot find binary {bin}".format(bin=args.binary))

            if env is None:
                env = Environment.build(wm.build_builtin_environment(), wm.build_user_environment())
                env.append(wm.build_packages_environment(DependencyUtils.installed([candidate_ip.identifier], ipmap, env=env)))

            ep = candidate_ip.binaries[args.binary]
            vr = VariableResolver(candidate_ip, ipmap.values())
            return execute_command(vr.resolve(ep.command), *uargs, print_stdout=True, env=env, shell=ep.shell)
