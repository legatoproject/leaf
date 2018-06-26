'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import argparse
from leaf.cli.cliutils import LeafCommand, LeafMetaCommand
from leaf.core.relengmanager import RelengManager
from pathlib import Path


class RepositoryMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(
            self,
            "repository",
            "commands to maintain a leaf repository")

    def getSubCommands(self):
        return [RepositoryPackSubCommand(),
                RepositoryIndexSubCommand()]


class RepositoryPackSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "pack",
                             "create a package")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('-o',
                            metavar='FILE',
                            required=True,
                            type=Path,
                            dest='pack_output',
                            help='output file')
        parser.add_argument('manifest',
                            type=Path,
                            help='the manifest file to package')

    def execute(self, args):
        RelengManager(self.getLogger(args)).pack(args.manifest,
                                                 args.pack_output)


class RepositoryIndexSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "index",
                             "build a repository index.json")

    def initArgs(self, parser):
        super().initArgs(parser)
        parser.add_argument('-o',
                            metavar='FILE',
                            required=True,
                            type=Path,
                            dest='index_output',
                            help='output file')
        parser.add_argument('--name',
                            metavar='NAME',
                            dest='index_name',
                            help='name of the repository')
        parser.add_argument('--description',
                            metavar='STRING',
                            dest='index_description',
                            help='description of the repository')
        parser.add_argument('--composite',
                            dest='index_composites',
                            metavar='FILE',
                            action='append',
                            help='reference composite index file')
        parser.add_argument('artifacts',
                            type=Path,
                            nargs=argparse.REMAINDER,
                            help='leaf artifacts')

    def execute(self, args):
        RelengManager(self.getLogger(args)).index(args.index_output,
                                                  args.artifacts,
                                                  args.index_name,
                                                  args.index_description,
                                                  args.index_composites)
