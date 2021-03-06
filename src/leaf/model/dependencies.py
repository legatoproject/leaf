"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from collections import OrderedDict
from functools import reduce

from leaf.core.logger import TextLogger
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
        all_packages = reduce(lambda a, b: a.update(b) or a, [apmap, ipmap], {})
        # Build the list from available packages
        DependencyUtils.__build_tree(pilist, all_packages, out, env=env)
        # Remove already installed packages
        out = [ap for ap in out if ap.identifier not in ipmap]
        return out

    @staticmethod
    def uninstall(pilist: list, ipmap: dict, env: Environment = None, logger: TextLogger = None):
        """
        Build the list of packages to uninstall.
        Dependencies are preserved (ie dependencies needed by other installed packages are kept)
        Packages are sorted for uninstall order.
        Returns a list of InstalledPackage
        """

        def _log(message):
            if logger is not None and logger.isverbose():
                logger.print_verbose(message)

        out = []
        # Build the list from installed packages
        DependencyUtils.__build_tree(pilist, ipmap, out, env=env, ignore_unknown=True)
        # for uninstall, reverse order
        out = list(reversed(out))

        # Remove read only packages
        ro_packages = list(filter(lambda ip: ip.read_only, out))
        if len(ro_packages) > 0 and logger is not None and logger.isverbose():
            logger.print_verbose("System package(s) cannot be uninstalled: " + ", ".join(map(str, ro_packages)))

        # Maintain dependencies
        other_pi_list = [ip.identifier for ip in ipmap.values() if ip not in out]
        # Keep all configurations (ie env=None) for all other installed packages
        for needed_ip in DependencyUtils.installed(other_pi_list, ipmap, env=None, ignore_unknown=True):
            if needed_ip in out:
                if logger is not None and logger.isverbose():
                    # Print packages which needs this package
                    rdepends = DependencyUtils.rdepends([needed_ip.identifier], ipmap, env=env)
                    _log("Cannot uninstall {ip.identifier} (dependency of {text})".format(ip=needed_ip, text=", ".join(map(str, rdepends))))
                out.remove(needed_ip)
        out = [ip for ip in out if ip not in ro_packages]
        return out

    @staticmethod
    def prereq(pilist: list, apmap: dict, ipmap: dict, env: Environment = None):
        """
        Return the list of prereq packages to install
        Packages are sorted in alpha order.
        Returns a list of AvailablePackages
        """
        # All available packages
        mfmap = reduce(lambda a, b: a.update(b) or a, [apmap or {}, ipmap or {}], {})

        # Get the list of prereq
        prereq_pilist = []
        for pi in pilist:
            mf = find_manifest(pi, mfmap)
            for pis in mf.requires_packages:
                prereq_pi = PackageIdentifier.parse(pis)
                if prereq_pi not in prereq_pilist:
                    prereq_pilist.append(prereq_pi)

        # Compute prereq dependencies
        out = []
        DependencyUtils.__build_tree(prereq_pilist, mfmap, out, env=env)
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

    @staticmethod
    def rdepends(pilist: list, mfmap: dict, env: Environment = None):
        out = OrderedDict()
        for pi, mf in mfmap.items():
            try:
                for cpi in mf.get_depends_from_env(env):
                    if cpi in pilist and pi not in out:
                        out[pi] = mf
            except Exception:
                pass
        return out
