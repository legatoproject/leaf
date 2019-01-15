'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from builtins import ValueError
from pathlib import Path

from leaf.cli.cliutils import LeafCommand
from leaf.core.dependencies import DependencyUtils
from leaf.core.error import PackageInstallInterruptedException
from leaf.format.renderer.manifest import ManifestListRenderer
from leaf.model.environment import Environment
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import Manifest, PackageIdentifier
from leaf.utils import envListToMap, mkTmpLeafRootDir


class PackageListCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'list',
            "list installed packages")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument("-a", "--all",
                            dest="allPackages",
                            action="store_true",
                            help="display all packages, not only master packages")
        parser.add_argument("-t", "--tag",
                            dest="tags", metavar="TAG",
                            action="append",
                            help="filter search results matching with given tag")
        parser.add_argument('keywords', metavar="KEYWORD",
                            nargs=argparse.ZERO_OR_MORE,
                            help="filter with given keywords")

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)

        pkgFilter = MetaPackageFilter()
        if 'allPackages' not in vars(args) or not args.allPackages:
            pkgFilter.onlyMasterPackages()

        if 'tags' in vars(args) and args.tags is not None:
            for t in args.tags:
                pkgFilter.withTag(t)

        if 'keywords' in vars(args) and args.keywords is not None and len(args.keywords) > 0:
            for kw in args.keywords:
                pkgFilter.withKeyword(kw)

        # Print filtered packages
        rend = ManifestListRenderer(pkgFilter)
        mfList = sorted(pm.listInstalledPackages().values(),
                        key=Manifest.getIdentifier)
        rend.extend(mf for mf in mfList if pkgFilter.matches(mf))
        pm.printRenderer(rend)


class PackageDepsCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'deps',
            "Build the dependency chain")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--installed",
                           dest="dependencyType",
                           action="store_const",
                           const="installed",
                           default="installed",
                           help="build dependency list from installed packages")
        group.add_argument("--available",
                           dest="dependencyType",
                           action="store_const",
                           const="available",
                           help="build dependency list from available packages")
        group.add_argument("--install",
                           dest="dependencyType",
                           action="store_const",
                           const="install",
                           help="build dependency list to install")
        group.add_argument("--uninstall",
                           dest="dependencyType",
                           action="store_const",
                           const="uninstall",
                           help="build dependency list to uninstall")
        group.add_argument("--prereq",
                           dest="dependencyType",
                           action="store_const",
                           const="prereq",
                           help="build dependency list for prereq install")
        group.add_argument("--upgrade",
                           dest="dependencyType",
                           action="store_const",
                           const="upgrade",
                           help="build dependency list for upgrade")
        parser.add_argument('--env',
                            dest='customEnvList',
                            action='append',
                            metavar='KEY=VALUE',
                            help='add given environment variable')
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ZERO_OR_MORE,
                            help='package identifier')

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)
        env = Environment.build(
            pm.getBuiltinEnvironment(),
            pm.getUserEnvironment(),
            Environment("Custom env", envListToMap(args.customEnvList)))

        items = None
        if args.dependencyType == 'available':
            items = DependencyUtils.install(
                PackageIdentifier.fromStringList(args.packages),
                pm.listAvailablePackages(),
                {},
                env=env)
        elif args.dependencyType == 'install':
            items = DependencyUtils.install(
                PackageIdentifier.fromStringList(args.packages),
                pm.listAvailablePackages(),
                pm.listInstalledPackages(),
                env=env)
        elif args.dependencyType == 'installed':
            items = DependencyUtils.installed(
                PackageIdentifier.fromStringList(args.packages),
                pm.listInstalledPackages(),
                env=env)
        elif args.dependencyType == 'uninstall':
            items = DependencyUtils.uninstall(
                PackageIdentifier.fromStringList(args.packages),
                pm.listInstalledPackages(),
                env=env)
        elif args.dependencyType == 'prereq':
            items = DependencyUtils.prereq(
                PackageIdentifier.fromStringList(args.packages),
                pm.listAvailablePackages(),
                pm.listInstalledPackages(),
                env=env)
        elif args.dependencyType == 'upgrade':
            items, _uninstallList = DependencyUtils.upgrade(
                None if len(args.packages) == 0 else args.packages,
                pm.listAvailablePackages(),
                pm.listInstalledPackages(),
                env=env)
        else:
            raise ValueError()

        rend = ManifestListRenderer()
        rend.extend(items)
        pm.printRenderer(rend)


class PackageInstallCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'install',
            "install packages (download + extract)")

    @staticmethod
    def initInstallArguments(subparser):
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        PackageInstallCommand.initInstallArguments(parser)
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='identifier of packages to install')

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)

        try:
            items = pm.installFromRemotes(PackageIdentifier.fromStringList(args.packages),
                                          keepFolderOnError=args.keepOnError)
        except Exception as e:
            raise PackageInstallInterruptedException(args.packages, e)

        if len(items) > 0:
            pm.logger.printQuiet(
                "Packages installed:",
                ' '.join([str(p.getIdentifier()) for p in items]))


class PackagePrereqCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'prereq',
            "check prereq packages")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument("--target",
                            dest="prereqRootFolder",
                            type=Path,
                            help="a alternative root folder for required packages installation")
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='package identifier')

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)

        tmpRootFolder = args.prereqRootFolder
        if tmpRootFolder is None:
            tmpRootFolder = mkTmpLeafRootDir()
        pm.logger.printQuiet("Prereq root folder: %s" % tmpRootFolder)
        errorCount = pm.installPrereqFromRemotes(PackageIdentifier.fromStringList(args.packages),
                                                 tmpRootFolder,
                                                 raiseOnError=False)
        pm.logger.printQuiet("Prereq installed with %d error(s)" % errorCount)
        return errorCount


class PackageUninstallCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'uninstall',
            "remove packages")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='identifier of package to uninstall')

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)

        pm.uninstallPackages(PackageIdentifier.fromStringList(args.packages))


class PackageSyncCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'sync',
            "performs sync operation")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ONE_OR_MORE,
                            help='name of package to uninstall')

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)

        pm.syncPackages(PackageIdentifier.fromStringList(args.packages))


class PackageUpgradeCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'upgrade',
            "upgrade packages to latest version")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument("--clean",
                            dest="clean",
                            action='store_true',
                            help="also try to uninstall old versions of upgraded packages")
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ZERO_OR_MORE,
                            help='name of the packages to upgrade')

    def execute(self, args, uargs):
        pm = self.getPackageManager(args)

        env = Environment.build(
            pm.getBuiltinEnvironment(),
            pm.getUserEnvironment())
        installList, uninstallList = DependencyUtils.upgrade(
            None if len(args.packages) == 0 else args.packages,
            pm.listAvailablePackages(),
            pm.listInstalledPackages(),
            env=env)

        pm.logger.printVerbose("%d package(s) to be upgraded: %s" %
                               (len(installList), ' '.join([str(ap.getIdentifier()) for ap in installList])))
        if args.clean:
            pm.logger.printVerbose("%d package(s) to be removed: %s" %
                                   (len(uninstallList), ' '.join([str(ip.getIdentifier()) for ip in uninstallList])))

        if len(installList) == 0:
            pm.logger.printDefault("No package to upgrade")
        else:
            pm.installFromRemotes(
                map(Manifest.getIdentifier, installList), env=env)
            if len(uninstallList) > 0:
                if args.clean:
                    pm.uninstallPackages(
                        map(Manifest.getIdentifier, uninstallList))
                else:
                    pm.logger.printDefault(
                        "These packages can be removed:", " ".join([str(ip.getIdentifier()) for ip in uninstallList]))
