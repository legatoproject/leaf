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
import json
import os
import platform
import shutil
import urllib.request

from leaf import __version__
from leaf.constants import JsonConstants, LeafConstants, LeafFiles, EnvConstants
from leaf.core.coreutils import VariableResolver, StepExecutor
from leaf.core.dependencies import DependencyManager, DependencyType
from leaf.format.formatutils import sizeof_fmt
from leaf.format.logger import TextLogger
from leaf.model.base import JsonObject
from leaf.model.config import UserConfiguration
from leaf.model.environment import Environment
from leaf.model.package import PackageIdentifier, AvailablePackage, \
    InstalledPackage, LeafArtifact, Manifest
from leaf.model.remote import Remote
from leaf.utils import getAltEnvPath, jsonLoadFile, jsonWriteFile, resolveUrl,\
    isFolderIgnored, getCachedArtifactName, markFolderAsIgnored,\
    mkTmpLeafRootDir, downloadFile


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
        self.logger = TextLogger(verbosity, nonInteractive)
        self.nonInteractive = nonInteractive


class RemoteManager(LoggerManager):

    def __init__(self, verbosity, nonInteractive):
        LoggerManager.__init__(self, verbosity, nonInteractive)
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
        for alias, json in self.readConfiguration().getRemotesMap().items():
            remote = Remote(alias, json)
            if remote.isEnabled() or not onlyEnabled:
                out[alias] = remote
        if self.remoteCacheFile.exists():
            cache = jsonLoadFile(self.remoteCacheFile)
            for remote in out.values():
                if remote.getUrl() in cache and remote.isEnabled():
                    remote.content = cache[remote.getUrl()]
        return out

    def createRemote(self, alias, url, enabled=True):
        usrc = self.readConfiguration()
        remotes = usrc.getRemotesMap()
        if alias in remotes:
            raise ValueError("Remote %s already exists" % alias)
        remotes[alias] = {JsonConstants.CONFIG_REMOTE_URL: str(url),
                          JsonConstants.CONFIG_REMOTE_ENABLED: enabled}
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

    def recursiveFetchUrl(self, remoteurl, content):
        '''
        Fetch an URL content and keep it in the given dict
        '''
        if remoteurl not in content:
            try:
                with urllib.request.urlopen(remoteurl, timeout=LeafConstants.DOWNLOAD_TIMEOUT) as url:
                    data = json.loads(url.read().decode())
                    self.logger.printVerbose("Fetched", remoteurl)
                    content[remoteurl] = data
                    composites = data.get(JsonConstants.REMOTE_COMPOSITE)
                    if composites is not None:
                        for composite in composites:
                            self.recursiveFetchUrl(resolveUrl(
                                remoteurl, composite), content)
            except Exception as e:
                self.logger.printError("Error fetching", remoteurl, ":", e)

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
            content = OrderedDict()
            activeRemotes = self.listRemotes(onlyEnabled=True).values()

            self.logger.progressStart('Fetch remote(s)',
                                      message="Refreshing available packages...",
                                      total=len(activeRemotes))
            worked = 0
            for remote in activeRemotes:
                self.logger.printDefault("Fetching remote %s" % remote.alias)
                self.recursiveFetchUrl(remote.getUrl(), content)
                worked += 1
                self.logger.progressWorked('Fetch remote(s)',
                                           worked=worked,
                                           total=len(activeRemotes))
            jsonWriteFile(self.remoteCacheFile, content)
            self.logger.progressDone('Fetch remote(s)')


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

        if self.remoteCacheFile.exists():
            userRemotes = self.listRemotes(True).values()

            remotesMap = OrderedDict()
            for remoteUrl, remoteJson in jsonLoadFile(self.remoteCacheFile).items():
                remotesMap[remoteUrl] = JsonObject(remoteJson)

            # Build the links between remote and parent remotes
            parentsTree = {}
            for remoteUrl, remoteModel in remotesMap.items():
                for subPath in remoteModel.jsonget(JsonConstants.REMOTE_COMPOSITE, []):
                    compositeUrl = resolveUrl(remoteUrl, subPath)
                    if compositeUrl not in parentsTree:
                        parentsTree[compositeUrl] = []
                    if remoteUrl not in parentsTree[compositeUrl]:
                        parentsTree[compositeUrl].append(remoteUrl)

            def retrieveSourceRemotes(remoteUrl, acc):
                # Check is URL is a user remote
                for remote in userRemotes:
                    if remote.getUrl() == remoteUrl and remote not in acc:
                        acc.append(remote)
                # Visit all
                if remoteUrl in parentsTree:
                    for parentUrl in parentsTree[remoteUrl]:
                        retrieveSourceRemotes(parentUrl, acc)

            for remoteUrl, remoteModel in remotesMap.items():
                for pkgInfoJson in remoteModel.jsonget(JsonConstants.REMOTE_PACKAGES, []):
                    ap = AvailablePackage(pkgInfoJson, remoteUrl)
                    if ap.getIdentifier() not in out:
                        out[ap.getIdentifier()] = ap
                    else:
                        ap = out[ap.getIdentifier()]
                    retrieveSourceRemotes(remoteUrl, ap.sourceRemotes)

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
        if not self.downloadCacheFolder.is_dir():
            self.downloadCacheFolder.mkdir()
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
                self.logger.progressStart('Installation',
                                          total=len(apToInstall) * 2)

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

                self.logger.progressWorked('Installation',
                                           message="Required packages checked",
                                           worked=1,
                                           total=len(apToInstall) * 2 + 1)

                # Download ap list
                laList = []
                for ap in apToInstall:
                    la = self.downloadAvailablePackage(ap)
                    laList.append(la)
                    self.logger.progressWorked('Installation',
                                               message="Downloaded %s" % ap.getIdentifier(),
                                               worked=len(laList) + 1,
                                               total=len(apToInstall) * 2 + 1)

                # Extract la list
                for la in laList:
                    ip = self.extractLeafArtifact(la, env,
                                                  keepFolderOnError=keepFolderOnError)
                    out.append(ip)
                    self.logger.progressWorked('Installation',
                                               message="Installed %s" % la.getIdentifier(),
                                               worked=len(laList) +
                                               len(out) + 1,
                                               total=len(apToInstall) * 2 + 1)

            self.logger.progressDone('Installation')

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
            self.logger.progressStart('Uninstall package(s)',
                                      total=total)
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
                self.logger.progressWorked('Uninstall package(s)',
                                           worked=worked,
                                           total=total)
                del installedPackages[ip.getIdentifier()]
            self.logger.progressDone('Uninstall package(s)',
                                     message="%d package(s) removed" % (len(ipToRemove)))

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
