'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import shutil
from builtins import Exception
from collections import OrderedDict
from datetime import datetime
from tarfile import TarFile

from leaf.api.remotes import RemoteManager
from leaf.core.constants import LeafConstants, LeafFiles
from leaf.model.dependencies import DependencyUtils
from leaf.core.error import (InvalidPackageNameException, LeafException,
                             LeafOutOfDateException,
                             NoPackagesInCacheException)
from leaf.core.lock import LockFile
from leaf.core.utils import (downloadFile, getCachedArtifactName, getTotalSize,
                             isFolderIgnored, markFolderAsIgnored,
                             mkTmpLeafRootDir)
from leaf.model.environment import Environment
from leaf.model.modelutils import findManifest, isLatestPackage
from leaf.model.package import (AvailablePackage, InstalledPackage,
                                LeafArtifact, PackageIdentifier)
from leaf.model.steps import StepExecutor, VariableResolver
from leaf.rendering.formatutils import sizeof_fmt


class PackageManager(RemoteManager):
    '''
    Main API for using Leaf package manager
    '''

    def __init__(self):
        '''
        Constructor
        '''
        RemoteManager.__init__(self)
        self.downloadCacheFolder = self.cacheFolder / LeafFiles.CACHE_DOWNLOAD_FOLDERNAME
        self.applicationLock = LockFile(
            self.configurationFolder / LeafFiles.LOCK_FILENAME)
        self._checkCacheFolderSize()

    def _checkCacheFolderSize(self):
        # Check if the download cache folder exists
        if self.downloadCacheFolder.exists():
            # Check if it has been checked recently
            if datetime.fromtimestamp(self.downloadCacheFolder.stat().st_mtime) < datetime.now() - LeafConstants.CACHE_DELTA:
                # Compute the folder total size
                cacheSize = getTotalSize(self.downloadCacheFolder)
                if cacheSize > LeafConstants.CACHE_SIZE_MAX:
                    # Display a message
                    self.logger.printError(
                        "You can save %s by cleaning the leaf cache folder" % sizeof_fmt(cacheSize))
                    self.printHints(
                        "to clean the cache, you can run: 'rm -r %s'" % self.downloadCacheFolder)
                    # Update the mtime
                    self.downloadCacheFolder.touch()

    def getInstallFolder(self):
        out = self.readConfiguration().getRootFolder()
        if not out.exists():
            out.mkdir()
        return out

    def setInstallFolder(self, folder):
        usrc = self.readConfiguration()
        usrc.setRootFolder(folder)
        self.writeConfiguration(usrc)

    def listAvailablePackages(self, smartRefresh=True):
        '''
        List all available package
        '''
        out = OrderedDict()
        self.fetchRemotes(smartRefresh=smartRefresh)

        for remote in self.listRemotes(onlyEnabled=True).values():
            if remote.isFetched():
                for apInfoJson in remote.getAvailablePackageList():
                    ap = AvailablePackage(apInfoJson, remote.getUrl())
                    ap.sourceRemotes.append(remote)
                    if ap.getIdentifier() not in out:
                        out[ap.getIdentifier()] = ap
                    else:
                        ap2 = out[ap.getIdentifier()]
                        ap2.sourceRemotes.append(remote)
                        if ap.getHash() != ap2.getHash():
                            self.logger.printError(
                                "Package %s is available in several remotes with same version but different content!" %
                                ap.getIdentifier())
                            raise LeafException(
                                "Package %s has multiple artifacts for the same version" %
                                ap.getIdentifier())
                        for tag in ap.getTags():
                            if tag not in ap2.getTags():
                                ap2.getTags().append(tag)

        if len(out) == 0:
            raise NoPackagesInCacheException()
        return out

    def listInstalledPackages(self):
        '''
        Return all installed packages
        @return: PackageIdentifier/InstalledPackage dict
        '''
        out = OrderedDict()
        for folder in self.getInstallFolder().iterdir():
            if folder.is_dir() and not isFolderIgnored(folder):
                manifest = folder / LeafFiles.MANIFEST
                if manifest.is_file():
                    ip = InstalledPackage(manifest)
                    out[ip.getIdentifier()] = ip
        return out

    def checkPackagesForInstall(self, mfList,
                                bypassLeafMinVersion=False):

        # Check leaf min version
        if not bypassLeafMinVersion:
            incompatibleList = [mf
                                for mf
                                in mfList
                                if not mf.isSupportedByCurrentLeafVersion()]
            if len(incompatibleList) > 0:
                self.logger.printError("These packages need a newer version: ",
                                       " ".join([str(mf.getIdentifier()) for mf in incompatibleList]))
                raise LeafOutOfDateException(
                    "Some package require a newer version of leaf")

    def downloadAvailablePackage(self, ap):
        '''
        Download given available package and returns the files in cache folder
        @return LeafArtifact
        '''
        filename = getCachedArtifactName(ap.getFilename(),
                                         ap.getHash())
        cachedFile = downloadFile(ap.getUrl(),
                                  self.downloadCacheFolder,
                                  self.logger,
                                  filename=filename,
                                  hash=ap.getHash())
        return LeafArtifact(cachedFile)

    def extractLeafArtifact(self, la, env,
                            keepFolderOnError=False,
                            altInstallFolder=None):
        '''
        Install a leaf artifact
        @return InstalledPackage
        '''
        if altInstallFolder is None:
            altInstallFolder = self.getInstallFolder()
        targetFolder = altInstallFolder / str(la.getIdentifier())
        if targetFolder.is_dir():
            raise LeafException("Folder already exists: " + str(targetFolder))

        # Create folder
        targetFolder.mkdir(parents=True)

        ipMap = self.listInstalledPackages()
        if la.getIdentifier() in ipMap:
            raise LeafException(
                "Package is already installed: %s" % la.getIdentifier())

        try:
            # Extract content
            self.logger.printVerbose("Extract %s in %s" %
                                     (la.path, targetFolder))
            with TarFile.open(str(la.path)) as tf:
                tf.extractall(str(targetFolder))
            # Execute post install steps
            out = InstalledPackage(targetFolder / LeafFiles.MANIFEST)
            ipMap[out.getIdentifier()] = out
            self._buildStepExecutorWithEnv(
                out.getIdentifier(), ipMap, env=env).postInstall()
            return out
        except Exception as e:
            self.logger.printError("Error during installation:", e)
            if keepFolderOnError:
                targetFolderIgnored = markFolderAsIgnored(targetFolder)
                self.logger.printVerbose(
                    "Mark folder as ignored: %s" % targetFolderIgnored)
            else:
                self.logger.printVerbose("Remove folder: %s" % targetFolder)
                shutil.rmtree(str(targetFolder), True)
            raise e

    def installPrereqFromRemotes(self, piList, tmpRootFolder,
                                 availablePackages=None,
                                 env=None,
                                 raiseOnError=True):
        '''
        Install given prereg available package in alternative root folder
        @return: error count
        '''
        if availablePackages is None:
            availablePackages = self.listAvailablePackages()

        # Get packages to install
        apList = [findManifest(pi, availablePackages) for pi in piList]

        errorCount = 0
        if len(apList) > 0:
            self.logger.printVerbose("Installing %d pre-required package(s) in %s" %
                                     (len(apList), tmpRootFolder))
            if env is None:
                env = Environment.build(self.getBuiltinEnvironment(),
                                        self.getUserEnvironment())
            env.addSubEnv(Environment("Prereq",
                                      {"LEAF_PREREQ_ROOT": tmpRootFolder}))
            for prereqAp in apList:
                try:
                    prereqLa = self.downloadAvailablePackage(prereqAp)
                    prereqIp = self.extractLeafArtifact(prereqLa,
                                                        env,
                                                        keepFolderOnError=True,
                                                        altInstallFolder=tmpRootFolder)
                    self.logger.printVerbose("Prereq package %s is OK" %
                                             prereqIp.getIdentifier())
                except Exception as e:
                    if raiseOnError:
                        raise e
                    self.logger.printVerbose("Prereq package %s has error: %s" %
                                             (prereqAp.getIdentifier(), e))
                    errorCount += 1
        return errorCount

    def installFromRemotes(self, piList,
                           env=None,
                           keepFolderOnError=False):
        '''
        Compute dependency tree, check compatibility, download from remotes and extract needed packages
        @return: InstalledPackage list
        '''
        with self.applicationLock.acquire():
            prereqRootFolder = None
            installedPackages = self.listInstalledPackages()
            availablePackages = self.listAvailablePackages()
            out = []

            # Build env to resolve dynamic dependencies
            if env is None:
                env = Environment.build(self.getBuiltinEnvironment(),
                                        self.getUserEnvironment())

            try:
                apToInstall = DependencyUtils.install(piList,
                                                      availablePackages,
                                                      installedPackages,
                                                      env=env)

                # Check nothing to do
                if len(apToInstall) == 0:
                    self.logger.printDefault("All packages are installed")
                else:
                    # Check ap list can be installed
                    self.checkPackagesForInstall(apToInstall)

                    # Confirm
                    self.logger.printQuiet("Packages to install:",
                                           ", ".join([str(ap.getIdentifier())for ap in apToInstall]))
                    totalSize = 0
                    for ap in apToInstall:
                        if ap.getSize() is not None:
                            totalSize += ap.getSize()
                    if totalSize > 0:
                        self.logger.printDefault(
                            "Total size:", sizeof_fmt(totalSize))
                    self.confirm(raiseOnDecline=True)

                    # Install prereq
                    prereqApList = DependencyUtils.prereq(piList,
                                                          availablePackages,
                                                          installedPackages,
                                                          env=env)

                    if len(prereqApList) > 0:
                        self.logger.printDefault("Check required packages")
                        prereqRootFolder = mkTmpLeafRootDir()
                        self.installPrereqFromRemotes(
                            [prereqAp.getIdentifier()
                             for prereqAp in prereqApList],
                            prereqRootFolder,
                            availablePackages=availablePackages,
                            env=env)

                    # Download ap list
                    self.logger.printDefault(
                        "Downloading %d package(s)" % len(apToInstall))
                    laList = []
                    for ap in apToInstall:
                        la = self.downloadAvailablePackage(ap)
                        laList.append(la)

                    # Extract la list
                    for la in laList:
                        self.logger.printDefault(
                            "[%d/%d] Installing %s" % (
                                len(out) + 1, len(laList), la.getIdentifier()))
                        ip = self.extractLeafArtifact(
                            la, env,
                            keepFolderOnError=keepFolderOnError)
                        out.append(ip)

            finally:
                if not keepFolderOnError and prereqRootFolder is not None:
                    self.logger.printVerbose("Remove prereq root folder %s" %
                                             prereqRootFolder)
                    shutil.rmtree(str(prereqRootFolder), True)

            return out

    def uninstallPackages(self, piList):
        '''
        Remove given package
        '''
        with self.applicationLock.acquire():
            ipMap = self.listInstalledPackages()

            ipToRemove = DependencyUtils.uninstall(piList, ipMap)

            if len(ipToRemove) == 0:
                self.logger.printDefault(
                    "No package to remove (to keep dependencies)")
            else:
                # Confirm
                self.logger.printQuiet("Packages to uninstall:",
                                       ", ".join([str(ip.getIdentifier()) for ip in ipToRemove]))
                self.confirm(raiseOnDecline=True)
                for ip in ipToRemove:
                    self.logger.printDefault("Removing", ip.getIdentifier())
                    self._buildStepExecutorWithEnv(
                        ip.getIdentifier(), ipMap).preUninstall()
                    self.logger.printVerbose("Remove folder:", ip.folder)
                    shutil.rmtree(str(ip.folder))
                    del ipMap[ip.getIdentifier()]

                self.logger.printDefault(
                    "%d package(s) removed" % len(ipToRemove))

    def syncPackages(self, piList, env=None):
        '''
        Run the sync steps for all given packages
        '''
        ipMap = self.listInstalledPackages()
        for pi in piList:
            self.logger.printVerbose("Sync package %s" % pi)
            self._buildStepExecutorWithEnv(pi, ipMap, env=env).sync()

    def _buildStepExecutorWithEnv(self,
                                  pi: PackageIdentifier,
                                  ipMap: dict,
                                  env: Environment = None) -> StepExecutor:
        # Find the package
        ip = findManifest(pi, ipMap)
        # The environment
        if env is None:
            env = Environment.build(self.getBuiltinEnvironment(),
                                    self.getUserEnvironment())
        # build the dependencies
        deps = DependencyUtils.installed(
            [pi], ipMap, env=env, ignoreUnknown=True)
        # Update env
        env.addSubEnv(self.getPackagesEnvironment(deps))
        # The Variable resolver
        vr = VariableResolver(ip, ipMap.values())
        # Execute steps
        return StepExecutor(self.logger, ip, vr, env=env)

    def getPackagesEnvironment(self, itemList):
        '''
        Get the env vars declared by given packages
        @param itemList: a list of InstalledPackage or PackageIdentifier
        '''
        installedPackages = self.listInstalledPackages()
        out = Environment()
        for item in itemList:
            ip = None
            if isinstance(item, InstalledPackage):
                ip = item
            elif isinstance(item, PackageIdentifier):
                ip = None
                if isLatestPackage(item):
                    ip = findManifest(item, installedPackages)
                else:
                    ip = installedPackages.get(item)
                if ip is None:
                    raise InvalidPackageNameException(item)
            else:
                raise InvalidPackageNameException(item)
            ipEnv = Environment("Exported by package %s" % ip.getIdentifier())
            out.addSubEnv(ipEnv)
            vr = VariableResolver(ip, installedPackages.values())
            for key, value in ip.getEnvMap().items():
                ipEnv.env.append((key, vr.resolve(value)))
        return out
