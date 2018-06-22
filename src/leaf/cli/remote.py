'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.cli.cliutils import LeafMetaCommand, LeafCommand


class RemoteMetaCommand(LeafMetaCommand):

    def __init__(self):
        LeafMetaCommand.__init__(
            self,
            "remote",
            "display and manage remote repositories")

    def getDefaultSubCommand(self):
        return RemoteListCommand()

    def getSubCommands(self):
        return [RemoteAddCommand(),
                RemoteRemoveCommand(),
                RemoteEnableCommand(),
                RemoteDisableCommand(),
                RemoteFetchCommand()]


class RemoteListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            "list",
            "list remote repositories")

    def execute(self, args):
        logger = self.getLogger(args)
        for remote in self.getApp(args, logger).getRemotes():
            logger.displayItem(remote)


class RemoteAddCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            "add",
            "add a remote repository")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)
        parser.add_argument('alias', metavar='ALIAS', nargs=1,
                            help='the alias of the new remote')
        parser.add_argument('url', metavar='URL', nargs=1,
                            help='the remote URL (supported url schemes: http(s)://, file://)')

    def execute(self, args):
        logger = self.getLogger(args)
        self.getApp(args, logger).addRemote(args.alias[0], args.url[0])


class RemoteRemoveCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            "remove",
            "remove a remote repository")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)
        parser.add_argument('alias', metavar='ALIAS', nargs=1,
                            help='the alias of the remote to remove')

    def execute(self, args):
        logger = self.getLogger(args)
        self.getApp(args, logger).removeRemote(args.alias[0])


class RemoteEnableCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            "enable",
            "enable a remote repository")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)
        parser.add_argument('alias', metavar='ALIAS', nargs=1,
                            help='the alias of the remote to enable')

    def execute(self, args):
        logger = self.getLogger(args)
        self.getApp(args, logger).updateRemote(args.alias[0], enabled=True)


class RemoteDisableCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            "disable",
            "disable a remote repository")

    def initArgs(self, parser):
        LeafCommand.initArgs(self, parser)
        parser.add_argument('alias', metavar='ALIAS', nargs=1,
                            help='the alias of the remote to disable')

    def execute(self, args):
        logger = self.getLogger(args)
        self.getApp(args, logger).updateRemote(args.alias[0], enabled=False)


class RemoteFetchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(self,
                             "fetch",
                             "fetch content from enabled remotes")

    def execute(self, args):
        self.getApp(args).fetchRemotes(smartRefresh=False)
