"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.api import RemoteManager
from leaf.cli.base import LeafCommand
from leaf.cli.completion import complete_remotes
from leaf.core.download import PRIORITIES_RANGE
from leaf.core.error import LeafException
from leaf.rendering.renderer.remote import RemoteListRenderer


class RemoteListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "list", "list remote repositories")

    def execute(self, args, uargs):
        rm = RemoteManager()

        rend = RemoteListRenderer()
        rend.extend(rm.list_remotes().values())
        rm.print_renderer(rend)


class RemoteAddCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "add", "add a remote repository")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("alias", metavar="ALIAS", nargs=1, help="the alias of the new remote")
        parser.add_argument("url", metavar="URL", nargs=1, help="the remote URL (supported url schemes: http(s)://, file://)")
        parser.add_argument(
            "--priority",
            dest="priority",
            type=int,
            help="remote priority between {min} and {max}, lower number means higher priority".format(min=PRIORITIES_RANGE[0], max=PRIORITIES_RANGE[-1]),
        )
        group = parser.add_mutually_exclusive_group()
        group.required = False
        group.add_argument("--insecure", dest="insecure", action="store_true", help="disable content checking for remote (default mode)")
        group.add_argument("--gpg", dest="gpgkey", action="store", help="GPG fingerprint to verify signature")

    def execute(self, args, uargs):
        rm = RemoteManager()
        if args.priority is not None and args.priority not in PRIORITIES_RANGE:
            raise LeafException("Invalid priority, must be between {min} and {max}".format(min=PRIORITIES_RANGE[0], max=PRIORITIES_RANGE[-1]))
        rm.create_remote(args.alias[0], args.url[0], insecure=args.insecure, gpgkey=args.gpgkey, priority=args.priority)


class RemoteRemoveCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "remove", "remove a remote repository")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("aliases", metavar="ALIAS", nargs="+", help="the alias(es) of the remote(s) to remove").completer = complete_remotes

    def execute(self, args, uargs):
        rm = RemoteManager()
        for alias in args.aliases:
            rm.delete_remote(alias)


class RemoteEnableCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "enable", "enable a remote repository")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("aliases", metavar="ALIAS", nargs="+", help="the alias(es) of the remote(s) to enable").completer = complete_remotes

    def execute(self, args, uargs):
        rm = RemoteManager()

        for alias in args.aliases:
            remote = rm.list_remotes().get(alias)
            if remote is None:
                raise LeafException("Cannot find remote {alias}".format(alias=alias))
            remote.enabled = True
            rm.update_remote(remote)


class RemoteDisableCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "disable", "disable a remote repository")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("aliases", metavar="ALIAS", nargs="+", help="the alias(es) of the remote(s) to disable").completer = complete_remotes

    def execute(self, args, uargs):
        rm = RemoteManager()

        for alias in args.aliases:
            remote = rm.list_remotes().get(alias)
            if remote is None:
                raise LeafException("Cannot find remote {alias}".format(alias=alias))
            remote.enabled = False
            rm.update_remote(remote)


class RemoteFetchCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "fetch", "fetch content from enabled remotes")

    def execute(self, args, uargs):
        rm = RemoteManager()
        rm.fetch_remotes(force_refresh=True)
