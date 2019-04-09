"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""


import argparse
from collections import OrderedDict

from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import init_common_args
from leaf.cli.completion import complete_settings
from leaf.rendering.renderer.settings import SettingsListRenderer


class ConfigListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "list", "list all available settings")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("-a", "--all", dest="show_all_settings", action="store_true", help="show all settings, even those not set")
        parser.add_argument("keywords", metavar="KEYWORD", nargs=argparse.OPTIONAL).completer = complete_settings

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)

        show_all_settings = "show_all_settings" in args and args.show_all_settings
        motif = None
        if "keywords" in args and args.keywords is not None:
            motif = args.keywords
            show_all_settings = True

        settings_map = OrderedDict()
        for sid, setting in wm.get_settings().items():  # filter if setting is set
            # filter by motif if provided in command line
            if motif is None or motif.lower() in sid.lower():
                settings_map[sid] = setting

        # Get settings value
        values_map = wm.get_settings_value(*settings_map.keys())

        # Build renderer
        renderer = SettingsListRenderer(wm.configuration_folder, values_map, filter_unset=not show_all_settings)
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
