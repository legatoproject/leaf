'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import argparse
import json
from leaf import __help_description__, __version__
from leaf.constants import LeafFiles, LeafConstants
from leaf.core import LeafApp
from leaf.logger import createLogger
from leaf.ui import filterPackageList
import os
from pathlib import Path
import shutil
import sys


def run():
    # Check python version
    currentPythonVersion = sys.version_info
    if (currentPythonVersion[0], currentPythonVersion[1]) < LeafConstants.MIN_PYTHON_VERSION:
        print(
            'Unsupported Python version, please use at least Python %d.%d.' % LeafConstants.MIN_PYTHON_VERSION,
            file=sys.stderr)
        sys.exit(1)
    return PackageManagerCli().execute(sys.argv[1:])


class LeafCommand():
    '''
    Abstract class to define parser for leaf commands
    '''

    def __init__(self, commandName, commandHelp, commandAlias=None):
        self.commandName = commandName
        self.commandHelp = commandHelp
        self.commandAlias = commandAlias

    def isHandled(self, cmd):
        return cmd == self.commandName or cmd == self.commandAlias

    def create(self, subparsers):
        parser = subparsers.add_parser(self.commandName,
                                       help=self.commandHelp,
                                       aliases=[] if self.commandAlias is None else [self.commandAlias])
        self.initArguments(parser)

    def initArguments(self, subparser):
        subparser.add_argument("-v", "--verbose",
                               dest="verbose",
                               action='store_true',
                               help="increase output verbosity")
        subparser.add_argument("-q", "--quiet",
                               dest="quiet",
                               action='store_true',
                               help="decrease output verbosity")

    def execute(self, app, logger, args):
        out = self.internalExecute(app, logger, args)
        return 0 if out is None else out


class ConfigCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "config",
                             "manage configuration")

    def initArguments(self, subparser):
        super().initArguments(subparser)
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

    def initArguments(self, subparser):
        super().initArguments(subparser)
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
        for rr in app.getRemoteRepositories():
            logger.displayItem(rr)


class FetchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "refresh",
                             "refresh remote repositories packages list",
                             commandAlias="f")

    def internalExecute(self, app, logger, args):
        for rr in app.fetchRemotes():
            logger.displayItem(rr)


class ListCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "list",
                             "list installed packages",
                             commandAlias="ls")

    def initArguments(self, subparser):
        super().initArguments(subparser)
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

    def initArguments(self, subparser):
        super().initArguments(subparser)
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
            if args.allPackages or (pack.isMaster() and pack.isSupported()):
                logger.displayItem(pack)


class DependsCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "dependencies",
                             "Build the dependency chain",
                             commandAlias="deps")

    def initArguments(self, subparser):
        super().initArguments(subparser)
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


class DownloadCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "download",
                             "Download the packages into the cache folder",)

    def initArguments(self, subparser):
        super().initArguments(subparser)
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.downloadPackages(args.packages).values()
        for i in items:
            logger.displayItem(i)


class ExtractCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "extract",
                             "extract given packages",
                             commandAlias="x")

    def initArguments(self, subparser):
        super().initArguments(subparser)
        InstallCommand.initInstallArguments(subparser)
        subparser.add_argument("--skip-depends",
                               dest="skipLeafDepends",
                               action="store_true",
                               help="extract packages without checking & installing leaf dependencies")
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.extractPackages(args.packages,
                                    bypassSupportedOsCheck=args.skipOsCompat,
                                    bypassLeafDependsCheck=args.skipLeafDepends,
                                    bypassAptDependsCheck=args.skipAptDepends,
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

    def initArguments(self, subparser):
        super().initArguments(subparser)
        InstallCommand.initInstallArguments(subparser)
        subparser.add_argument('packages',
                               nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        items = app.installPackages(args.packages,
                                    bypassSupportedOsCheck=args.skipOsCompat,
                                    bypassAptDependsCheck=args.skipAptDepends,
                                    keepFolderOnError=args.keepOnError)
        logger.printQuiet("Package installed: " +
                          ' '.join([str(p.getIdentifier()) for p in items]))


class RemoveCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "remove",
                             "remove packages",
                             commandAlias="rm")

    def initArguments(self, subparser):
        super().initArguments(subparser)
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        app.uninstallPackages(args.packages)


class EnvCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "env",
                             "display environment variables exported by packages")

    def initArguments(self, subparser):
        super().initArguments(subparser)
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

    def internalExecute(self, app, logger, args):
        for k, v in app.getEnv(args.packages).items():
            logger.printQuiet('export %s="%s"' % (k, v))


class PackCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "pack",
                             "create a package")

    def initArguments(self, subparser):
        super().initArguments(subparser)
        subparser.add_argument('-o',
                               metavar='FILE',
                               required=True,
                               type=Path,
                               dest='pack_output',
                               help='output file')
        subparser.add_argument('manifest',
                               type=Path,
                               help='the manifest file to package')

    def internalExecute(self, app, logger, args):
        app.pack(args.manifest, args.pack_output)


class IndexCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "index",
                             "build a repository index.json")

    def initArguments(self, subparser):
        super().initArguments(subparser)
        subparser.add_argument('-o',
                               metavar='FILE',
                               required=True,
                               type=Path,
                               dest='index_output',
                               help='output file')
        subparser.add_argument('--name',
                               metavar='NAME',
                               dest='index_name',
                               help='name of the repository')
        subparser.add_argument('--description',
                               metavar='STRING',
                               dest='index_description',
                               help='description of the repository')
        subparser.add_argument('--composite',
                               dest='index_composites',
                               metavar='FILE',
                               action='append',
                               help='reference composite index file')
        subparser.add_argument('artifacts',
                               type=Path,
                               nargs=argparse.REMAINDER,
                               help='leaf artifacts')

    def internalExecute(self, app, logger, args):
        app.index(args.index_output,
                  args.artifacts,
                  args.index_name,
                  args.index_description,
                  args.index_composites)


class PackageManagerCli():

    def __init__(self):
        # Setup argument parser
        self.parser = ArgumentParser(description=__help_description__,
                                     formatter_class=RawDescriptionHelpFormatter)

        self.parser.add_argument("--json",
                                 dest="json",
                                 action="store_true",
                                 help="output json format")
        self.parser.add_argument('-V', '--version',
                                 action='version',
                                 version="v%s" % __version__)
        self.parser.add_argument("--config",
                                 metavar='CONFIG_FILE',
                                 dest="customConfig",
                                 type=Path,
                                 help="use custom configuration file")

        subparsers = self.parser.add_subparsers(dest='command',
                                                description='supported commands',
                                                metavar="COMMAND",
                                                help='actions to execute')
        subparsers.required = True

        self.commands = []
        for cmdCls in LeafCommand.__subclasses__():
            command = cmdCls()
            command.create(subparsers)
            self.commands.append(command)

    def execute(self, args0):
        args = self.parser.parse_args(args0)
        logger = createLogger(args.verbose, args.quiet, args.json)

        configFile = LeafFiles.DEFAULT_CONFIG_FILE
        if args.customConfig is not None:
            configFile = args.customConfig

        app = LeafApp(logger, configFile)
        for cmd in self.commands:
            if cmd.isHandled(args.command):
                return cmd.execute(app, logger, args)
        raise ValueError("Cannot find command for " + args.command)
