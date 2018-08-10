'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from builtins import filter
from collections import OrderedDict
from datetime import datetime
from tarfile import TarFile
from tempfile import NamedTemporaryFile
import json
import os
import platform
import shutil

import gnupg

from leaf import __version__
from leaf.constants import JsonConstants, LeafConstants, LeafFiles, EnvConstants
from leaf.core.coreutils import VariableResolver, StepExecutor
from leaf.core.dependencies import DependencyManager, DependencyType
from leaf.format.formatutils import sizeof_fmt
from leaf.format.logger import TextLogger
from leaf.format.theme import ThemeManager
from leaf.model.base import JsonObject
from leaf.model.config import UserConfiguration
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier, AvailablePackage, \
    InstalledPackage, LeafArtifact, Manifest
from leaf.model.remote import Remote
from leaf.utils import getAltEnvPath, jsonLoadFile, jsonWriteFile, \
    isFolderIgnored, getCachedArtifactName, markFolderAsIgnored,\
    mkTmpLeafRootDir, downloadFile, downloadData


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

        self.configurationFile = self.configurationFolder / \
            LeafFiles.CONFIG_FILENAME


class LoggerManager(_LeafBase):

    def __init__(self, verbosity, nonInteractive):
        _LeafBase.__init__(self)
        themesFile = self.configurationFolder / LeafFiles.THEMES_FILENAME
        self.themeManager = ThemeManager(themesFile)
        self.logger = TextLogger(verbosity, nonInteractive)
        self.nonInteractive = nonInteractive

    def printRenderer(self, renderer):
        renderer.verbosity = self.logger.getVerbosity()
        renderer.tm = self.themeManager
        renderer.print()


class GPGManager(LoggerManager):

    def __init__(self, verbosity, nonInteractive):
        LoggerManager.__init__(self, verbosity, nonInteractive)
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

    def __init__(self, verbosity, nonInteractive):
        GPGManager.__init__(self, verbosity, nonInteractive)
        '''
        Constructor
        '''
        self.remoteCacheFile = self.cacheFolder / \
            LeafFiles.CACHE_REMOTES_FILENAME

    def readConfiguration(self):
        '''
        Read the configuration if it exists, else return the the default configuration
        '''
        if not self.configurationFile.exists():
            # Default configuration here
            skel = UserConfiguration({})
            skel.setRootFolder(LeafFiles.DEFAULT_LEAF_ROOT)
            self.writeConfiguration(skel)

        return UserConfiguration(jsonLoadFile(self.configurationFile))

    def writeConfiguration(self, usrc):
        '''
        Write the given configuration
        '''
        jsonWriteFile(self.configurationFile, usrc.json, pp=True)

    def cleanRemotesCacheFile(self):
        if self.remoteCacheFile.exists():
            os.remove(str(self.remoteCacheFile))

    def listRemotes(self, onlyEnabled=False):
        out = OrderedDict()

        cache = None
        if self.remoteCacheFile.exists():
            cache = jsonLoadFile(self.remoteCacheFile)

        for alias, json in self.readConfiguration().getRemotesMap().items():
            remote = Remote(alias, json)
            if remote.isEnabled() or not onlyEnabled:
                out[alias] = remote
            url = remote.getUrl()
            if cache is not None and url in cache:
                remote.content = cache[url]

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
            for remote in self.listRemotes(onlyEnabled=True).values():
                try:
                    indexUrl = remote.getUrl()
                    data = downloadData(indexUrl)
                    gpgKey = remote.getGpgKey()
                    if gpgKey is not None:
                        signatureUrl = indexUrl + LeafConstants.GPG_SIG_EXTENSION
                        self.logger.printDefault(
                            "Verifying signature for remote %s" % remote.alias)
                        self.gpgImportKeys(gpgKey)
                        self.gpgVerifyContent(data,
                                              signatureUrl,
                                              expectedKey=gpgKey)
                    self.logger.printVerbose("Fetched", indexUrl)
                    content[indexUrl] = json.loads(data.decode())
                    self.logger.printDefault(
                        "Fetched content from %s" % remote.alias)
                except Exception as e:
                    self.logger.printError(
                        "Error fetching", indexUrl, ":", e)
            jsonWriteFile(self.remoteCacheFile, content)


class PackageManager(RemoteManager):
    '''
    Main API for using Leaf package manager
    '''

    def __init__(self, verbosity, nonInteractive):
        '''
        Constructor
        '''
        RemoteManager.__init__(self, verbosity, nonInteractive)
        self.downloadCacheFolder = self.cacheFolder / \
            LeafFiles.CACHE_DOWNLOAD_FOLDERNAME

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
        if self.nonInteractive:
            out.env.append(("LEAF_NON_INTERACTIVE", "1"))
        return out

    def getUserEnvironment(self):
        return self.readConfiguration().getEnvironment()

    def updateUserEnv(self, setMap=None, unsetList=None):
        usrc = self.readConfiguration()
        usrc.updateEnv(setMap, unsetList)
        self.writeConfiguration(usrc)

    def resolveLatest(self, motifList, ipMap=None, apMap=None):
        '''
        Search a package given a full packageidentifier
        or only a name (latest version will be returned then.
        @return: PackageIdentifier list
        '''
        out = []
        knownPiList = []
        if ipMap is True:
            ipMap = self.listInstalledPackages()
        if ipMap is not None:
            for pi in ipMap.keys():
                if pi not in knownPiList:
                    knownPiList.append(pi)
        if apMap is True:
            apMap = self.listAvailablePackages()
        if apMap is not None:
            for pi in apMap.keys():
                if pi not in knownPiList:
                    knownPiList.append(pi)
        knownPiList = sorted(knownPiList)
        for motif in motifList:
            pi = None
            if isinstance(motif, PackageIdentifier):
                pi = motif
            elif PackageIdentifier.isValidIdentifier(motif):
                pi = PackageIdentifier.fromString(motif)
            else:
                for pi in filter(lambda pi: pi.name == motif, knownPiList):
                    # loop to get the last item
                    pass
            if pi is None:
                raise ValueError("Cannot find package matching %s" % motif)
            if pi not in out:
                out.append(pi)
        return out

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
                        # Checks that aps are the same
                        if ap.getSha1sum() != ap2.getSha1sum():
                            self.logger.printError(
                                ("Package %s is available in several remotes " +
                                 "with same version but different content!") %
                                ap.getIdentifier())
                            raise ValueError(
                                "Package %s has multiple artifacts for the same version" %
                                ap.getIdentifier())
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

    def listDependencies(self, motifList, depType, envMap=None):
        '''
        List all dependencies for given packages
        @return: PackageIdentifier list
        '''
        installedPackages = self.listInstalledPackages()
        availablePackages = self.listAvailablePackages()
        piList = self.resolveLatest(motifList,
                                    ipMap=installedPackages,
                                    apMap=availablePackages)
        env = Environment.build(self.getLeafEnvironment(),
                                self.getUserEnvironment(),
                                Environment("Custom env", envMap))
        return DependencyManager.compute(piList, depType,
                                         apMap=availablePackages,
                                         ipMap=installedPackages,
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
                                         ap.getSha1sum())
        cachedFile = downloadFile(ap.getUrl(),
                                  self.downloadCacheFolder,
                                  self.logger,
                                  filename=filename,
                                  sha1sum=ap.getSha1sum())
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

    def installPrereqFromRemotes(self, motifList, tmpRootFolder,
                                 availablePackages=None,
                                 env=None,
                                 raiseOnError=True):
        '''
        Install given prereg available package in alternative root folder
        @return: error count
        '''

        if availablePackages is None:
            availablePackages = self.listAvailablePackages()

        piList = self.resolveLatest(motifList,
                                    apMap=availablePackages)

        # Get packages to install
        apList = [availablePackages[pi] for pi in piList]

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

    def installFromRemotes(self, motifList,
                           env=None,
                           keepFolderOnError=False):
        '''
        Compute dependency tree, check compatibility, download from remotes and extract needed packages
        @return: InstalledPackage list
        '''
        prereqRootFolder = None
        installedPackages = self.listInstalledPackages()
        availablePackages = self.listAvailablePackages()
        piList = self.resolveLatest(motifList,
                                    ipMap=installedPackages,
                                    apMap=availablePackages)
        try:
            # Build env to resolve dynamic dependencies
            if env is None:
                env = Environment.build(self.getLeafEnvironment(),
                                        self.getUserEnvironment())

            apToInstall = DependencyManager.compute(piList,
                                                    DependencyType.INSTALL,
                                                    apMap=availablePackages,
                                                    ipMap=installedPackages,
                                                    env=env)
            out = []

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
                    raise ValueError("Installation aborted")

                # Install prereq
                prereqApList = DependencyManager.compute(piList, DependencyType.PREREQ,
                                                         apMap=availablePackages,
                                                         ipMap=installedPackages,
                                                         env=env)

                if len(prereqApList) > 0:
                    prereqRootFolder = mkTmpLeafRootDir()
                    self.installPrereqFromRemotes(map(Manifest.getIdentifier, prereqApList),
                                                  prereqRootFolder,
                                                  availablePackages=availablePackages,
                                                  env=env)

                self.logger.progressWorked(message="Required packages checked",
                                           worked=1,
                                           total=len(apToInstall) * 2 + 1)

                # Download ap list
                laList = []
                for ap in apToInstall:
                    la = self.downloadAvailablePackage(ap)
                    laList.append(la)
                    self.logger.progressWorked(message="Downloaded %s" % ap.getIdentifier(),
                                               worked=len(laList) + 1,
                                               total=len(apToInstall) * 2 + 1)

                # Extract la list
                for la in laList:
                    ip = self.extractLeafArtifact(la, env,
                                                  keepFolderOnError=keepFolderOnError)
                    out.append(ip)
                    self.logger.progressWorked(message="Installed %s" % la.getIdentifier(),
                                               worked=len(laList) +
                                               len(out) + 1,
                                               total=len(apToInstall) * 2 + 1)

        finally:
            if not keepFolderOnError and prereqRootFolder is not None:
                self.logger.printVerbose("Remove prereq root folder %s" %
                                         prereqRootFolder)
                shutil.rmtree(str(prereqRootFolder), True)

        return out

    def uninstallPackages(self, motifList):
        '''
        Remove given package
        '''
        installedPackages = self.listInstalledPackages()
        piList = self.resolveLatest(motifList, ipMap=installedPackages)

        ipToRemove = DependencyManager.compute(piList,
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
                raise ValueError("Operation aborted")

            total = len(ipToRemove)
            worked = 0
            env = Environment.build(self.getLeafEnvironment(),
                                    self.getUserEnvironment())
            for ip in ipToRemove:
                self.logger.printDefault("Removing", ip.getIdentifier())
                vr = VariableResolver(ip,
                                      self.listInstalledPackages().values())
                stepExec = StepExecutor(self.logger, ip, vr, env=env)
                stepExec.preUninstall()
                self.logger.printVerbose("Remove folder:", ip.folder)
                shutil.rmtree(str(ip.folder))
                worked += 1
                self.logger.progressWorked(worked=worked,
                                           total=total)
                del installedPackages[ip.getIdentifier()]
            self.logger.printDefault(
                "%d package(s) removed" % (len(ipToRemove)))

    def syncPackages(self, pisList, env=None):

        ipMap = self.listInstalledPackages()

        if env is None:
            env = Environment.build(self.getLeafEnvironment(),
                                    self.getUserEnvironment())

        for pis in pisList:
            pi = PackageIdentifier.fromString(pis)
            ip = ipMap.get(pi)
            if ip is None:
                raise ValueError("Cannot find package %s", pis)
            self.logger.printVerbose("Sync package %s" % pis)
            vr = VariableResolver(ip,
                                  self.listInstalledPackages().values())
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
