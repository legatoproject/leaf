'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.api import PackageManager
from leaf.cli.cliutils import LeafCommand
from leaf.core.error import LeafException
from leaf.rendering.renderer.remote import RemoteListRenderer


class RemoteListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'list',
            "list remote repositories")

    def execute(self, args, uargs):
        pm = PackageManager()

        rend = RemoteListRenderer()
        rend.extend(pm.listRemotes().values())
        pm.printRenderer(rend)


class RemoteAddCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'add',
            "add a remote repository")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('alias', metavar='ALIAS', nargs=1,
                            help='the alias of the new remote')
        parser.add_argument('url', metavar='URL', nargs=1,
                            help='the remote URL (supported url schemes: http(s)://, file://)')
        group = parser.add_mutually_exclusive_group()
        group.required = True
        group.add_argument("--insecure",
                           dest="insecure",
                           action="store_true",
                           help="disable content checking for remote")
        group.add_argument("--gpg",
                           dest="gpgKey",
                           action="store",
                           help="GPG fingerprint to verify signature")

    def execute(self, args, uargs):
        pm = PackageManager()

        pm.createRemote(args.alias[0], args.url[0],
                        insecure=args.insecure,
                        gpgKey=args.gpgKey)


class RemoteRemoveCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'remove',
            "remove a remote repository")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('aliases',
                            metavar='ALIAS',
                            nargs='+',
                            help='the alias(es) of the remote(s) to remove')

    def execute(self, args, uargs):
        pm = PackageManager()
        for alias in args.aliases:
            pm.deleteRemote(alias)


class RemoteEnableCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'enable',
            "enable a remote repository")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('aliases',
                            metavar='ALIAS',
                            nargs='+',
                            help='the alias(es) of the remote(s) to enable')

    def execute(self, args, uargs):
        pm = PackageManager()

        for alias in args.aliases:
            remote = pm.listRemotes().get(alias)
            if remote is None:
                raise LeafException("Cannot find remote %s" % alias)
            remote.setEnabled(True)
            pm.updateRemote(remote)


class RemoteDisableCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(
            self,
            'disable',
            "disable a remote repository")

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('aliases',
                            metavar='ALIAS',
                            nargs='+',
                            help='the alias(es) of the remote(s) to disable')

    def execute(self, args, uargs):
        pm = PackageManager()

        for alias in args.aliases:
            remote = pm.listRemotes().get(alias)
            if remote is None:
                raise LeafException("Cannot find remote %s" % alias)
            remote.setEnabled(False)
            pm.updateRemote(remote)


class RemoteFetchCommand(LeafCommand):

    def __init__(self):
        LeafCommand.__init__(
            self,
            'fetch',
            "fetch content from enabled remotes")

    def execute(self, args, uargs):
        pm = PackageManager()

        pm.fetchRemotes(smartRefresh=False)
