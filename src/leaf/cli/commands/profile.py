"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.cli.base import LeafCommand
from leaf.cli.cliutils import init_common_args
from leaf.model.modelutils import find_latest_version, find_manifest_list
from leaf.model.package import PackageIdentifier
from leaf.rendering.renderer.profile import ProfileListRenderer


class AbstractProfileCommand(LeafCommand):
    def __init__(self, name, description, profile_nargs=None):
        LeafCommand.__init__(self, name, description)
        self.profile_nargs = profile_nargs

    def _find_profile_name(self, args, wm=None):
        if hasattr(args, "profiles"):
            if isinstance(args.profiles, list):
                if len(args.profiles) == 1:
                    return args.profiles[0]
            elif isinstance(args.profiles, str):
                return args.profiles

        if wm is not None:
            return wm.current_profile_name

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        if self.profile_nargs is not None:
            parser.add_argument("profiles", nargs=self.profile_nargs, metavar="PROFILE", help="the profile name")


class ProfileListCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "list", "list profiles", profile_nargs="*")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()
        name = self._find_profile_name(args)
        profiles = []
        if "profiles" in vars(args) and len(args.profiles) > 0:
            for name in args.profiles:
                profiles.append(wm.get_profile(name))
        else:
            profiles.extend(wm.list_profiles().values())

        ipmap = wm.list_installed_packages()

        renderer = ProfileListRenderer(wm.ws_root_folder)
        for profile in profiles:
            sync = wm.is_profile_sync(profile)
            iplist = []
            if sync:
                iplist = wm.get_profile_dependencies(profile)
            else:
                iplist = find_manifest_list(list(map(PackageIdentifier.parse, profile.packages)), ipmap, ignore_unknown=True)
            renderer.append_profile(profile, sync, iplist)

        wm.print_renderer(renderer)


class ProfileCreateCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "create", "create a profile", profile_nargs=1)

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        profile = wm.create_profile(self._find_profile_name(args))
        wm.switch_profile(profile)
        wm.logger.print_default("Profile {pf.name} created".format(pf=profile))


class ProfileRenameCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "rename", "rename current profile", profile_nargs=None)

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument("profiles", nargs=1, metavar="NEWNAME", help="the new profile name")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        oldname = wm.current_profile_name
        profile = wm.rename_profile(oldname, args.profiles[0])
        wm.logger.print_default("Profile {oldname} renamed to {pf.name}".format(oldname=oldname, pf=profile))


class ProfileDeleteCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "delete", "delete profile(s)", profile_nargs="*")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        for pfname in args.profiles if len(args.profiles) > 0 else [wm.current_profile_name]:
            wm.delete_profile(pfname)
            wm.logger.print_default("Profile {name} deleted".format(name=pfname))


class ProfileSwitchCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "switch", "set current profile", profile_nargs=1)

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        profile = wm.get_profile(self._find_profile_name(args))
        wm.switch_profile(profile)
        wm.logger.print_verbose("Profile package folder: {pf.folder}".format(pf=profile))


class ProfileSyncCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "sync", "install packages needed for current or given profile", profile_nargs="?")

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        pfname = self._find_profile_name(args, wm=wm)
        profile = wm.get_profile(pfname)
        wm.provision_profile(profile)


class ProfileConfigCommand(AbstractProfileCommand):
    def __init__(self):
        AbstractProfileCommand.__init__(self, "config", "configure profile to add and remove packages", profile_nargs="?")

    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        init_common_args(parser, add_rm_packages=True)

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()

        profile = wm.get_profile(self._find_profile_name(args, wm=wm))

        if args.pkg_add_list is not None:
            valid_pilist = list(wm.list_available_packages().keys()) + list(wm.list_installed_packages().keys())
            pilist = []
            for motif in args.pkg_add_list:
                if PackageIdentifier.is_valid_identifier(motif):
                    pilist.append(PackageIdentifier.parse(motif))
                else:
                    pilist.append(find_latest_version(motif, valid_pilist))
            profile.add_packages(pilist)
        if args.pkg_rm_list is not None:
            valid_pilist = profile.packages_map.values()
            pilist = []
            for motif in args.pkg_rm_list:
                if PackageIdentifier.is_valid_identifier(motif):
                    pilist.append(PackageIdentifier.parse(motif))
                else:
                    pilist.append(find_latest_version(motif, valid_pilist))
            profile.remove_packages(pilist)

        wm.update_profile(profile)
