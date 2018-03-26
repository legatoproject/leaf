'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import argparse
import json
from leaf.cli import LeafCli, LeafCommand
from leaf.cli_releng import PackCommand, IndexCommand
from leaf.constants import LeafFiles
from leaf.ui import filterPackageList
import os
import shutil


def main():
    return PackageManagerCli().run()


class PackageManagerCli (LeafCli):
    def __init__(self):
        LeafCli.__init__(self,
                         ConfigCommand(),
                         CleanCommand(),
                         RemoteCommand(),
                         FetchCommand(),
                         ListCommand(),
                         SearchCommand(),
                         DependsCommand(),
                         ExtractCommand(),
                         InstallCommand(),
                         RemoveCommand(),
                         EnvCommand(),
                         # Releng
                         PackCommand(),
                         IndexCommand())


class ConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "config",
                             "manage configuration")

    def internalInitArgs(self, subparser):
        subparser.add_argument('--root',
                               dest='root_folder',
                               metavar='DIR',
                               help="set the root folder, default: " + str(LeafFiles.DEFAULT_LEAF_ROOT))
        subparser.add_argument('--env',
                               dest='config_env',
                               action='append',
                               metavar='KEY=VALUE',
                               help="set custom env variables for exec steps")

    def internalExecute(self, app, logger, args):
        if args.root_folder is not None:
            app.updateConfiguration(rootFolder=args.root_folder)
        if args.config_env is not None:
            app.updateConfiguration(env=args.config_env)
        logger.printDefault("Configuration file:", app.configurationFile)
        logger.printDefault(json.dumps(app.readConfiguration(),
                                       sort_keys=True,
                                       indent=2,
                                       separators=(',', ': ')))


class CleanCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "clean",
                             "clean cache folder")

    def internalInitArgs(self, subparser):
        pass

    def internalExecute(self, app, logger, args):
        logger.printDefault("Clean cache folder: ",
                            LeafFiles.CACHE_FOLDER)
        shutil.rmtree(str(LeafFiles.FILES_CACHE_FOLDER), True)
        cacheFile = LeafFiles.REMOTES_CACHE_FILE
        if cacheFile.exists():
            os.remove(str(cacheFile))
        shutil.rmtree(str(LeafFiles.FILES_CACHE_FOLDER), True)


class RemoteCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "remote",
                             "manage remote repositories")

    def internalInitArgs(self, subparser):
        subparser.add_argument('--add',
                               dest='remote_add',
                               action='append',
                               metavar='URL',
                               help='add given remote url')
        subparser.add_argument('--rm',
                               dest='remote_rm',
                               action='append',
                               metavar='URL',
                               help='remove given remote url')

    def internalExecute(self, app, logger, args):
        if args.remote_add is not None:
            for url in args.remote_add:
                app.remoteAdd(url)
        if args.remote_rm is not None:
            for url in args.remote_rm:
                app.remoteRemove(url)
        if args.remote_add is None and args.remote_rm is None:
            for rr in app.getRemoteRepositories():
                if rr.isRootRepository or logger.isVerbose():
                    logger.displayItem(rr)


class FetchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "refresh",
                             "refresh remote repositories packages list",
                             commandAlias="f")

    def internalInitArgs(self, subparser):
        pass

    def internalExecute(self, app, logger, args):
        app.fetchRemotes()
        for rr in app.getRemoteRepositories():
            logger.displayItem(rr)


class ListCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "list",
                             "list installed packages",
                             commandAlias="ls")

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
        ipMap = app.listInstalledPackages()
        filteredIpList = filterPackageList(ipMap.values(),
                                           keywords=args.keywords,
                                           modules=args.modules)
        for pack in filteredIpList:
            if args.allPackages or pack.isMaster():
                logger.displayItem(pack)


class SearchCommand(LeafCommand):

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
        apMap = app.listAvailablePackages()
        filteredApList = filterPackageList(apMap.values(),
                                           keywords=args.keywords,
                                           modules=args.modules)
        for pack in filteredApList:
            if args.allPackages or (pack.isMaster() and pack.isSupportedOs()):
                logger.displayItem(pack)


class DependsCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "dependencies",
                             "Build the dependency chain",
                             commandAlias="deps")

    def internalInitArgs(self, subparser):
        subparser.add_argument("-r", "--reverse",
                               dest="reverseOrder",
                               action="store_true",
                               help="reverse order")
        subparser.add_argument("-i", "--filter-installed",
                               dest="filterInstalled",
                               action="store_true",
                               help="filter already installed packages")
        subparser.add_argument("--apt",
                               dest="aptDepends",
                               action="store_true",
                               help="display apt dependencies")
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.listDependencies(args.packages,
                                     reverse=args.reverseOrder,
                                     filterInstalled=args.filterInstalled,
                                     aptDepends=args.aptDepends)
        for i in items:
            logger.displayItem(i)


class ExtractCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "extract",
                             "extract given packages",
                             commandAlias="x")

    def internalInitArgs(self, subparser):
        InstallCommand.initInstallArguments(subparser)
        subparser.add_argument("--skip-depends",
                               dest="skipLeafDepends",
                               action="store_true",
                               help="extract packages without checking & installing leaf dependencies")
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.installFromFiles(args.packages,
                                     bypassSupportedOs=args.skipOsCompat,
                                     bypassLeafDepends=args.skipLeafDepends,
                                     bypassAptDepends=args.skipAptDepends,
                                     keepFolderOnError=args.keepOnError)
        logger.printQuiet("Package extracted: " +
                          ' '.join([str(p.getIdentifier()) for p in items]))


class InstallCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "install",
                             "install packages (download + extract)",
                             commandAlias="i")

    @staticmethod
    def initInstallArguments(subparser):
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")
        subparser.add_argument("--accept-licenses",
                               dest="skipLicenses",
                               action="store_true",
                               help="automatically accept all licenses")
        subparser.add_argument("--skip-apt",
                               dest="skipAptDepends",
                               action="store_true",
                               help="do not check apt dependencies")
        subparser.add_argument("--skip-compat",
                               dest="skipOsCompat",
                               action="store_true",
                               help="do not check if package are compatible with current OS")

    def internalInitArgs(self, subparser):
        InstallCommand.initInstallArguments(subparser)
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.installFromRemotes(args.packages,
                                       bypassSupportedOs=args.skipOsCompat,
                                       bypassAptDepends=args.skipAptDepends,
                                       keepFolderOnError=args.keepOnError)
        logger.printQuiet("Package installed: " +
                          ' '.join([str(p.getIdentifier()) for p in items]))


class RemoveCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "remove",
                             "remove packages",
                             commandAlias="rm")

    def internalInitArgs(self, subparser):
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        app.uninstallPackages(args.packages)


class EnvCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "env",
                             "display environment variables exported by packages")

    def internalInitArgs(self, subparser):
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        for t in app.getEnv(args.packages):
            logger.displayItem(t)
