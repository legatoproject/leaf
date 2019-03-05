"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import argparse

from leaf.api import PackageManager
from leaf.api.remotes import LeafSettings
from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import init_common_args
from leaf.core.error import ProfileOutOfSyncException
from leaf.core.utils import env_list_to_map
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier
from leaf.rendering.renderer.environment import EnvironmentRenderer


class EnvPrintCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "print", "display all environment variables to use the current (or given) profile")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, env_scripts=True)
        parser.add_argument("profiles", nargs=argparse.OPTIONAL, metavar="PROFILE", help="the profile name")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager(check_initialized=False)

        env = None
        if not wm.is_initialized:
            env = Environment.build(wm.build_builtin_environment(), wm.build_user_environment())
        else:
            # Get profile name, key could not exist if command is default
            # command
            name = args.profiles if "profiles" in vars(args) and args.profiles is not None else wm.current_profile_name
            profile = wm.get_profile(name)
            if not wm.is_profile_sync(profile):
                raise ProfileOutOfSyncException(profile)
            env = wm.build_full_environment(profile)
        wm.print_renderer(EnvironmentRenderer(env))
        if "activate_script" in vars(args):
            env.generate_scripts(args.activate_script, args.deactivate_script)


class EnvBuiltinCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "builtin", "display environment variables exported by leaf application")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, env_scripts=True)

    def execute(self, args, uargs):
        pm = PackageManager()

        env = pm.build_builtin_environment()
        pm.print_renderer(EnvironmentRenderer(env))
        env.generate_scripts(args.activate_script, args.deactivate_script)


class EnvUserCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "user", "display and update environment variables exported by user configuration")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, add_rm_env=True, env_scripts=True)

    def _get_epilog_text(self):
        settings = ", ".join(sorted(map(lambda s: s.key, LeafSettings.values())))
        return "note: \n  You can configure leaf settings with the user environment\n  List of settings: " + settings

    def execute(self, args, uargs):
        pm = PackageManager()

        if args.env_add_list is not None or args.env_rm_list is not None:
            pm.update_user_environment(set_map=env_list_to_map(args.env_add_list), unset_list=args.env_rm_list)

        env = pm.build_user_environment()
        pm.print_renderer(EnvironmentRenderer(env))
        env.generate_scripts(args.activate_script, args.deactivate_script)


class EnvWorkspaceCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "workspace", "display and update environment variables exported by workspace")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, add_rm_env=True, env_scripts=True)

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        if args.env_add_list is not None or args.env_rm_list is not None:
            wm.update_ws_environment(set_map=env_list_to_map(args.env_add_list), unset_list=args.env_rm_list)

        env = wm.build_ws_environment()
        wm.print_renderer(EnvironmentRenderer(env))
        env.generate_scripts(args.activate_script, args.deactivate_script)


class EnvProfileCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "profile", "display and update environment variables exported by profile")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, add_rm_env=True, env_scripts=True)
        parser.add_argument("profiles", nargs=argparse.OPTIONAL, metavar="PROFILE", help="the profile name")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        name = args.profiles if args.profiles is not None else wm.current_profile_name
        profile = wm.get_profile(name)

        if args.env_add_list is not None or args.env_rm_list is not None:
            profile.update_environment(set_map=env_list_to_map(args.env_add_list), unset_list=args.env_rm_list)
            wm.update_profile(profile)

        env = profile.build_environment()
        wm.print_renderer(EnvironmentRenderer(env))
        env.generate_scripts(args.activate_script, args.deactivate_script)


class EnvPackageCommand(LeafCommand):
    def __init__(self):
        LeafCommand.__init__(self, "package", "display environment variables exported by packages")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, env_scripts=True)
        parser.add_argument("--nodeps", dest="resolve_deps", action="store_false", help="do not add dependencies environements")
        parser.add_argument(dest="packages", metavar="PKGID", nargs=argparse.REMAINDER)

    def execute(self, args, uargs):
        pm = PackageManager()

        items = None
        if args.resolve_deps:
            items = DependencyUtils.installed(PackageIdentifier.parse_list(args.packages), pm.list_installed_packages(), ignore_unknown=True)
        else:
            items = PackageIdentifier.parse_list(args.packages)
        env = pm.build_packages_environment(items)
        pm.print_renderer(EnvironmentRenderer(env))
        env.generate_scripts(args.activate_script, args.deactivate_script)
