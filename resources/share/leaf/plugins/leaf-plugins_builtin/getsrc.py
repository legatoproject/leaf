"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import argparse

from leaf.api import WorkspaceManager
from leaf.cli.cliutils import init_common_args
from leaf.cli.plugins import LeafPluginCommand
from leaf.core.error import LeafException, WorkspaceNotInitializedException
from leaf.core.settings import Setting
from leaf.model.base import Scope
from leaf.model.features import FeatureManager


class GetSrcConstants:
    SRCSUFFIX = "-src"
    BINARY = "binary"
    SOURCE = "source"
    SOURCE_EXT = "source-"


class GetSrcSettings:
    MODULE = Setting("LEAF_GETSRC_MODULE")


class GetSrcContext:
    def __init__(self, args):
        self.__args = args
        self.__wm = WorkspaceManager(WorkspaceManager.find_root(check_parents=True))
        self.__fm = FeatureManager()
        self.__fm.append_features(self.__wm.list_installed_packages().values())
        self.__fm.append_features(self.__wm.list_available_packages().values())
        if args.module is not None and not self.__wm.is_initialized:
            raise WorkspaceNotInitializedException()
        GetSrcSettings.MODULE.value = args.module

    @property
    def wm(self):
        return self.__wm

    @property
    def fm(self):
        return self.__fm

    @property
    def args(self):
        return self.__args

    @property
    def scope(self):
        return self.__args.env_scope


class GetSrcPlugin(LeafPluginCommand):
    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument(
            "module",
            nargs=argparse.OPTIONAL,
            metavar="SRCMODULE",
            help="the module from which to trigger source sync\nif not specified, list available modules",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--binary",
            "--disable",
            dest="required_status",
            action="store_const",
            const=GetSrcConstants.BINARY,
            help="disable source mode and get back to binary mode",
        )
        group.add_argument(
            "--source",
            dest="required_status",
            action="store",
            const=GetSrcConstants.SOURCE,
            nargs="?",
            metavar="MODE",
            help="toggle source mode (eventually in the specified MODE)\nand trigger source sync",
        )
        init_common_args(parser, with_scope=True)

    def get_known_modules(self, ctx):
        modules = []
        for f in ctx.fm.features.keys():
            if f.endswith(GetSrcConstants.SRCSUFFIX):
                modules += [(f[: -len(GetSrcConstants.SRCSUFFIX)])]
        return modules

    def get_feature(self, ctx):
        return ctx.fm.get_feature(GetSrcSettings.MODULE.value + GetSrcConstants.SRCSUFFIX)

    def get_profile(self, ctx):
        return ctx.wm.get_profile(ctx.wm.current_profile_name)

    def get_feature_status(self, ctx):
        feature = self.get_feature(ctx)
        profile = self.get_profile(ctx)
        env = ctx.wm.build_full_environment(profile)
        value = env.find_value(feature.key)
        vlist = feature.retrieve_enums_for_value(value)
        if len(vlist) != 1:
            raise LeafException(message="Internal error while computing {ftr.name} value".format(ftr=feature))
        return vlist[0]

    def set_feature_status(self, ctx, status):
        feature = self.get_feature(ctx)
        if ctx.scope == Scope.USER:
            usrc = ctx.wm.read_user_configuration()
            ctx.fm.toggle_feature(feature.name, status, usrc)
            ctx.wm.write_user_configuration(usrc)
        elif ctx.scope == Scope.WORKSPACE:
            wksc = ctx.wm.read_ws_configuration()
            ctx.fm.toggle_feature(feature.name, status, wksc)
            ctx.wm.write_ws_configuration(wksc)
        elif ctx.scope == Scope.PROFILE:
            profile = self.get_profile(ctx)
            ctx.fm.toggle_feature(feature.name, status, profile)
            ctx.wm.update_profile(profile)

    def sync_module(self, ctx):
        # Check for valid source module
        if GetSrcSettings.MODULE.value not in self.get_known_modules(ctx):
            raise LeafException(message="Unknown source module: " + GetSrcSettings.MODULE.value, hints=["Try 'leaf getsrc' to list available modules"])

        # Check for current status
        current_status = self.get_feature_status(ctx)
        ctx.wm.logger.print_verbose("Current status for {m} module: {s}".format(m=GetSrcSettings.MODULE.value, s=current_status))

        # Determine new required status
        new_status = None
        if ctx.args.required_status is not None:
            if ctx.args.required_status in [GetSrcConstants.BINARY, GetSrcConstants.SOURCE]:
                new_status = ctx.args.required_status
            else:
                new_status = GetSrcConstants.SOURCE_EXT + ctx.args.required_status
        elif current_status == GetSrcConstants.BINARY:
            # No status arg specified, but currently in binary mode: default toggle to source mode
            new_status = GetSrcConstants.SOURCE

        # Different value?
        if new_status is not None and current_status != new_status:
            ctx.wm.logger.print_verbose("Toggling status for {m} module: {s}".format(m=GetSrcSettings.MODULE.value, s=new_status))
            self.set_feature_status(ctx, new_status)

        # In any case, finally trigger a profile sync
        ctx.wm.provision_profile(self.get_profile(ctx))

    def execute(self, args, uargs):
        ctx = GetSrcContext(args)
        if GetSrcSettings.MODULE.value is None:
            # Just list available modules
            ctx.wm.logger.print_quiet("\n".join(self.get_known_modules(ctx)))
        else:
            # Something to sync
            self.sync_module(ctx)
