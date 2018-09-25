'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from pathlib import Path

from leaf.cli.cliutils import LeafCommand, LeafMetaCommand
from leaf.core.dependencies import DependencyType
from leaf.core.error import PackageInstallInterruptedException
from leaf.format.renderer.manifest import ManifestListRenderer
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import Manifest, PackageIdentifier
from leaf.utils import envListToMap, mkTmpLeafRootDir


class PackageMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(self,
                                 "package",
                                 "core package manager commands")

    def getDefaultSubCommand(self):
        return PackageListCommand()

    def getSubCommands(self):
        return [PackageInstallCommand(),
                PackageUninstallCommand(),
                PackageSyncCommand(),
                PackageDepsCommand(),
                PackagePrereqCommand()]


class PackageListCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "list",
                             "list installed packages")

    def initArgs(self, parser):
        super().initArgs(parser)
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

    def execute(self, args):
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
        LeafCommand.__init__(self,
                             "deps",
                             "Build the dependency chain")

    def initArgs(self, parser):
        super().initArgs(parser)
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--installed",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.INSTALLED,
                           default=DependencyType.INSTALLED,
                           help="build dependency list from installed packages")
        group.add_argument("--available",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.AVAILABLE,
                           help="build dependency list from available packages")
        group.add_argument("--install",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.INSTALL,
                           help="build dependency list to install")
        group.add_argument("--uninstall",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.UNINSTALL,
                           help="build dependency list to uninstall")
        group.add_argument("--prereq",
                           dest="dependencyType",
                           action="store_const",
                           const=DependencyType.PREREQ,
                           help="build dependency list for prereq install")
        parser.add_argument('--env',
                            dest='customEnvList',
                            action='append',
                            metavar='KEY=VALUE',
                            help='add given environment variable')
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='package identifier')

    def execute(self, args):
        pm = self.getPackageManager(args)

        items = pm.listDependencies(PackageIdentifier.fromStringList(args.packages),
                                    args.dependencyType,
                                    envMap=envListToMap(args.customEnvList))
        rend = ManifestListRenderer()
        rend.extend(items)
        pm.printRenderer(rend)


class PackageInstallCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "install",
                             "install packages (download + extract)")

    @staticmethod
    def initInstallArguments(subparser):
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")

    def initArgs(self, parser):
        super().initArgs(parser)
        PackageInstallCommand.initInstallArguments(parser)
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='identifier of packages to install')

    def execute(self, args):
        pm = self.getPackageManager(args)

        try:
            items = pm.installFromRemotes(PackageIdentifier.fromStringList(args.packages),
                                          keepFolderOnError=args.keepOnError)
        except Exception as e:
            raise PackageInstallInterruptedException(args.packages, e)

        if len(items) > 0:
            pm.logger.printQuiet("Packages installed: " +
                                 ' '.join([str(p.getIdentifier()) for p in items]))


class PackagePrereqCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "prereq",
                             "check prereq packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument("--target",
                            dest="prereqRootFolder",
                            type=Path,
                            help="a alternative root folder for required packages installation")
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='package identifier')

    def execute(self, args):
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
        LeafCommand.__init__(self,
                             "uninstall",
                             "remove packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('packages', metavar='PKG_IDENTIFIER',
                            nargs=argparse.ONE_OR_MORE,
                            help='identifier of package to uninstall')

    def execute(self, args):
        pm = self.getPackageManager(args)

        pm.uninstallPackages(PackageIdentifier.fromStringList(args.packages))


class PackageSyncCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "sync",
                             "performs sync operation")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ONE_OR_MORE,
                            help='name of package to uninstall')

    def execute(self, args):
        pm = self.getPackageManager(args)

        pm.syncPackages(PackageIdentifier.fromStringList(args.packages))
