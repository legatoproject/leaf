'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import json
import os
import platform
import shutil
from builtins import Exception
from collections import OrderedDict
from datetime import datetime
from tarfile import TarFile
from tempfile import NamedTemporaryFile

import gnupg

from leaf import __version__
from leaf.constants import (EnvConstants, JsonConstants, LeafConstants,
                            LeafFiles)
from leaf.core.coreutils import StepExecutor, VariableResolver, retrievePackage
from leaf.core.dependencies import DependencyManager, DependencyType
from leaf.core.error import (BadRemoteUrlException, LeafException,
                             NoEnabledRemoteException,
                             NoPackagesInCacheException, NoRemoteException,
                             UserCancelException)
from leaf.format.formatutils import sizeof_fmt
from leaf.format.logger import TextLogger
from leaf.format.renderer.error import HintsRenderer, LeafExceptionRenderer
from leaf.format.theme import ThemeManager
from leaf.model.config import UserConfiguration
from leaf.model.environment import Environment
from leaf.model.package import (AvailablePackage, InstalledPackage,
                                LeafArtifact, PackageIdentifier)
from leaf.model.remote import Remote
from leaf.utils import (downloadData, downloadFile, getAltEnvPath,
                        getCachedArtifactName, getTotalSize, isFolderIgnored,
                        jsonLoadFile, jsonWriteFile, markFolderAsIgnored,
                        mkTmpLeafRootDir, versionComparator_lt)


class _LeafBase():
    def __init__(self):
        '''
        Constructor
        '''
        self.configurationFolder = getAltEnvPath(
            EnvConstants.CUSTOM_CONFIG,
            LeafFiles.DEFAULT_CONFIG_FOLDER,
            mkdirIfNeeded=True)
        self.cacheFolder = getAltEnvPath(
            EnvConstants.CUSTOM_CACHE,
            LeafFiles.DEFAULT_CACHE_FOLDER,
            mkdirIfNeeded=True)

    def _getSkelConfigurationFile(self, filename):
        '''
        Try to find a default configuration file
        '''
        if filename in LeafFiles.SKEL_FILES:
            for candidate in LeafFiles.SKEL_FILES[filename]:
                if candidate.exists():
                    return candidate

    def getConfigurationFile(self, filename, checkExists=False):
        '''
        Return the path of a configuration file.
        If checkExists arg is True and the file does not exists, returns None
        '''
        out = self.configurationFolder / filename
        if checkExists and not out.exists():
            return None
        return out


class LoggerManager(_LeafBase):

    def __init__(self, verbosity):
        _LeafBase.__init__(self)
        themesFile = self.getConfigurationFile(
            LeafFiles.THEMES_FILENAME, checkExists=True)
        # If the theme file does not exists, try to find a skeleton
        if themesFile is None:
            themesFile = self._getSkelConfigurationFile(
                LeafFiles.THEMES_FILENAME)
        self.themeManager = ThemeManager(themesFile)
        self.logger = TextLogger(verbosity)

    def printHints(self, *hints):
        tr = HintsRenderer()
        tr.extend(hints)
        self.printRenderer(tr)

    def printException(self, ex):
        if isinstance(ex, LeafException):
            self.printRenderer(LeafExceptionRenderer(ex))
        else:
            self.logger.printError(str(ex))

    def printRenderer(self, renderer):
        renderer.verbosity = self.logger.getVerbosity()
        renderer.tm = self.themeManager
        renderer.print()


class GPGManager(LoggerManager):

    def __init__(self, verbosity):
        LoggerManager.__init__(self, verbosity)
        self.gpgHome = self.configurationFolder / LeafFiles.GPG_DIRNAME
        if not self.gpgHome.is_dir():
            self.gpgHome.mkdir(mode=0o700)

        self.gpg = gnupg.GPG(gnupghome=str(self.gpgHome))
        self.gpgDefaultKeyserver = os.environ.get(
            EnvConstants.GPG_KEYSERVER,
            LeafConstants.DEFAULT_GPG_KEYSERVER)

    def gpgVerifyContent(self, data, sigUrl, expectedKey=None):
        self.logger.printVerbose(
            "Known GPG keys:", len(self.gpg.list_keys()))
        with NamedTemporaryFile() as sigFile:
            downloadData(sigUrl, sigFile.name)
            verif = self.gpg.verify_data(sigFile.name, data)
            if verif.valid:
                self.logger.printVerbose(
                    "Content has been signed by %s (%s)" %
                    (verif.username, verif.pubkey_fingerprint))
                if expectedKey is not None:
                    if expectedKey != verif.pubkey_fingerprint:
                        raise ValueError(
                            "Content is not signed with %s" % expectedKey)
            else:
                raise ValueError("Signed content could not be verified")

    def gpgImportKeys(self, *keys, keyserver=None):
        if keyserver is None:
            keyserver = self.gpgDefaultKeyserver
        if len(keys) > 0:
            self.logger.printVerbose(
                "Update GPG keys for %s from %s" %
                (", ".join(keys), keyserver))
            gpgImport = self.gpg.recv_keys(keyserver, *keys)
            for result in gpgImport.results:
                if 'ok' in result:
                    self.logger.printVerbose(
                        "Received GPG key {fingerprint}".format(**result))
                else:
                    raise ValueError(
                        "Error receiving GPG keys: {text}".format(**result))


class RemoteManager(GPGManager):

    def __init__(self, verbosity):
        GPGManager.__init__(self, verbosity)
        '''
        Constructor
        '''
        self.remoteCacheFile = self.cacheFolder / \
            LeafFiles.CACHE_REMOTES_FILENAME

    def readConfiguration(self):
        '''
        Read the configuration if it exists, else return the the default configuration
        '''
        return UserConfiguration(
            self._getSkelConfigurationFile(LeafFiles.CONFIG_FILENAME),
            self.getConfigurationFile(LeafFiles.CONFIG_FILENAME))

    def writeConfiguration(self, usrc):
        '''
        Write the given configuration
        '''
        skelFile = self._getSkelConfigurationFile(LeafFiles.CONFIG_FILENAME)
        usrc.writeLayerToFile(
            self.getConfigurationFile(LeafFiles.CONFIG_FILENAME),
            previousLayerFile=skelFile,
            pp=True)

    def cleanRemotesCacheFile(self):
        if self.remoteCacheFile.exists():
            os.remove(str(self.remoteCacheFile))

    def listRemotes(self, onlyEnabled=False):
        out = OrderedDict()

        cache = None
        if self.remoteCacheFile.exists():
            cache = jsonLoadFile(self.remoteCacheFile)

        items = self.readConfiguration().getRemotesMap().items()
        if len(items) == 0:
            raise NoRemoteException()
        for alias, jsondata in items:
            remote = Remote(alias, jsondata)
            if remote.isEnabled() or not onlyEnabled:
                out[alias] = remote
            url = remote.getUrl()
            if cache is not None and url in cache:
                remote.content = cache[url]

        if len(out) == 0 and onlyEnabled:
            raise NoEnabledRemoteException()
        return out

    def createRemote(self, alias, url, enabled=True, insecure=False, gpgKey=None):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if alias in remotes:
            raise ValueError("Remote %s already exists" % alias)
        if insecure:
            remotes[alias] = {JsonConstants.CONFIG_REMOTE_URL: str(url),
                              JsonConstants.CONFIG_REMOTE_ENABLED: enabled}
        elif gpgKey is not None:
            remotes[alias] = {JsonConstants.CONFIG_REMOTE_URL: str(url),
                              JsonConstants.CONFIG_REMOTE_ENABLED: enabled,
                              JsonConstants.CONFIG_REMOTE_GPGKEY: gpgKey}
        else:
            raise ValueError("Invalid security for remote %s" % alias)
        # Save and clean cache
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def renameRemote(self, oldalias, newalias):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if oldalias not in remotes:
            raise ValueError("Cannot find remote %s" % oldalias)
        if newalias in remotes:
            raise ValueError("Remote %s already exists" % newalias)
        remotes[newalias] = remotes[oldalias]
        del remotes[oldalias]
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def updateRemote(self, remote):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if remote.alias not in remotes:
            raise ValueError("Cannot find remote %s" % remote.alias)
        remotes[remote.alias] = remote.json
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def deleteRemote(self, alias):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if alias not in remotes:
            raise ValueError("Cannot find remote %s" % alias)
        del remotes[alias]
        self.writeConfiguration(usrc)
        self.cleanRemotesCacheFile()

    def fetchRemotes(self, smartRefresh=True):
        '''
        Refresh remotes content with smart refresh, ie auto refresh after X days
        '''
        if self.remoteCacheFile.exists():
            if not smartRefresh:
                os.remove(str(self.remoteCacheFile))
            elif datetime.fromtimestamp(self.remoteCacheFile.stat().st_mtime) < datetime.now() - LeafConstants.CACHE_DELTA:
                self.logger.printDefault("Cache file is outdated")
                os.remove(str(self.remoteCacheFile))
        if not self.remoteCacheFile.exists():
            self.logger.printDefault("Refreshing available packages...")
            content = OrderedDict()
            remotes = self.listRemotes(onlyEnabled=True)
            if len(remotes) == 0:
                raise ValueError(
                    "No remote configured, first add or enable at least one remote (see 'leaf help remote')")
            for alias, remote in remotes.items():
                try:
                    indexUrl = remote.getUrl()
                    data = downloadData(indexUrl)
                    gpgKey = remote.getGpgKey()
                    if gpgKey is not None:
                        signatureUrl = indexUrl + LeafConstants.GPG_SIG_EXTENSION
                        self.logger.printDefault(
                            "Verifying signature for remote %s" % alias)
                        self.gpgImportKeys(gpgKey)
                        self.gpgVerifyContent(data,
                                              signatureUrl,
                                              expectedKey=gpgKey)
                    self.logger.printVerbose("Fetched", indexUrl)
                    jsonData = json.loads(data.decode())
                    self._checkRemoteContent(alias, indexUrl, jsonData)
                    content[indexUrl] = jsonData
                    self.logger.printDefault(
                        "Fetched content from %s" % alias)
                except Exception as e:
                    self.printException(BadRemoteUrlException(remote, e))
            if len(content) > 0:
                jsonWriteFile(self.remoteCacheFile, content)

    def _checkRemoteContent(self, alias, url, jsonContent):
        # Check leaf min version for all packages
        remote = Remote("", None)
        remote.content = jsonContent
        leafMinVersion = None
        for apInfoJson in remote.getAvailablePackageList():
            ap = AvailablePackage(apInfoJson, url)
            if not ap.isSupportedByCurrentLeafVersion():
                if leafMinVersion is None or versionComparator_lt(leafMinVersion, ap.getSupportedLeafVersion()):
                    leafMinVersion = ap.getSupportedLeafVersion()
        if leafMinVersion is not None:
            raise ValueError(
                "You need to upgrade leaf v%s to use packages from %s" % (leafMinVersion, alias))


class PackageManager(RemoteManager):
    '''
    Main API for using Leaf package manager
    '''

    def __init__(self, verbosity):
        '''
        Constructor
        '''
        RemoteManager.__init__(self, verbosity)
        self.downloadCacheFolder = self.cacheFolder / \
            LeafFiles.CACHE_DOWNLOAD_FOLDERNAME
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

    def getLeafEnvironment(self):
        out = Environment("Leaf built-in variables")
        out.env.append(("LEAF_VERSION", str(__version__)))
        out.env.append(("LEAF_PLATFORM_SYSTEM", platform.system()))
        out.env.append(("LEAF_PLATFORM_MACHINE", platform.machine()))
        out.env.append(("LEAF_PLATFORM_RELEASE", platform.release()))
        if EnvConstants.NON_INTERACTIVE in os.environ:
            out.env.append((EnvConstants.NON_INTERACTIVE,
                            os.getenv(EnvConstants.NON_INTERACTIVE)))
        return out

    def getUserEnvironment(self):
        return self.readConfiguration().getEnvironment()

    def updateUserEnv(self, setMap=None, unsetList=None):
        usrc = self.readConfiguration()
        usrc.updateEnv(setMap, unsetList)
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
                            raise ValueError(
                                "Package %s has multiple artifacts for the same version" %
                                ap.getIdentifier())

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

    def listDependencies(self, piList, depType, envMap=None):
        '''
        List all dependencies for given packages
        @return: PackageIdentifier list
        '''
        env = Environment.build(self.getLeafEnvironment(),
                                self.getUserEnvironment(),
                                Environment("Custom env", envMap))
        return DependencyManager.compute(
            piList,
            depType,
            apMap=self.listAvailablePackages(),
            ipMap=self.listInstalledPackages(),
            env=env,
            ignoreUnknown=True)

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
                raise ValueError(
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
            raise ValueError("Folder already exists: " + str(targetFolder))

        # Create folder
        targetFolder.mkdir(parents=True)

        try:
            # Extract content
            self.logger.printVerbose("Extract %s in %s" %
                                     (la.path, targetFolder))
            with TarFile.open(str(la.path)) as tf:
                tf.extractall(str(targetFolder))

            # Execute post install steps
            out = InstalledPackage(targetFolder / LeafFiles.MANIFEST)
            vr = VariableResolver(out,
                                  self.listInstalledPackages().values())
            se = StepExecutor(self.logger,
                              out,
                              vr,
                              env=env)
            se.postInstall()
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
        apList = [retrievePackage(pi, availablePackages) for pi in piList]

        errorCount = 0
        if len(apList) > 0:
            self.logger.printVerbose("Installing %d pre-required package(s) in %s" %
                                     (len(apList), tmpRootFolder))
            if env is None:
                env = Environment.build(self.getLeafEnvironment(),
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
        prereqRootFolder = None
        installedPackages = self.listInstalledPackages()
        availablePackages = self.listAvailablePackages()
        out = []

        # Build env to resolve dynamic dependencies
        if env is None:
            env = Environment.build(self.getLeafEnvironment(),
                                    self.getUserEnvironment())

        try:
            apToInstall = DependencyManager.compute(piList,
                                                    DependencyType.INSTALL,
                                                    apMap=availablePackages,
                                                    ipMap=installedPackages,
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
                if not self.logger.confirm():
                    raise UserCancelException()

                # Install prereq
                prereqApList = DependencyManager.compute(piList, DependencyType.PREREQ,
                                                         apMap=availablePackages,
                                                         ipMap=installedPackages,
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
        installedPackages = self.listInstalledPackages()

        ipToRemove = DependencyManager.compute(
            piList,
            DependencyType.UNINSTALL,
            ipMap=installedPackages)

        if len(ipToRemove) == 0:
            self.logger.printDefault(
                "No package to remove (to keep dependencies)")
        else:
            # Confirm
            self.logger.printQuiet("Packages to uninstall:",
                                   ", ".join([str(ip.getIdentifier()) for ip in ipToRemove]))
            if not self.logger.confirm():
                raise UserCancelException()

            env = Environment.build(self.getLeafEnvironment(),
                                    self.getUserEnvironment())
            for ip in ipToRemove:
                self.logger.printDefault("Removing", ip.getIdentifier())
                vr = VariableResolver(
                    ip,
                    installedPackages.values())
                stepExec = StepExecutor(self.logger, ip, vr, env=env)
                stepExec.preUninstall()
                self.logger.printVerbose("Remove folder:", ip.folder)
                shutil.rmtree(str(ip.folder))
                del installedPackages[ip.getIdentifier()]

            self.logger.printDefault("%d package(s) removed" % len(ipToRemove))

    def syncPackages(self, piList, env=None):
        '''
        Run the sync steps for all given packages
        '''
        ipMap = self.listInstalledPackages()
        if env is None:
            env = Environment.build(self.getLeafEnvironment(),
                                    self.getUserEnvironment())

        for pi in piList:
            ip = retrievePackage(pi, ipMap)
            self.logger.printVerbose("Sync package %s" % ip.getIdentifier())
            vr = VariableResolver(ip, ipMap.values())
            stepExec = StepExecutor(self.logger, ip, vr, env=env)
            stepExec.sync()

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
                ip = installedPackages.get(item)
                if ip is None:
                    raise ValueError("Cannot find package %s" % item)
            else:
                raise ValueError("Invalid package %s" % item)
            ipEnv = Environment("Exported by package %s" % ip.getIdentifier())
            out.addSubEnv(ipEnv)
            vr = VariableResolver(ip, installedPackages.values())
            for key, value in ip.getEnvMap().items():
                ipEnv.env.append((key, vr.resolve(value)))
        return out
