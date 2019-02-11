'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from leaf import __help_description__, __version__
from leaf.cli.build import (BuildIndexSubCommand, BuildManifestSubCommand,
                            BuildPackSubCommand)
from leaf.cli.cliutils import EnvSetterAction, LeafMetaCommand
from leaf.cli.config import ConfigCommand
from leaf.cli.env import (EnvBuiltinCommand, EnvPackageCommand,
                          EnvPrintCommand, EnvProfileCommand, EnvUserCommand,
                          EnvWorkspaceCommand)
from leaf.cli.feature import (FeatureListCommand, FeatureQueryCommand,
                              FeatureToggleCommand)
from leaf.cli.package import (PackageDepsCommand, PackageInstallCommand,
                              PackageListCommand, PackagePrereqCommand,
                              PackageSyncCommand, PackageUninstallCommand,
                              PackageUpgradeCommand)
from leaf.cli.profile import (ProfileConfigCommand, ProfileCreateCommand,
                              ProfileDeleteCommand, ProfileListCommand,
                              ProfileRenameCommand, ProfileSwitchCommand,
                              ProfileSyncCommand)
from leaf.cli.remote import (RemoteAddCommand, RemoteDisableCommand,
                             RemoteEnableCommand, RemoteFetchCommand,
                             RemoteListCommand, RemoteRemoveCommand)
from leaf.cli.run import RunCommand
from leaf.cli.search import SearchCommand
from leaf.cli.select import SelectCommand
from leaf.cli.status import StatusCommand
from leaf.cli.workspace import WorkspaceInitCommand
from leaf.core.constants import LeafSettings
from leaf.rendering.ansi import ANSI


class LeafRootCommand(LeafMetaCommand):
    def __init__(self, pluginManager):
        LeafMetaCommand.__init__(
            self,
            'leaf',
            __help_description__,
            [
                # Common commands
                StatusCommand(),
                SearchCommand(),
                SelectCommand(),

                # Env
                LeafMetaCommand(
                    'env',
                    "display environement variables",
                    [EnvPrintCommand(),
                     EnvBuiltinCommand(),
                     EnvUserCommand(),
                     EnvWorkspaceCommand(),
                     EnvProfileCommand(),
                     EnvPackageCommand()],
                    acceptDefaultCommand=True,
                    pluginManager=pluginManager
                ),
                # Entry points
                RunCommand(),
                # Features
                LeafMetaCommand(
                    'feature',
                    "manage features from available packages",
                    [FeatureListCommand(),
                     FeatureToggleCommand(),
                     FeatureQueryCommand()],
                    acceptDefaultCommand=True,
                    pluginManager=pluginManager
                ),
                # Workspace common operations
                WorkspaceInitCommand(),
                LeafMetaCommand(
                    'profile',
                    "command to manage profiles",
                    [ProfileListCommand(),
                     ProfileCreateCommand(),
                     ProfileRenameCommand(),
                     ProfileDeleteCommand(),
                     ProfileSwitchCommand(),
                     ProfileSyncCommand(),
                     ProfileConfigCommand()],
                    acceptDefaultCommand=True,
                    pluginManager=pluginManager
                ),
                # Config & remotes
                ConfigCommand(),
                LeafMetaCommand(
                    'remote',
                    "display and manage remote repositories",
                    [RemoteListCommand(),
                     RemoteAddCommand(),
                     RemoteRemoveCommand(),
                     RemoteEnableCommand(),
                     RemoteDisableCommand(),
                     RemoteFetchCommand()],
                    acceptDefaultCommand=True,
                    pluginManager=pluginManager
                ),
                # Packages
                LeafMetaCommand(
                    'package',
                    "core package manager commands",
                    [PackageListCommand(),
                     PackageInstallCommand(),
                     PackageUpgradeCommand(),
                     PackageUninstallCommand(),
                     PackageSyncCommand(),
                     PackageDepsCommand(),
                     PackagePrereqCommand()],
                    acceptDefaultCommand=True,
                    pluginManager=pluginManager
                ),
                # Releng
                LeafMetaCommand(
                    'build',
                    "commands to build leaf artifacts (manifest, package or index)",
                    [BuildPackSubCommand(),
                     BuildIndexSubCommand(),
                     BuildManifestSubCommand()],
                    pluginManager=pluginManager
                )],
            pluginManager=pluginManager)

    def _createParser(self, subparsers):
        # Setup argument parser
        apkw = {'description': self.description,
                'formatter_class': RawDescriptionHelpFormatter}
        # Disable args abbreviation, only supported in 3.5+
        if sys.version_info > (3, 5):
            apkw['allow_abbrev'] = False

        return _MyArgumentParser(**apkw)

    def _configureParser(self, parser):
        super()._configureParser(parser)
        parser.add_argument('-V', '--version',
                            action='version',
                            version="leaf version %s" % __version__)
        parser.add_argument("--non-interactive",
                            action=EnvSetterAction,
                            dest=LeafSettings.NON_INTERACTIVE.key,
                            const='1',
                            help="assume yes if a confirmation is asked")
        parser.add_argument("-w", "--workspace",
                            action=EnvSetterAction,
                            dest=LeafSettings.WORKSPACE.key,
                            nargs=1,
                            help="use given workspace")


class _MyArgumentParser(ArgumentParser):
    '''
    Class that prints argparse error message in red
    '''

    def __init__(self, *args, **kwargs):
        ArgumentParser.__init__(self, *args, **kwargs)

    def error(self, *args, **kwargs):
        print(ANSI.style().RESET_ALL, ANSI.fore().RED,
              file=sys.stderr, end='', sep='')
        try:
            super().error(*args, **kwargs)
        finally:
            print(ANSI.style().RESET_ALL,
                  file=sys.stderr, end='', sep='')
