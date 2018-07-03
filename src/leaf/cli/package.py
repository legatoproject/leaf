'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from pathlib import Path

from leaf.cli.cliutils import LeafCommand, LeafMetaCommand
from leaf.core.dependencies import DependencyType
from leaf.model.filtering import MetaPackageFilter
from leaf.model.package import Manifest
from leaf.utils import mkTmpLeafRootDir, envListToMap
from leaf.format.manifestlistrenderer import ManifestListRenderer


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
        logger = self.getLogger(args)
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
        logger.printRenderer(rend)


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
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ONE_OR_MORE,
                            help='package name')

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getPackageManager(args)
        items = app.listDependencies(args.packages,
                                     args.dependencyType,
                                     envMap=envListToMap(args.customEnvList))
        for i in items:
            logger.displayItem(i)


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
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ONE_OR_MORE,
                            help='name of packages to install')

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getPackageManager(args)

        items = app.installFromRemotes(args.packages,
                                       keepFolderOnError=args.keepOnError)
        if len(items) > 0:
            logger.printQuiet("Packages installed: " +
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
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ONE_OR_MORE,
                            help='package name')

    def execute(self, args):
        logger = self.getLogger(args)
        app = self.getPackageManager(args)

        tmpRootFolder = args.prereqRootFolder
        if tmpRootFolder is None:
            tmpRootFolder = mkTmpLeafRootDir()
        logger.printQuiet("Prereq root folder: %s" % tmpRootFolder)
        errorCount = app.installPrereqFromRemotes(args.packages,
                                                  tmpRootFolder,
                                                  raiseOnError=False)
        logger.printQuiet("Prereq installed with %d error(s)" % errorCount)
        return errorCount


class PackageUninstallCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "uninstall",
                             "remove packages")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('packages', metavar='PKGNAME',
                            nargs=argparse.ONE_OR_MORE,
                            help='name of package to uninstall')

    def execute(self, args):
        app = self.getPackageManager(args)

        app.uninstallPackages(args.packages)
