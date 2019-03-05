from leaf.cli.base import LeafCommand
from leaf.cli.plugins import LeafPluginManager

"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""


class LeafMetaCommand(LeafCommand):

    """
    Generic class to represent commands that have subcommands
    """

    def __init__(self, name: str, description: str, commands: str, accept_default: bool = False, plugins_manager: LeafPluginManager = None):
        LeafCommand.__init__(self, name, description)
        self.__commands = commands
        self.__accept_default = accept_default
        self.__plugins_manager = plugins_manager
        # Link subcommands to current Meta command
        for c in self.__commands:
            c.parent = self

    def _configure_parser(self, parser):
        # Add quiet/verbose
        super()._configure_parser(parser)

        # Create sub parsers
        subparsers = parser.add_subparsers(description="supported subcommands", metavar="SUBCOMMAND", help="actions to execute")

        # Initialize all subcommand parsers
        for command in self.__commands:
            command.setup(subparsers)
        # If external commands are enabled, initialize parsers
        if self.__plugins_manager is not None:
            for c in self.__plugins_manager.get_commands(self.path, ignored_names=[c.name for c in self.__commands]):
                c.setup(subparsers)
        # If no default command, subparser is required
        subparsers.required = not self.__accept_default
        # Register default handler
        if self.__accept_default:
            parser.set_defaults(handler=self.__commands[0])

    def execute(self, args, uargs):
        raise NotImplementedError()
