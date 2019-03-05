"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.api import PackageManager
from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import init_common_args
from leaf.model.base import Scope
from leaf.model.environment import Environment
from leaf.model.features import FeatureManager
from leaf.rendering.renderer.feature import FeatureListRenderer


class FeatureListCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "list", "list all available features")

    def execute(self, args, uargs):
        pm = PackageManager()

        fm = FeatureManager()
        fm.append_features(pm.list_installed_packages().values())
        fm.append_features(pm.list_available_packages().values())

        renderer = FeatureListRenderer()
        renderer.extend(sorted(fm.features.values(), key=lambda x: x.name))
        pm.print_renderer(renderer)


class FeatureQueryCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "query", "query feature status")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("feature", metavar="FEATURE", nargs=1, help="the feature name")

    def execute(self, args, uargs):
        pm = PackageManager()

        fm = FeatureManager()
        fm.append_features(pm.list_installed_packages().values())
        fm.append_features(pm.list_available_packages().values())

        feature = fm.get_feature(args.feature[0])
        pm.logger.print_verbose("Found feature {feature.name} with key {feature.key}".format(feature=feature))

        env = None
        workspace = self.get_workspacemanager(check_initialized=False)
        if workspace.is_initialized:
            profile = workspace.get_profile(workspace.current_profile_name)
            env = workspace.build_full_environment(profile)
        else:
            env = Environment.build(pm.build_builtin_environment(), pm.build_user_environment())
        value = env.find_value(feature.key)
        pm.logger.print_verbose("Found {feature.key}={value} in env".format(feature=feature, value=value))
        text = " | ".join(feature.retrieve_enums_for_value(value))
        if pm.logger.isquiet():
            pm.logger.print_quiet(text)
        else:
            pm.logger.print_default("{feature.name} = {values}".format(feature=feature, values=text))


class FeatureToggleCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "toggle", "toggle a feature")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, with_scope=True)
        parser.add_argument("feature_name", metavar="FEATURE", nargs=1, help="the feature name")
        parser.add_argument("feature_value", metavar="VALUE", nargs=1, help="the feature value")

    def execute(self, args, uargs):

        fm = FeatureManager()
        name = args.feature_name[0]
        value = args.feature_value[0]

        if args.env_scope == Scope.USER:
            pm = PackageManager()
            fm.append_features(pm.list_installed_packages().values())
            fm.append_features(pm.list_available_packages().values())

            usrc = pm.read_user_configuration()
            fm.toggle_feature(name, value, usrc)
            pm.write_user_configuration(usrc)
        else:
            wm = self.get_workspacemanager()
            fm.append_features(wm.list_installed_packages().values())
            fm.append_features(wm.list_available_packages().values())

            if args.env_scope == Scope.WORKSPACE:
                wsrc = wm.read_ws_configuration()
                fm.toggle_feature(name, value, wsrc)
                wm.write_ws_configuration(wsrc)
            elif args.env_scope == Scope.PROFILE:
                profile = wm.get_profile(wm.current_profile_name)
                fm.toggle_feature(name, value, profile)
                wm.update_profile(profile)
