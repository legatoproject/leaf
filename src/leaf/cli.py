'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from argparse import RawDescriptionHelpFormatter, ArgumentParser
import argparse
import json
from leaf import __version__, __help_description__
from leaf.constants import LeafConstants, LeafFiles
from leaf.core import LeafApp, JsonLogger, QuietLogger, VerboseLogger
from leaf.model import Manifest
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
    return PackageManagerCli().execute()


class PackageManagerCli():

    _ACTION_CONFIG = 'config'
    _ACTION_REMOTE = 'remote'
    _ACTION_LIST = 'list'
    _ACTION_REFRESH = 'refresh'
    _ACTION_SEARCH = 'search'
    _ACTION_INSTALL = 'install'
    _ACTION_REMOVE = 'remove'
    _ACTION_ENV = 'env'
    _ACTION_PACK = 'pack'
    _ACTION_INDEX = 'index'
    _ACTION_CLEAN = 'clean'
    _ACTION_ALIASES = {
        _ACTION_LIST: ['ls'],
        _ACTION_REMOVE: ['rm'],
        _ACTION_INSTALL: ['i']
    }

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

        def newParser(action, command_help):
            out = subparsers.add_parser(action,
                                        help=command_help,
                                        aliases=PackageManagerCli._ACTION_ALIASES.get(action, []))
            out.add_argument("-v", "--verbose",
                             dest="verbose",
                             action='count',
                             help="increase output verbosity")
            return out

        # CONFIG
        subparser = newParser(
            PackageManagerCli._ACTION_CONFIG, "manage configuration")
        subparser.add_argument('--root',
                               dest='root_folder',
                               metavar='DIR',
                               help="set the root folder, default: " + str(LeafFiles.DEFAULT_LEAF_ROOT))
        subparser.add_argument('--env',
                               dest='config_env',
                               action='append',
                               metavar='KEY=VALUE',
                               help="set custom env variables for exec steps")

        # CLEAN
        subparser = newParser(
            PackageManagerCli._ACTION_CLEAN, "clean cache folder")

        # REMOTE
        subparser = newParser(PackageManagerCli._ACTION_REMOTE,
                              "manage remote repositories")
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

        # FETCH
        subparser = newParser(PackageManagerCli._ACTION_REFRESH,
                              "refresh remote repositories packages list")

        # LIST
        subparser = newParser(
            PackageManagerCli._ACTION_LIST, "list installed packages")
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument("-m", "--module",
                               dest="modules",
                               action="append",
                               metavar="MODULE",
                               help="filter packages supporting given module")
        subparser.add_argument('keywords', nargs=argparse.ZERO_OR_MORE)

        # SEARCH
        subparser = newParser(PackageManagerCli._ACTION_SEARCH,
                              "search for available packages")
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument("-m", "--module",
                               dest="modules",
                               action="append",
                               metavar="MODULE",
                               help="filter packages supporting given module")
        subparser.add_argument('keywords', nargs=argparse.ZERO_OR_MORE)

        # INSTALL
        subparser = newParser(PackageManagerCli._ACTION_INSTALL,
                              "install packages")
        subparser.add_argument("--skip-licenses",
                               dest="skipLicenses",
                               action="store_true",
                               help="skip license display and accept, assume yes")
        subparser.add_argument('-f', "--force",
                               dest="force",
                               action="store_true",
                               help="force installation in case of warnings")
        subparser.add_argument('-d', "--download-only",
                               dest="downloadOnly",
                               action="store_true",
                               help="only download artifacts in cache, do not install them")
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

        # REMOVE
        subparser = newParser(PackageManagerCli._ACTION_REMOVE,
                              "remove packages")
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

        # ENV
        subparser = newParser(PackageManagerCli._ACTION_ENV,
                              "display environment variables exported by packages")
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

        # PACK
        subparser = newParser(PackageManagerCli._ACTION_PACK,
                              "create a package")
        subparser.add_argument('-o',
                               metavar='FILE',
                               required=True,
                               type=Path,
                               dest='pack_output',
                               help='output file')
        subparser.add_argument('manifest',
                               type=Path,
                               help='the manifest file to package')

        # INDEX
        subparser = newParser(PackageManagerCli._ACTION_INDEX,
                              "build a repository index.json")
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

    def execute(self, argv=None):
        '''
        Entry point
        '''

        if argv is None:
            argv = sys.argv
        else:
            sys.argv.extend(argv)

        try:
            # Process arguments
            args = self.parser.parse_args()
            logger = VerboseLogger() if args.verbose else QuietLogger()
            if args.json:
                logger = JsonLogger()

            configFile = LeafFiles.DEFAULT_CONFIG_FILE
            if args.customConfig is not None:
                configFile = args.customConfig

            app = LeafApp(logger, configFile)

            action = args.command
            for k, v in PackageManagerCli._ACTION_ALIASES.items():
                if action in v:
                    action = k
                    break
            if action == PackageManagerCli._ACTION_CONFIG:
                if args.root_folder is not None:
                    app.updateConfiguration(rootFolder=args.root_folder)
                if args.config_env is not None:
                    app.updateConfiguration(env=args.config_env)
                logger.printMessage("Configuration file:",
                                    app.configurationFile)
                logger.printMessage(json.dumps(app.readConfiguration(),
                                               sort_keys=True,
                                               indent=2,
                                               separators=(',', ': ')))
            elif action == PackageManagerCli._ACTION_CLEAN:
                logger.printMessage(
                    "Clean cache folder: ", LeafFiles.CACHE_FOLDER)
                shutil.rmtree(str(LeafFiles.FILES_CACHE_FOLDER), True)
                cacheFile = LeafFiles.REMOTES_CACHE_FILE
                if cacheFile.exists():
                    os.remove(str(cacheFile))
                shutil.rmtree(str(LeafFiles.FILES_CACHE_FOLDER), True)
            elif action == PackageManagerCli._ACTION_REMOTE:
                if args.remote_add is not None:
                    for url in args.remote_add:
                        app.remoteAdd(url)
                if args.remote_rm is not None:
                    for url in args.remote_rm:
                        app.remoteRemove(url)
                for url, info in app.remoteList().items():
                    logger.displayRemote(url, info)
            elif action == PackageManagerCli._ACTION_REFRESH:
                app.fetchRemotes()
            elif action == PackageManagerCli._ACTION_LIST:
                for pack in self.filterPackageList(app.listInstalledPackages().values(), keywords=args.keywords, modules=args.modules):
                    if args.allPackages or pack.isMaster():
                        logger.displayPackage(pack)
            elif action == PackageManagerCli._ACTION_SEARCH:
                for pack in self.filterPackageList(app.listAvailablePackages().values(), args.keywords, args.modules):
                    if args.allPackages or (pack.isMaster() and pack.isSupported()):
                        logger.displayPackage(pack)
            elif action == PackageManagerCli._ACTION_INSTALL:
                app.install(args.packages,
                            downloadOnly=args.downloadOnly,
                            forceInstall=args.force,
                            keepFolderOnError=args.keepOnError,
                            skipLicenses=args.skipLicenses)
            elif action == PackageManagerCli._ACTION_REMOVE:
                app.uninstall(args.packages)
            elif action == PackageManagerCli._ACTION_ENV:
                for k, v in app.getEnv(args.packages).items():
                    logger.printMessage('export %s="%s"' % (k, v))
            elif action == PackageManagerCli._ACTION_PACK:
                app.pack(args.manifest, args.pack_output)
            elif action == PackageManagerCli._ACTION_INDEX:
                app.index(args.index_output,
                          args.artifacts,
                          args.index_name,
                          args.index_description,
                          args.index_composites)

            return 0
        except KeyboardInterrupt:
            ### handle keyboard interrupt ###
            return 1
        except Exception as e:
            if args.verbose:
                raise e
            logger.printError(e, exception=e)
            return 2

    def filterPackageList(self, content, keywords=None, modules=None, sort=True):
        '''
        Filter a list of packages given optional criteria
        '''
        out = list(content)

        def my_filter(p):
            out = True
            if modules is not None and len(modules) > 0:
                out = False
                if p.getSupportedModules() is not None:
                    for m in modules:
                        if m.lower() in map(str.lower, p.getSupportedModules()):
                            out = True
                            break
            if out and keywords is not None and len(keywords) > 0:
                out = False
                for k in keywords:
                    k = k.lower()
                    if k in str(p.getIdentifier()).lower():
                        out = True
                        break
                    if p.getDescription() is not None and k in p.getDescription().lower():
                        out = True
                        break
            return out
        out = filter(my_filter, out)
        if sort:
            out = sorted(out, key=Manifest.getIdentifier)
        return out
