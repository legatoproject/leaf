'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import argparse
from leaf.cliutils import LeafCommand
from leaf.coreutils import TagManager
from leaf.filtering import AndPackageFilter, MasterPackageFilter, \
    KeywordPackageFilter, ModulePackageFilter
from leaf.model import Manifest
from leaf.utils import mkTmpLeafRootDir
from pathlib import Path


class RemotesCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "remotes",
                             "display informations about remotes")

    def internalInitArgs(self, subparser):
        pass

    def internalExecute(self, app, logger, args):
        rrList = app.getRemoteRepositories(smartRefresh=False)
        for rr in rrList:
            if rr.isRootRepository:
                logger.displayItem(rr)


class PackageSearchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "search",
                             "search for available packages")

    def internalInitArgs(self, subparser):
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument("-m", "--module",
                               dest="modules",
                               action="append",
                               metavar="MODULE",
                               help="filter packages supporting given module")
        subparser.add_argument('keywords',
                               nargs=argparse.ZERO_OR_MORE)

    def internalExecute(self, app, logger, args):
        pkgFilter = AndPackageFilter()
        if not args.allPackages:
            pkgFilter.addFilter(MasterPackageFilter())
            pass

        if args.modules is not None:
            logger.printDefault("Filter by modules:",
                                ", ".join(args.modules))
            pkgFilter.addFilter(ModulePackageFilter(args.modules))

        if args.keywords is not None and len(args.keywords) > 0:
            logger.printDefault("Filter by keywords:",
                                ", ".join(args.keywords))
            pkgFilter.addFilter(KeywordPackageFilter(args.keywords))

        # Pkg list
        mfList = sorted(app.listAvailablePackages().values(),
                        key=Manifest.getIdentifier)
        # manage tags
        TagManager().tagLatest(mfList)
        TagManager().tagInstalled(mfList, app.listInstalledPackages().keys())

        # Print filtered packages
        for mf in mfList:
            if pkgFilter.matches(mf):
                logger.displayItem(mf)


class PackageCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "package",
                             "core package manager commands",
                             cmdAliases=["pkg"],
                             addVerboseQuiet=False)
        self.subCommands = [
            PackageListSubCommand(),
            PackageRefreshSubCommand(),
            PackageInstallSubCommand(),
            PackageRemoveSubCommand(),
            PackageEnvSubCommand(),
            PackageDependsSubCommand(),
            PackagePrereqSubCommand()]

    def internalInitArgs(self, subparser):
        subsubparsers = subparser.add_subparsers(dest='subCommand',
                                                 description='supported subcommands',
                                                 metavar="SUBCOMMAND",
                                                 help='actions to execute')
        subsubparsers.required = True
        for subCommand in self.subCommands:
            subCommand.create(subsubparsers)

    def internalExecute(self, app, logger, args):
        for subCommand in self.subCommands:
            if subCommand.isHandled(args.subCommand):
                return subCommand.execute(app, logger, args)
        raise ValueError("Cannot find subcommand for %s" % args.subcommand)


class PackageRefreshSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "refresh",
                             "refresh remote repositories packages list",
                             cmdAliases=["f"])

    def internalInitArgs(self, subparser):
        pass

    def internalExecute(self, app, logger, args):
        app.fetchRemotes()


class PackageListSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "list",
                             "list installed packages",
                             cmdAliases=["ls"])

    def internalInitArgs(self, subparser):
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument("-m", "--module",
                               dest="modules",
                               action="append",
                               metavar="MODULE",
                               help="filter packages supporting given module")
        subparser.add_argument('keywords',
                               nargs=argparse.ZERO_OR_MORE)

    def internalExecute(self, app, logger, args):
        pkgFilter = AndPackageFilter()
        if not args.allPackages:
            pkgFilter.addFilter(MasterPackageFilter())
            pass

        if args.modules is not None:
            logger.printDefault("Filter by modules:",
                                ", ".join(args.modules))
            pkgFilter.addFilter(ModulePackageFilter(args.modules))

        if args.keywords is not None and len(args.keywords) > 0:
            logger.printDefault("Filter by keywords:",
                                ", ".join(args.keywords))
            pkgFilter.addFilter(KeywordPackageFilter(args.keywords))

        # Print filtered packages
        for mf in sorted(app.listInstalledPackages().values(),
                         key=Manifest.getIdentifier):
            if pkgFilter.matches(mf):
                logger.displayItem(mf)


class PackageDependsSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "dependencies",
                             "Build the dependency chain",
                             cmdAliases=["deps"])

    def internalInitArgs(self, subparser):
        subparser.add_argument("-r", "--reverse",
                               dest="reverseOrder",
                               action="store_true",
                               help="reverse order")
        subparser.add_argument("-i", "--filter-installed",
                               dest="filterInstalled",
                               action="store_true",
                               help="filter already installed packages")
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.listDependencies(args.packages,
                                     reverse=args.reverseOrder,
                                     filterInstalled=args.filterInstalled)
        for i in items:
            logger.displayItem(i)


class PackageInstallSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "install",
                             "install packages (download + extract)",
                             cmdAliases=["i"])

    @staticmethod
    def initInstallArguments(subparser):
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")

    def internalInitArgs(self, subparser):
        PackageInstallSubCommand.initInstallArguments(subparser)
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.installFromRemotes(args.packages,
                                       keepFolderOnError=args.keepOnError)
        if len(items) > 0:
            logger.printQuiet("Packages installed: " +
                              ' '.join([str(p.getIdentifier()) for p in items]))


class PackagePrereqSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "prereq",
                             "check prereq packages")

    def internalInitArgs(self, subparser):
        subparser.add_argument("--target",
                               dest="prereqRootFolder",
                               type=Path,
                               help="a alternative root folder for required packages installation")
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        tmpRootFolder = args.prereqRootFolder
        if tmpRootFolder is None:
            tmpRootFolder = mkTmpLeafRootDir()
        logger.printQuiet("Prereq root folder: %s" % tmpRootFolder)
        errorCount = app.installPrereqFromRemotes(args.packages,
                                                  tmpRootFolder,
                                                  raiseOnError=False)
        logger.printQuiet("Prereq installed with %d error(s)" % errorCount)
        return errorCount


class PackageRemoveSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "remove",
                             "remove packages",
                             cmdAliases=["rm"])

    def internalInitArgs(self, subparser):
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        app.uninstallPackages(args.packages)


class PackageEnvSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "env",
                             "display environment variables exported by packages")

    def internalInitArgs(self, subparser):
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        env = app.getPackageEnv(args.packages)
        logger.displayItem(env)
