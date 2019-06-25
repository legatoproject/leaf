"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from builtins import Exception
from collections import OrderedDict
from pathlib import Path
from tarfile import TarFile

from leaf.api.remotes import RemoteManager
from leaf.core.constants import LeafConstants, LeafFiles
from leaf.core.download import download_and_verify_file
from leaf.core.error import InvalidPackageNameException, LeafException, LeafOutOfDateException, NoPackagesInCacheException
from leaf.core.lock import LockFile
from leaf.core.utils import (
    fs_check_free_space,
    fs_compute_total_size,
    get_cached_artifact_name,
    mark_folder_as_ignored,
    mkdir_tmp_leaf_dir,
    mkdirs,
    rmtree_force,
)
from leaf.model.dependencies import DependencyUtils
from leaf.model.environment import Environment
from leaf.model.modelutils import check_leaf_min_version, find_manifest, is_latest_package
from leaf.model.package import AvailablePackage, InstalledPackage, LeafArtifact, PackageIdentifier
from leaf.model.steps import StepExecutor, VariableResolver
from leaf.rendering.formatutils import sizeof_fmt


class PackageManager(RemoteManager):

    """
    Main API for using Leaf package manager
    """

    def __init__(self):
        """
        Constructor
        """
        RemoteManager.__init__(self)
        self.__download_cache_folder = self.cache_folder / LeafFiles.CACHE_DOWNLOAD_FOLDERNAME
        self.__application_lock = LockFile(self.find_configuration_file(LeafFiles.LOCK_FILENAME))
        self.__check_cache_folder_size()

    @property
    def application_lock(self):
        return self.__application_lock

    @property
    def download_cache_folder(self):
        return mkdirs(self.__download_cache_folder)

    def __check_cache_folder_size(self):
        # Check if it has been checked recently
        if self.is_file_outdated(self.download_cache_folder):
            # Compute the folder total size
            totalsize = fs_compute_total_size(self.download_cache_folder)
            if totalsize > LeafConstants.CACHE_SIZE_MAX:
                # Display a message
                self.logger.print_error("You can save {size} by cleaning the leaf cache folder".format(size=sizeof_fmt(totalsize)))
                self.print_hints("to clean the cache, you can run: 'rm -r {folder}'".format(folder=self.download_cache_folder))
                # Update the mtime
                self.download_cache_folder.touch()

    def list_available_packages(self, force_refresh=False) -> dict:
        """
        List all available package
        """
        out = OrderedDict()
        self.fetch_remotes(force_refresh=force_refresh)

        for remote in self.list_remotes(only_enabled=True).values():
            if remote.is_fetched:
                for ap in remote.available_packages:
                    if ap.identifier not in out:
                        out[ap.identifier] = ap
                    else:
                        ap2 = out[ap.identifier]
                        ap2.remotes.append(remote)
                        if ap.hashsum != ap2.hashsum:
                            self.logger.print_error(
                                "Package {ap.identifier} is available in several remotes with same version but different content!".format(ap=ap)
                            )
                            raise LeafException("Package {ap.identifier} has multiple artifacts for the same version".format(ap=ap))
                        # Keep tags
                        for t in ap.tags:
                            if t not in ap2.tags:
                                ap2.tags.append(t)

        if len(out) == 0:
            raise NoPackagesInCacheException()
        return out

    def __download_ap(self, ap: AvailablePackage) -> LeafArtifact:
        """
        Download given available package and returns the files in cache folder
        @return LeafArtifact
        """
        cachedfile = self.__download_cache_folder / get_cached_artifact_name(ap.filename, ap.hashsum)
        download_and_verify_file(ap.url, cachedfile, logger=self.logger, hashstr=ap.hashsum)
        return LeafArtifact(cachedfile)

    def __extract_artifact(
        self, la: LeafArtifact, env: Environment, install_folder: Path, ipmap: dict = None, keep_folder_on_error: bool = False
    ) -> InstalledPackage:
        """
        Install a leaf artifact
        @return InstalledPackage
        """
        target_folder = install_folder / str(la.identifier)
        if target_folder.is_dir():
            raise LeafException("Folder already exists: {folder}".format(folder=target_folder))

        # Check already installed
        ipmap = ipmap or self.list_installed_packages()
        if la.identifier in ipmap:
            raise LeafException("Package is already installed: {la.identifier}".format(la=la))

        # Check leaf min version
        min_version = check_leaf_min_version([la])
        if min_version:
            raise LeafOutOfDateException("You need to upgrade leaf to v{version} to install {la.identifier}".format(version=min_version, la=la))

        # Create folder
        target_folder.mkdir(parents=True)

        try:
            # Extract content
            self.logger.print_verbose("Extract {la.path} in {dest}".format(la=la, dest=target_folder))
            with TarFile.open(str(la.path)) as tf:
                tf.extractall(str(target_folder))
            # Execute post install steps
            out = InstalledPackage(target_folder / LeafFiles.MANIFEST)
            ipmap[out.identifier] = out
            self.__execute_steps(out.identifier, ipmap, StepExecutor.install, env=env)
            # Touch folder to trigger FS event
            target_folder.touch(exist_ok=True)
            return out
        except Exception as e:
            self.logger.print_error("Error during installation:", e)
            if keep_folder_on_error:
                target_folder = mark_folder_as_ignored(target_folder)
                self.logger.print_verbose("Mark folder as ignored: {folder}".format(folder=target_folder))
            else:
                self.logger.print_verbose("Remove folder: {folder}".format(folder=target_folder))
                rmtree_force(target_folder)
            raise e

    def install_prereq(self, pilist: list, tmp_install_folder: Path, apmap: dict = None, env: Environment = None, raise_on_error: bool = True):
        """
        Install given prereg available package in alternative root folder
        @return: error count
        """
        if apmap is None:
            apmap = self.list_available_packages()

        # Get packages to install
        aplist = [find_manifest(pi, apmap) for pi in pilist]

        errors = 0
        if len(aplist) > 0:
            self.logger.print_verbose("Installing {count} pre-required package(s) in {folder}".format(count=len(aplist), folder=tmp_install_folder))
            if env is None:
                env = Environment.build(self.build_builtin_environment(), self.build_user_environment())
            env.append(Environment("Prereq", {"LEAF_PREREQ_ROOT": tmp_install_folder}))
            for prereqap in aplist:
                try:
                    prereqla = self.__download_ap(prereqap)
                    prereqip = self.__extract_artifact(prereqla, env, tmp_install_folder, keep_folder_on_error=True)
                    self.logger.print_verbose("Prereq package {ip.identifier} is OK".format(ip=prereqip))
                except Exception as e:
                    if raise_on_error:
                        raise e
                    self.logger.print_verbose("Prereq package {ap.identifier} has error: {error}".format(ap=prereqap, error=e))
                    errors += 1
        return errors

    def install_packages(self, pilist: list, env: Environment = None, keep_folder_on_error: bool = False):
        """
        Compute dependency tree, check compatibility, download from remotes and extract needed packages
        @return: InstalledPackage list
        """
        with self.application_lock.acquire():
            prereq_install_folder = None
            ipmap = self.list_installed_packages()
            apmap = self.list_available_packages()
            out = []

            # Build env to resolve dynamic dependencies
            if env is None:
                env = Environment.build(self.build_builtin_environment(), self.build_user_environment())

            try:
                ap_to_install = DependencyUtils.install(pilist, apmap, ipmap, env=env)

                # Check leaf min version
                min_version = check_leaf_min_version(ap_to_install)
                if min_version:
                    raise LeafOutOfDateException(
                        "You need to upgrade leaf to v{version} to install {text}".format(
                            version=min_version, text=", ".join([str(ap.identifier) for ap in ap_to_install])
                        )
                    )

                # Check nothing to do
                if len(ap_to_install) == 0:
                    self.logger.print_default("All packages are installed")
                else:
                    # Check available size
                    download_totalsize = 0
                    for ap in ap_to_install:
                        if ap.size is not None:
                            download_totalsize += ap.size
                    fs_check_free_space(self.download_cache_folder, download_totalsize)

                    # Confirm
                    text = ", ".join([str(ap.identifier) for ap in ap_to_install])
                    self.logger.print_quiet("Packages to install: {packages}".format(packages=text))
                    if download_totalsize > 0:
                        self.logger.print_default("Total size:", sizeof_fmt(download_totalsize))
                    self.print_with_confirm(raise_on_decline=True)

                    # Install prereq
                    prereq_to_install = DependencyUtils.prereq(pilist, apmap, ipmap, env=env)

                    if len(prereq_to_install) > 0:
                        self.logger.print_default("Check required packages")
                        prereq_install_folder = mkdir_tmp_leaf_dir()
                        self.install_prereq([p.identifier for p in prereq_to_install], prereq_install_folder, apmap=apmap, env=env)

                    # Download ap list
                    self.logger.print_default("Downloading {size} package(s)".format(size=len(ap_to_install)))
                    la_to_install = []
                    for ap in ap_to_install:
                        la_to_install.append(self.__download_ap(ap))

                    # Check the extracted size
                    extracted_totalsize = 0
                    for la in la_to_install:
                        if la.final_size is not None:
                            extracted_totalsize += la.final_size
                        else:
                            extracted_totalsize += la.get_total_size()
                    fs_check_free_space(self.install_folder, extracted_totalsize)

                    # Extract la list
                    for la in la_to_install:
                        self.logger.print_default(
                            "[{current}/{total}] Installing {la.identifier}".format(current=(len(out) + 1), total=len(la_to_install), la=la)
                        )
                        ip = self.__extract_artifact(la, env, self.install_folder, ipmap=ipmap, keep_folder_on_error=keep_folder_on_error)
                        out.append(ip)

            finally:
                if not keep_folder_on_error and prereq_install_folder is not None:
                    self.logger.print_verbose("Remove prereq root folder {folder}".format(folder=prereq_install_folder))
                    rmtree_force(prereq_install_folder)

            return out

    def uninstall_packages(self, pilist: list):
        """
        Remove given package
        """
        with self.application_lock.acquire():
            ipmap = self.list_installed_packages()

            iplist_to_remove = DependencyUtils.uninstall(pilist, ipmap, logger=self.logger)

            if len(iplist_to_remove) == 0:
                self.logger.print_default("No package to remove")
            else:
                # Confirm
                text = ", ".join([str(ip.identifier) for ip in iplist_to_remove])
                self.logger.print_quiet("Packages to uninstall: {packages}".format(packages=text))
                self.print_with_confirm(raise_on_decline=True)
                for ip in iplist_to_remove:
                    if ip.read_only:
                        raise LeafException("Cannot uninstall system package {ip.identifier}".format(ip=ip))
                    self.logger.print_default("Removing {ip.identifier}".format(ip=ip))
                    self.__execute_steps(ip.identifier, ipmap, StepExecutor.uninstall)
                    self.logger.print_verbose("Remove folder: {ip.folder}".format(ip=ip))
                    rmtree_force(ip.folder)
                    del ipmap[ip.identifier]

                self.logger.print_default("{count} package(s) removed".format(count=len(iplist_to_remove)))

    def sync_packages(self, pilist: list, env: Environment = None):
        """
        Run the sync steps for all given packages
        """
        ipmap = self.list_installed_packages()
        for pi in pilist:
            self.logger.print_verbose("Sync package {pi}".format(pi=pi))
            self.__execute_steps(pi, ipmap, StepExecutor.sync, env=env)

    def __execute_steps(self, pi: PackageIdentifier, ipmap: dict, se_func: callable, env: Environment = None):
        # Find the package
        ip = find_manifest(pi, ipmap)
        # The environment
        if env is None:
            env = Environment.build(self.build_builtin_environment(), self.build_user_environment())
        # build the dependencies
        deps = DependencyUtils.installed([pi], ipmap, env=env, ignore_unknown=True)
        # Update env
        env.append(self.build_packages_environment(deps))
        # The Variable resolver
        vr = VariableResolver(ip, ipmap.values())
        # Execute steps
        se = StepExecutor(self.logger, ip, vr, env=env)
        se_func(se)

    def build_packages_environment(self, items: list, ipmap=None):
        """
        Get the env vars declared by given packages
        @param items: a list of InstalledPackage or PackageIdentifier
        """
        ipmap = ipmap or self.list_installed_packages()
        out = Environment()
        for item in items:
            ip = None
            if isinstance(item, InstalledPackage):
                ip = item
            elif isinstance(item, PackageIdentifier):
                ip = None
                if is_latest_package(item):
                    ip = find_manifest(item, ipmap)
                else:
                    ip = ipmap.get(item)
                if ip is None:
                    raise InvalidPackageNameException(item)
            else:
                raise InvalidPackageNameException(item)
            vr = VariableResolver(ip, ipmap.values())
            out.append(ip.build_environment(vr=vr.resolve))
        return out
