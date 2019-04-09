#!/usr/bin/env python3
# LEAF_DESCRIPTION update current profile packages
"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""


from leaf.cli.completion import complete_available_packages
from leaf.cli.plugins import LeafPluginCommand
from leaf.core.error import InvalidPackageNameException
from leaf.model.modelutils import group_package_identifiers_by_name
from leaf.model.package import PackageIdentifier


def get_latest_ap(motif, pilist):
    if PackageIdentifier.is_valid_identifier(motif):
        pi = PackageIdentifier.parse(motif)
        return pi if pi in pilist else None
    out = None
    for pi in pilist:
        if pi.name == motif:
            if out is None or pi > out:
                out = pi
    return out


class UpdagePlugin(LeafPluginCommand):
    def _configure_parser(self, parser):
        super()._configure_parser(parser)
        parser.add_argument(
            "-p", "--add-package", dest="packages", action="append", metavar="PKG_NAME", help="specific packages to update"
        ).completer = complete_available_packages

    def execute(self, args, uargs):
        wm = self.get_workspacemanager()
        logger = wm.logger

        pfname = wm.current_profile_name
        profile = wm.get_profile(pfname)

        profile_packagesmap = profile.packages_map
        grouped_packagesmap = group_package_identifiers_by_name(wm.list_installed_packages())
        grouped_packagesmap = group_package_identifiers_by_name(wm.list_available_packages(), pkgmap=grouped_packagesmap)

        update_pilist = []

        motiflist = args.packages if args.packages is not None else profile_packagesmap.keys()
        for motif in motiflist:
            pi = None
            if PackageIdentifier.is_valid_identifier(motif):
                # User force specific version
                candidate = PackageIdentifier.parse(motif)
                if candidate.name in grouped_packagesmap:
                    if candidate in grouped_packagesmap[candidate.name]:
                        pi = candidate
            elif motif in grouped_packagesmap:
                # Get latest version
                pi = grouped_packagesmap[motif][-1]

            if pi is None:
                # Unknown package identifier
                raise InvalidPackageNameException(motif)

            if pi is not None and pi not in update_pilist:
                # Get PI in profile
                previouspi = profile_packagesmap.get(pi.name)
                if previouspi is None:
                    # Package not in profile yet, add it
                    if wm.print_with_confirm("Do you want to add package {pi}?".format(pi=pi)):
                        update_pilist.append(pi)
                elif previouspi != pi:
                    # Package already in profile with a different version, update it
                    if wm.print_with_confirm("Do you want to update package {pi.name} from {oldpi.version} to {pi.version}?".format(pi=pi, oldpi=previouspi)):
                        update_pilist.append(pi)
                else:
                    # Package already in profile with same version, do nothing
                    pass

        if len(update_pilist) == 0:
            logger.print_default("Nothing to do")
        else:
            profile.add_packages(update_pilist)
            wm.update_profile(profile)
            wm.provision_profile(profile)
