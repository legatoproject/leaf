"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import argparse
from builtins import ValueError
from collections import OrderedDict

from leaf.api import PackageManager
from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import get_optional_arg
from leaf.cli.completion import complete_all_packages, complete_available_packages, complete_installed_packages, complete_installed_packages_tags
from leaf.core.error import PackageInstallInterruptedException
from leaf.core.utils import env_list_to_map
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import IDENTIFIER_GETTER, PackageIdentifier
from leaf.rendering.renderer.manifest import ManifestListRenderer


class PackageListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "list", "list installed packages")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-a", "--all", dest="show_all_packages", action="store_true", help="display all packages, not only master packages")
        parser.add_argument(
            "-t", "--tag", dest="tags", metavar="TAG", action="append", help="filter search results matching with given tag"
        ).completer = complete_installed_packages_tags
        parser.add_argument(
            "keywords", metavar="KEYWORD", nargs=argparse.ZERO_OR_MORE, help="filter with given keywords"
        ).completer = complete_installed_packages

    def execute(self, args, uargs):
        pm = PackageManager()
        metafilter = MetaPackageFilter()

        if not get_optional_arg(args, "show_all_packages", False):
            metafilter.only_master_packages()

        for t in get_optional_arg(args, "tags", []):
            metafilter.with_tag(t)

        for kw in get_optional_arg(args, "keywords", []):
            metafilter.with_keyword(kw)

        # Print filtered packages
        rend = ManifestListRenderer(metafilter)
        mflist = pm.list_installed_packages().values()
        rend.extend(filter(metafilter.matches, mflist))
        pm.print_renderer(rend)


class PackageDepsCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "deps", "Build the dependency chain")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--installed",
            dest="dependency_type",
            action="store_const",
            const="installed",
            default="installed",
            help="build dependency list from installed packages",
        )
        group.add_argument("--available", dest="dependency_type", action="store_const", const="available", help="build dependency list from available packages")
        group.add_argument("--install", dest="dependency_type", action="store_const", const="install", help="build dependency list to install")
        group.add_argument("--uninstall", dest="dependency_type", action="store_const", const="uninstall", help="build dependency list to uninstall")
        group.add_argument("--prereq", dest="dependency_type", action="store_const", const="prereq", help="build dependency list for prereq install")
        group.add_argument("--upgrade", dest="dependency_type", action="store_const", const="upgrade", help="build dependency list for upgrade")
        group.add_argument(
            "--rdepends", dest="dependency_type", action="store_const", const="rdepends", help="list packages having given package(s) as dependency"
        )
        parser.add_argument("--env", dest="custom_envlist", action="append", metavar="KEY=VALUE", help="add given environment variable")
        parser.add_argument("packages", metavar="PKG_IDENTIFIER", nargs=argparse.ZERO_OR_MORE, help="package identifier").completer = complete_all_packages

    def execute(self, args, uargs):
        pm = PackageManager()
        env = None
        # If the user specified env values, build a complete env
        if args.custom_envlist is not None:
            env = Environment.build(
                pm.build_builtin_environment(), pm.build_user_environment(), Environment("Custom env", env_list_to_map(args.custom_envlist))
            )

        items = None
        if args.dependency_type == "available":
            items = DependencyUtils.install(PackageIdentifier.parse_list(args.packages), pm.list_available_packages(), {}, env=env)
        elif args.dependency_type == "install":
            items = DependencyUtils.install(PackageIdentifier.parse_list(args.packages), pm.list_available_packages(), pm.list_installed_packages(), env=env)
        elif args.dependency_type == "installed":
            items = DependencyUtils.installed(PackageIdentifier.parse_list(args.packages), pm.list_installed_packages(), env=env, ignore_unknown=True)
        elif args.dependency_type == "uninstall":
            items = DependencyUtils.uninstall(PackageIdentifier.parse_list(args.packages), pm.list_installed_packages(), env=env)
        elif args.dependency_type == "prereq":
            items = DependencyUtils.prereq(PackageIdentifier.parse_list(args.packages), pm.list_available_packages(), pm.list_installed_packages(), env=env)
        elif args.dependency_type == "upgrade":
            items, _ = DependencyUtils.upgrade(
                None if len(args.packages) == 0 else args.packages, pm.list_available_packages(), pm.list_installed_packages(), env=env
            )
        elif args.dependency_type == "rdepends":
            mfmap = OrderedDict()
            mfmap.update(DependencyUtils.rdepends(PackageIdentifier.parse_list(args.packages), pm.list_available_packages(), env=env))
            mfmap.update(DependencyUtils.rdepends(PackageIdentifier.parse_list(args.packages), pm.list_installed_packages(), env=env))
            items = mfmap.values()
        else:
            raise ValueError()

        rend = ManifestListRenderer()
        rend.extend(items)
        pm.print_renderer(rend)


class PackageInstallCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "install", "install packages (download + extract)")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-k", "--keep", dest="keep_on_error", action="store_true", help="keep package folder in case of installation error")
        parser.add_argument(
            "packages", metavar="PKG_IDENTIFIER", nargs=argparse.ONE_OR_MORE, help="identifier of packages to install"
        ).completer = complete_available_packages

    def execute(self, args, uargs):
        pm = PackageManager()

        complete_available_packages()
        try:
            items = pm.install_packages(PackageIdentifier.parse_list(args.packages), keep_folder_on_error=args.keep_on_error)
        except Exception as e:
            raise PackageInstallInterruptedException(args.packages, e)

        if len(items) > 0:
            pm.logger.print_quiet("Packages installed:", " ".join([str(p.identifier) for p in items]))


class PackageUninstallCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "uninstall", "remove packages")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument(
            "packages", metavar="PKG_IDENTIFIER", nargs=argparse.ONE_OR_MORE, help="identifier of package to uninstall"
        ).completer = complete_installed_packages

    def execute(self, args, uargs):
        pm = PackageManager()

        pm.uninstall_packages(PackageIdentifier.parse_list(args.packages))


class PackageSyncCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "sync", "performs sync operation")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument(
            "packages", metavar="PKGNAME", nargs=argparse.ONE_OR_MORE, help="name of package to uninstall"
        ).completer = complete_installed_packages

    def execute(self, args, uargs):
        pm = PackageManager()

        pm.sync_packages(PackageIdentifier.parse_list(args.packages))


class PackageUpgradeCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "upgrade", "upgrade packages to latest version")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("--clean", dest="clean", action="store_true", help="also try to uninstall old versions of upgraded packages")
        parser.add_argument(
            "packages", metavar="PKGNAME", nargs=argparse.ZERO_OR_MORE, help="name of the packages to upgrade"
        ).completer = complete_installed_packages

    def execute(self, args, uargs):
        pm = PackageManager()

        env = Environment.build(pm.build_builtin_environment(), pm.build_user_environment())

        install_list, uninstall_list = DependencyUtils.upgrade(
            None if len(args.packages) == 0 else args.packages, pm.list_available_packages(), pm.list_installed_packages(), env=env
        )

        pm.logger.print_verbose(
            "{count} package(s) to be upgraded: {text}".format(count=len(install_list), text=" ".join([str(ap.identifier) for ap in install_list]))
        )
        if args.clean:
            pm.logger.print_verbose(
                "{count} package(s) to be removed: {text}".format(count=len(uninstall_list), text=" ".join([str(ip.identifier) for ip in uninstall_list]))
            )

        if len(install_list) == 0:
            pm.logger.print_default("No package to upgrade")
        else:
            pm.install_packages(map(IDENTIFIER_GETTER, install_list), env=env)
            if len(uninstall_list) > 0:
                if args.clean:
                    pm.uninstall_packages(map(IDENTIFIER_GETTER, uninstall_list))
                else:
                    pm.logger.print_default("These packages can be removed:", " ".join([str(ip.identifier) for ip in uninstall_list]))
