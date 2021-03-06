"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter, SUPPRESS

from leaf import __help_description__, __version__
from leaf.cli.cliutils import EnvSetterAction
from leaf.cli.commands.build import BuildIndexSubCommand, BuildManifestSubCommand, BuildPackSubCommand
from leaf.cli.commands.config import ConfigListCommand, ConfigMetaCommand, SettingGetCommand, SettingResetCommand, SettingSetCommand
from leaf.cli.commands.env import EnvBuiltinCommand, EnvPackageCommand, EnvPrintCommand, EnvProfileCommand, EnvUserCommand, EnvWorkspaceCommand
from leaf.cli.commands.help import HelpCommand
from leaf.cli.commands.package import (
    PackageDepsCommand,
    PackageInspectCommand,
    PackageInstallCommand,
    PackageListCommand,
    PackageSyncCommand,
    PackageUninstallCommand,
    PackageUpgradeCommand,
)
from leaf.cli.commands.profile import (
    ProfileConfigCommand,
    ProfileCreateCommand,
    ProfileDeleteCommand,
    ProfileListCommand,
    ProfileRenameCommand,
    ProfileSwitchCommand,
    ProfileSyncCommand,
)
from leaf.cli.commands.remote import RemoteAddCommand, RemoteDisableCommand, RemoteEnableCommand, RemoteFetchCommand, RemoteListCommand, RemoteRemoveCommand
from leaf.cli.commands.run import RunCommand
from leaf.cli.commands.search import SearchCommand
from leaf.cli.commands.select import SelectCommand
from leaf.cli.commands.status import StatusCommand
from leaf.cli.commands.workspace import WorkspaceInitCommand
from leaf.cli.meta import LeafMetaCommand
from leaf.core.constants import LeafSettings
from leaf.rendering.ansi import ANSI


class LeafRootCommand(LeafMetaCommand):
    def __init__(self, plugins_manager):
        LeafMetaCommand.__init__(
            self,
            "leaf",
            __help_description__,
            [
                # Common commands
                StatusCommand(),
                SearchCommand(),
                SelectCommand(),
                # Env
                LeafMetaCommand(
                    "env",
                    "display environement variables",
                    [EnvPrintCommand(), EnvBuiltinCommand(), EnvUserCommand(), EnvWorkspaceCommand(), EnvProfileCommand(), EnvPackageCommand()],
                    accept_default=True,
                    plugins_manager=plugins_manager,
                ),
                # Entry points
                RunCommand(),
                # Config&settings
                ConfigMetaCommand(
                    "config",
                    "manage leaf configuration",
                    [ConfigListCommand(), SettingGetCommand(), SettingSetCommand(), SettingResetCommand()],
                    accept_default=True,
                    plugins_manager=plugins_manager,
                ),
                # Workspace common operations
                WorkspaceInitCommand(),
                LeafMetaCommand(
                    "profile",
                    "command to manage profiles",
                    [
                        ProfileListCommand(),
                        ProfileCreateCommand(),
                        ProfileRenameCommand(),
                        ProfileDeleteCommand(),
                        ProfileSwitchCommand(),
                        ProfileSyncCommand(),
                        ProfileConfigCommand(),
                    ],
                    accept_default=True,
                    plugins_manager=plugins_manager,
                ),
                # Remotes
                LeafMetaCommand(
                    "remote",
                    "display and manage remote repositories",
                    [RemoteListCommand(), RemoteAddCommand(), RemoteRemoveCommand(), RemoteEnableCommand(), RemoteDisableCommand(), RemoteFetchCommand()],
                    accept_default=True,
                    plugins_manager=plugins_manager,
                ),
                # Packages
                LeafMetaCommand(
                    "package",
                    "core package manager commands",
                    [
                        PackageListCommand(),
                        PackageInstallCommand(),
                        PackageUpgradeCommand(),
                        PackageUninstallCommand(),
                        PackageSyncCommand(),
                        PackageDepsCommand(),
                        PackageInspectCommand(),
                    ],
                    accept_default=True,
                    plugins_manager=plugins_manager,
                ),
                # Releng
                LeafMetaCommand(
                    "build",
                    "commands to build leaf artifacts (manifest, package or index)",
                    [BuildPackSubCommand(), BuildIndexSubCommand(), BuildManifestSubCommand()],
                    plugins_manager=plugins_manager,
                ),
                # Help
                HelpCommand(),
            ],
            plugins_manager=plugins_manager,
        )

    def _create_parser(self, subparsers):
        # Setup argument parser
        apkw = {"description": self.description, "formatter_class": RawDescriptionHelpFormatter}
        # Disable args abbreviation, only supported in 3.5+
        if sys.version_info > (3, 5):
            apkw["allow_abbrev"] = False

        return _MyArgumentParser(**apkw)

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-V", "--version", action="version", version="leaf version {version}".format(version=__version__))
        parser.add_argument(
            "--non-interactive",
            action=EnvSetterAction,
            dest=LeafSettings.NON_INTERACTIVE.key,
            const="1",
            help="assume yes if a print_with_confirmation is asked",
        )
        parser.add_argument(
            "-w",
            "--workspace",
            action=EnvSetterAction,
            dest=LeafSettings.WORKSPACE.key,
            nargs=1,
            help=SUPPRESS
        )


class _MyArgumentParser(ArgumentParser):

    """
    Class that prints argparse error message in red
    """

    def __init__(self, *args, **kwargs):
        ArgumentParser.__init__(self, *args, **kwargs)

    def error(self, *args, **kwargs):
        print(ANSI.style.RESET_ALL, ANSI.fore.RED, file=sys.stderr, end="", sep="")
        try:
            super().error(*args, **kwargs)
        finally:
            print(ANSI.style.RESET_ALL, file=sys.stderr, end="", sep="")
