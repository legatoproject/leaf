"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.model.environment import Environment
from leaf.model.modelutils import find_latest_version, find_manifest
from leaf.model.package import IDENTIFIER_GETTER, PackageIdentifier


class DependencyUtils:

    """
    Used to build the dependency tree using dynamic conditions
    """

    @staticmethod
    def __build_tree(
        pilist: list, mfmap: dict, out: list, env: Environment = None, only_keep_latest: bool = False, ignored_pilist: list = None, ignore_unknown: bool = False
    ):
        """
        Build a manifest list of given PackageIdentifiers and its dependecies
        @return: Manifest list
        """
        if ignored_pilist is None:
            ignored_pilist = []
        for pi in pilist:
            if pi not in ignored_pilist:
                ignored_pilist.append(pi)
                mf = find_manifest(pi, mfmap, ignore_unknown=ignore_unknown)
                if mf is not None and mf not in out:
                    # Begin by adding dependencies
                    DependencyUtils.__build_tree(
                        mf.get_depends_from_env(env), mfmap, out, env=env, ignored_pilist=ignored_pilist, ignore_unknown=ignore_unknown
                    )
                    out.append(mf)

        if only_keep_latest:
            # Create a MF dict overriding package to latest version previously
            # computed
            alt_mfmap = {}
            for pi in mfmap:
                latest_mf = None
                for mf in out:
                    if pi.name == mf.name:
                        if latest_mf is None or mf.identifier > latest_mf.identifier:
                            latest_mf = mf
                alt_mfmap[pi] = latest_mf or mfmap[pi]
            # Reset out
            del out[:]
            # Reinvoke and give latest versions,
            # NB reset ignored_pilist to restart algo
            DependencyUtils.__build_tree(pilist, alt_mfmap, out, env=env, ignore_unknown=ignore_unknown)

    @staticmethod
    def installed(pilist: list, ipmap: dict, env: Environment = None, only_keep_latest: bool = False, ignore_unknown: bool = False):
        """
        Build a dependency list of installed packages and dependencies.
        Returns a list of InstalledPackage
        """
        out = []
        DependencyUtils.__build_tree(pilist, ipmap, out, env=env, only_keep_latest=only_keep_latest, ignore_unknown=ignore_unknown)
        return out

    @staticmethod
    def install(pilist: list, apmap: dict, ipmap: dict, env: Environment = None):
        """
        Build the list of packages to install, with needed dependencies.
        Already installed packages are removed for the list.
        Packages are sorted for install order.
        Returns a list of AvailablePackage
        """
        out = []

        # Build a map containing all knwon packages
        all_packages = dict(apmap)
        all_packages.update(ipmap)

        # Build the list from available packages
        DependencyUtils.__build_tree(pilist, all_packages, out, env=env)
        # Remove already installed packages
        out = [ap for ap in out if ap.identifier not in ipmap]
        return out

    @staticmethod
    def uninstall(pilist: list, ipmap: dict, env: Environment = None):
        """
        Build the list of packages to uninstall.
        Dependencies are preserved (ie dependencies needed by other installed packages are kept)
        Packages are sorted for uninstall order.
        Returns a list of InstalledPackage
        """
        out = []
        # Build the list from installed packages
        DependencyUtils.__build_tree(pilist, ipmap, out, env=env, ignore_unknown=True)
        # for uninstall, reverse order
        out = list(reversed(out))
        # Maintain dependencies
        other_pi_list = [ip.identifier for ip in ipmap.values() if ip not in out]
        # Keep all configurations (ie env=None) for all other installed packages
        for needed_ip in DependencyUtils.installed(other_pi_list, ipmap, env=None, ignore_unknown=True):
            if needed_ip in out:
                out.remove(needed_ip)
        return out

    @staticmethod
    def prereq(pilist: list, apmap: dict, ipmap: dict, env: Environment = None):
        """
        Return the list of prereq packages to install
        Packages are sorted in alpha order.
        Returns a list of AvailablePackages
        """
        out = []
        # First get the install tree
        aplist = DependencyUtils.install(pilist, apmap, ipmap, env=env)
        # Get all prereq PI and find corresponding AP
        for ap in aplist:
            for pi in map(PackageIdentifier.parse, ap.requires_packages):
                out.append(find_manifest(pi, apmap))
        # sort alphabetically and ensure no dupplicates
        out = list(sorted(set(out), key=IDENTIFIER_GETTER))
        return out

    @staticmethod
    def upgrade(namelist: list, apmap: dict, ipmap: dict, env: Environment = None):
        """
        Return a tuple of 2 lists:
         - First contains the AvailablePackages  to install for an upgrade
         - Second contains InstalledPackages that can be uninstalled
        uninstalled after
        """

        # Update all auto upgradable packages if no input given
        if namelist is None:
            namelist = set(map(lambda ip: ip.name, filter(lambda ip: ip.auto_upgrade, ipmap.values())))

        # Compute the list of package to install
        install_list = []
        for name in namelist:
            latest_installed = find_latest_version(name, ipmap)
            latest_available = find_latest_version(name, apmap, ignore_unknown=False)
            if latest_available is not None and latest_available > latest_installed:
                ap = apmap[latest_available]
                if ap not in install_list:
                    install_list.append(ap)

        # Compute the list of packages to uninstall
        uninstall_list = []
        for ap in install_list:
            for ip in ipmap.values():
                if ip.name == ap.name and ip.auto_upgrade and ap.identifier > ip.identifier:
                    uninstall_list.append(ip)
        uninstall_list = sorted(uninstall_list, key=IDENTIFIER_GETTER)
        return (install_list, uninstall_list)
