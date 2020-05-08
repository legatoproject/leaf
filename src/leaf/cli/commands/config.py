"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""


import argparse
from collections import OrderedDict
from pathlib import Path

from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import init_common_args
from leaf.cli.completion import complete_settings
from leaf.cli.meta import LeafMetaCommand
from leaf.core.constants import LeafSettings
from leaf.model.base import Scope
from leaf.rendering.renderer.settings import SettingsListRenderer


class ConfigMetaCommand(LeafMetaCommand):
    # Code to be removed when "config --root" CLI will be dropped

    def __init__(self, *args, **kwargs):
        kwargs["accept_default"] = True
        LeafMetaCommand.__init__(self, *args, **kwargs)

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("--root", dest="rootfolder", type=Path, help="the folder where packages are installed")
        self.__default_handler = parser.get_default("handler")
        parser.set_defaults(handler=self)

    def execute(self, args, uargs):
        if args.rootfolder is None:
            return self.__default_handler.execute(args, uargs)

        wm = self.get_workspacemanager(check_initialized=False)
        wm.print_hints(
            "The --root option is deprecated and will soon be removed",
            "Next time you should use 'leaf config set {id} \"{value}\"' instead".format(id=LeafSettings.USER_PKG_FOLDER.identifier, value=args.rootfolder),
        )
        wm.set_setting(LeafSettings.USER_PKG_FOLDER.identifier, args.rootfolder, scope=Scope.USER)


class ConfigListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "list", "list all available settings")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("keywords", metavar="KEYWORD", nargs=argparse.OPTIONAL).completer = complete_settings

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)

        motif = None
        if "keywords" in args and args.keywords is not None:
            motif = args.keywords

        settings_map = OrderedDict()
        for sid, setting in wm.get_settings().items():  # filter if setting is set
            # filter by motif if provided in command line
            if motif is None or motif.lower() in sid.lower():
                settings_map[sid] = setting

        # Get settings value
        values_map = wm.get_settings_value(*settings_map.keys())

        # Build renderer
        renderer = SettingsListRenderer(wm.configuration_folder, values_map, filter_unset=False)
        renderer.extend(settings_map.values())
        wm.print_renderer(renderer)


class SettingGetCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "get", "get setting value")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("settings_id", metavar="ID", nargs=argparse.ONE_OR_MORE, help="the setting to get").completer = complete_settings

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)

        def myformat(v):
            return "(unset)" if v is None else '"{0}"'.format(v)

        for sid, value in wm.get_settings_value(*args.settings_id).items():
            if wm.logger.isquiet():
                print(value or "")
            elif wm.logger.isverbose():
                print("{id} = {value}".format(id=sid, value=myformat(value)))
            else:
                print("{id}={value}".format(id=sid, value=value))


class SettingSetCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "set", "update a setting")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, with_scope=True)
        parser.add_argument("setting_id", metavar="ID", help="the setting to update").completer = complete_settings
        parser.add_argument("setting_value", metavar="VALUE", help="the setting value")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)
        wm.set_setting(args.setting_id, args.setting_value, scope=args.env_scope)


class SettingResetCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "reset", "reset a setting")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("setting_id", metavar="ID", help="the setting to update").completer = complete_settings

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)
        wm.unset_setting(args.setting_id)
