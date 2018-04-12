'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import argparse
from pathlib import Path

from leaf.cliutils import LeafCommand


class RepositoryCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "repository",
                             "commands to maintain a leaf repository",
                             cmdAliases=["repo"],
                             addVerboseQuiet=False)
        self.subCommands = [
            RepositoryPackSubCommand(),
            RepositoryIndexSubCommand()
        ]

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


class RepositoryPackSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "pack",
                             "create a package")

    def internalInitArgs(self, subparser):
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


class RepositoryIndexSubCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "index",
                             "build a repository index.json")

    def internalInitArgs(self, subparser):
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
