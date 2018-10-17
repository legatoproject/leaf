'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import argparse
import time
from builtins import ValueError
from pathlib import Path

from leaf.cli.cliutils import LeafCommand, LeafMetaCommand, stringToBoolean
from leaf.constants import JsonConstants, LeafFiles
from leaf.core.relengmanager import RelengManager
from leaf.utils import TAR_COMPRESSIONS


class RepositoryMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(
            self,
            "repository",
            "commands to maintain a leaf repository")

    def getSubCommands(self):
        return [RepositoryPackSubCommand(),
                RepositoryIndexSubCommand(),
                RepositoryManifestSubCommand()]


class RepositoryPackSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "pack",
                             "create a package")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('-o', '--output',
                            metavar='FILE',
                            required=True,
                            type=Path,
                            dest='outputFile',
                            help='output file')
        parser.add_argument('--no-info',
                            action='store_false',
                            dest='storeExtenalInfo',
                            help='do not store artifact info in a separate file')
        parser.add_argument('--compression',
                            metavar='COMPRESSION',
                            dest='compression',
                            choices=TAR_COMPRESSIONS,
                            help='configure compression (%s)' % (
                                '|'.join(TAR_COMPRESSIONS)))
        parser.add_argument('--timestamp',
                            metavar='TIMESTAMP',
                            type=float,
                            dest='timestamp',
                            help='force the timestamp for files in the generated tar archive (current: %lf)' % (time.time()))
        parser.add_argument('--root-owner',
                            action='store_true',
                            dest='root_owner',
                            help='force root as user/group in the generated tar file')

        parser.add_argument('pkgFolder',
                            metavar='PKGFOLDER',
                            nargs='?',
                            type=Path,
                            help='the package folder (if no specified, use current directory)')

    def execute(self, args):
        loggerAttr = self.getLoggerAttr(args)
        rm = RelengManager(loggerAttr[0], loggerAttr[1])

        pkgFolder = None
        if args.pkgFolder is None:
            pkgFolder = Path('.')
        elif args.pkgFolder.is_dir():
            pkgFolder = args.pkgFolder
        elif args.pkgFolder.is_file() and args.pkgFolder.name == LeafFiles.MANIFEST:
            # Handles legacy, arg is not the folder but the manifest
            pkgFolder = args.pkgFolder.parent

        rm.createPackage(pkgFolder, args.outputFile,
                         storeExtenalInfo=args.storeExtenalInfo,
                         forceTimestamp=args.timestamp,
                         compression=args.compression,
                         forceRootOwner=args.root_owner)


class RepositoryIndexSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "index",
                             "build a repository index.json")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('-o', '--output',
                            required=True,
                            metavar='FILE',
                            type=Path,
                            dest='outputFile',
                            help='the new json index file')
        parser.add_argument('--name',
                            metavar='NAME',
                            dest='index_name',
                            help='name of the repository')
        parser.add_argument('--description',
                            metavar='STRING',
                            dest='index_description',
                            help='description of the repository')
        parser.add_argument('--no-info',
                            action='store_false',
                            dest='useExternalInfo',
                            help='do not use info files (*.info), THIS MAY SLOW THE INDEX GENERATION')
        parser.add_argument('--no-extra-tags',
                            action='store_false',
                            dest='useExtraTags',
                            help='do not use extra tags in "*.tags" files')
        parser.add_argument('--prettyprint',
                            action='store_true',
                            dest='prettyprint',
                            help='pretty print json')
        parser.add_argument('artifacts',
                            type=Path,
                            nargs=argparse.REMAINDER,
                            help='leaf artifacts')

    def execute(self, args):
        loggerAttr = self.getLoggerAttr(args)
        rm = RelengManager(loggerAttr[0], loggerAttr[1])
        rm.generateIndex(args.outputFile,
                         args.artifacts,
                         name=args.index_name,
                         description=args.index_description,
                         useExternalInfo=args.useExternalInfo,
                         useExtraTags=args.useExtraTags,
                         prettyprint=args.prettyprint)


class RepositoryManifestSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "manifest",
                             "build a package manifest.json")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('-o', '--output',
                            metavar='FOLDER',
                            type=Path,
                            dest='outputFolder',
                            help='folder where the manifest.json will be generated')
        parser.add_argument('--append',
                            metavar='JSON_FILE',
                            action='append',
                            type=Path,
                            dest='fragmentFiles',
                            help='json fragment that will be added to generated manifest')
        parser.add_argument('--env',
                            action='store_true',
                            dest='resolveEnvVariables',
                            help='use environment variables to perform string replacement')

        commonGroup = parser.add_argument_group(
            title='Setup common attributes')
        commonGroup.add_argument('--name',
                                 metavar='NAME',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_NAME,
                                 help='set the package name')
        commonGroup.add_argument('--version',
                                 metavar='VERSION',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_VERSION,
                                 help='set the package version')
        commonGroup.add_argument('--description',
                                 metavar='DESCRIPTION',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_DESCRIPTION,
                                 help='set the package description')
        commonGroup.add_argument('--date',
                                 metavar='DATE',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_DATE,
                                 help='set the date')
        commonGroup.add_argument('--minver',
                                 metavar='MINIMUM_VERSION',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_LEAF_MINVER,
                                 help='set leaf minimum version to use the package')
        commonGroup.add_argument('--master',
                                 metavar='BOOLEAN',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_MASTER,
                                 type=stringToBoolean,
                                 help='set master package (true|false)')
        commonGroup.add_argument('--requires',
                                 metavar='PKGID',
                                 action='append',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_REQUIRES,
                                 help='add a required package')
        commonGroup.add_argument('--depends',
                                 metavar='PKGID',
                                 action='append',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_DEPENDS,
                                 help='add a dependency package')
        commonGroup.add_argument('--tag',
                                 metavar='TAG',
                                 action='append',
                                 dest=JsonConstants.INFO + "_" + JsonConstants.INFO_TAGS,
                                 help='add a tag')

    def execute(self, args):
        loggerAttr = self.getLoggerAttr(args)
        rm = RelengManager(loggerAttr[0], loggerAttr[1])

        # Guess output file
        outputFile = LeafFiles.MANIFEST
        if args.outputFolder is not None:
            if not args.outputFolder.is_dir():
                raise ValueError("Invalid output folder: " % args.outputFolder)
            outputFile = args.outputFolder / LeafFiles.MANIFEST

        # Build the info map
        infoMap = {}
        for k, v in vars(args).items():
            if k.startswith(JsonConstants.INFO + "_"):
                infoMap[k[(len(JsonConstants.INFO) + 1):]] = v

        rm.generateManifest(outputFile,
                            fragmentFiles=args.fragmentFiles,
                            infoMap=infoMap,
                            resolveEnvVariables=args.resolveEnvVariables)
