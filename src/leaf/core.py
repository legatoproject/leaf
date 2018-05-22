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
import json
from leaf import __version__
from leaf.constants import JsonConstants, LeafConstants, LeafFiles
from leaf.coreutils import StepExecutor, VariableResolver, \
    DynamicDependencyManager
from leaf.model import Manifest, InstalledPackage, AvailablePackage, LeafArtifact, \
    PackageIdentifier, RemoteRepository, Profile, \
    WorkspaceConfiguration, Environment, UserConfiguration
from leaf.utils import resolveUrl, getCachedArtifactName, isFolderIgnored, \
    markFolderAsIgnored, openOutputTarFile, computeSha1sum, downloadFile, \
    jsonLoadFile, checkSupportedLeaf, jsonWriteFile, mkTmpLeafRootDir,\
    getAltEnvPath
import os
from pathlib import Path
import platform
import shutil
from tarfile import TarFile
import urllib.request


class LeafRepository():
    '''
    Methods needed for releng, ie generate packages and maintain repository
    '''

    def __init__(self, logger):
        self.logger = logger

    def pack(self, manifestFile, outputFile):
        '''
        Create a leaf artifact from given the manifest.
        if the output file ands with .json, a *manifest only* package will be generated.
        Output file can ends with tar.[gz,xz,bz2] of json
        '''
        manifest = Manifest(jsonLoadFile(manifestFile))
        self.logger.printDefault("Found:", manifest.getIdentifier())
        self.logger.printDefault(
            "Create tar:", manifestFile, "-->", outputFile)
        with openOutputTarFile(outputFile) as tf:
            for file in manifestFile.parent.glob('*'):
                tf.add(str(file),
                       str(file.relative_to(manifestFile.parent)))

    def index(self, outputFile, artifacts, name=None, description=None, composites=[]):
        '''
        Create an index.json referencing all given artifacts
        '''
        infoNode = OrderedDict()
        if name is not None:
            infoNode[JsonConstants.REMOTE_NAME] = name
        if description is not None:
            infoNode[JsonConstants.REMOTE_DESCRIPTION] = description
        infoNode[JsonConstants.REMOTE_DATE] = str(datetime.utcnow())

        rootNode = OrderedDict()
        rootNode[JsonConstants.INFO] = infoNode
        if composites is not None and len(composites) > 0:
            rootNode[JsonConstants.REMOTE_COMPOSITE] = composites

        packagesNode = []
        rootNode[JsonConstants.REMOTE_PACKAGES] = packagesNode
        for a in artifacts:
            la = LeafArtifact(a)
            self.logger.printDefault("Found:", la.getIdentifier())
            fileNode = OrderedDict()
            fileNode[JsonConstants.REMOTE_PACKAGE_FILE] = str(
                Path(a).relative_to(outputFile.parent))
            fileNode[JsonConstants.REMOTE_PACKAGE_SHA1SUM] = str(
                computeSha1sum(a))
            fileNode[JsonConstants.REMOTE_PACKAGE_SIZE] = a.stat().st_size
            fileNode[JsonConstants.INFO] = la.getNodeInfo()
            packagesNode.append(fileNode)

        jsonWriteFile(outputFile, rootNode, pp=True)
        self.logger.printDefault("Index created:", outputFile)


class LeafApp(LeafRepository):
    '''
    Main API for using Leaf
    '''

    def __init__(self, logger,
                 nonInteractive=False):
        '''
        Constructor
        '''
        super().__init__(logger)
        self.configurationFile = getAltEnvPath(LeafConstants.ENV_CONFIG_FILE,
                                               LeafFiles.DEFAULT_CONFIG_FILE)
        cacheFolder = getAltEnvPath(LeafConstants.ENV_CACHE_FOLDER,
                                    LeafFiles.DEFAULT_CACHE_FOLDER)
        self.remoteCacheFile = cacheFolder / LeafFiles.CACHE_REMOTES_FILENAME
        self.downloadCacheFolder = cacheFolder / LeafFiles.CACHE_DOWNLOAD_FOLDERNAME
        self.nonInteractive = nonInteractive

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

    def getInstallFolder(self):
        out = self.readConfiguration().getRootFolder()
        if not out.exists():
            out.mkdir()
        return out

    def updateUserConfiguration(self,
                                rootFolder=None,
                                envSetMap=None, envUnsetList=None,
                                remoteAddList=None, remoteRmList=None):
        '''
        Update the configuration file
        '''
        usrc = self.readConfiguration()
        if rootFolder is not None:
            usrc.setRootFolder(rootFolder)

        # Update env
        usrc.updateEnv(envSetMap, envUnsetList)

        # Update remotes
        needRefresh = usrc.updateRemotes(remoteAddList, remoteRmList)

        # Save and clean cache
        self.writeConfiguration(usrc)
        if needRefresh and self.remoteCacheFile.exists():
            os.remove(str(self.remoteCacheFile))

    def getLeafEnvironment(self):
        out = Environment("Leaf variables")
        out.env.append(("LEAF_PLATFORM_SYSTEM", platform.system()))
        out.env.append(("LEAF_PLATFORM_MACHINE", platform.machine()))
        out.env.append(("LEAF_PLATFORM_RELEASE", platform.release()))
        if self.nonInteractive:
            out.env.append(("LEAF_NON_INTERACTIVE", "1"))
        out.addSubEnv(self.getUserEnvironment())
        return out

    def getUserEnvironment(self):
        return Environment("Exported by user config",
                           self.readConfiguration().getEnvMap())

    def getRemoteRepositories(self, smartRefresh=True):
        '''
        List all remotes from configuration
        '''
        if self.remoteCacheFile.exists():
            if datetime.fromtimestamp(self.remoteCacheFile.stat().st_mtime) < datetime.now() - LeafConstants.CACHE_DELTA:
                self.logger.printDefault("Cache file is outdated")
                if smartRefresh:
                    os.remove(str(self.remoteCacheFile))

        if not self.remoteCacheFile.exists():
            self.fetchRemotes()

        cache = jsonLoadFile(self.remoteCacheFile)
        out = []
        masterUrls = self.readConfiguration().getRemotes()
        for url, data in cache.items():
            out.append(RemoteRepository(url, url in masterUrls, data))
        return out

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
            out.append(pi)
        return out

    def listAvailablePackages(self, smartRefresh=True):
        '''
        List all available package
        '''
        out = OrderedDict()
        for rr in self.getRemoteRepositories(smartRefresh=smartRefresh):
            if rr.isFetched():
                for jsonPayload in rr.getPackages():
                    ap = AvailablePackage(jsonPayload, rr.url)
                    if ap.getIdentifier() not in out:
                        out[ap.getIdentifier()] = ap
        return out

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
                            self.recursiveFetchUrl(resolveUrl(remoteurl,
                                                              composite),
                                                   content)
            except Exception as e:
                self.logger.printError("Error fetching", remoteurl, ":", e)

    def fetchRemotes(self):
        '''
        Fetch remotes
        '''
        content = OrderedDict()
        urls = self.readConfiguration().getRemotes()
        self.logger.progressStart('Fetch remote(s)',
                                  message="Refreshing available packages...",
                                  total=len(urls))
        worked = 0
        for url in urls:
            self.recursiveFetchUrl(url, content)
            worked += 1
            self.logger.progressWorked('Fetch remote(s)',
                                       worked=worked,
                                       total=len(urls))
        jsonWriteFile(self.remoteCacheFile, content)
        self.logger.progressDone('Fetch remote(s)')

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

    def listDependencies(self, motifList, reverse=False, filterInstalled=False):
        '''                                                                                                                                                             
        List all dependencies for given packages                                                                                                                        
        @return: PackageIdentifier list                                                                                                                                 
        '''
        installedPackages = self.listInstalledPackages()
        availablePackages = self.listAvailablePackages()
        piList = self.resolveLatest(motifList,
                                    ipMap=installedPackages,
                                    apMap=availablePackages)

        mfMap = OrderedDict()
        mfMap.update(installedPackages)
        for pi, ap in availablePackages.items():
            if pi not in installedPackages:
                mfMap[pi] = ap

        # Build the mf list
        out = DynamicDependencyManager.computeDependencyTree(piList,
                                                             mfMap,
                                                             self.getLeafEnvironment(),
                                                             reverse)

        if filterInstalled:
            out = [mf for mf in out if mf.getIdentifier() not in installedPackages]

        # Keep only PI
        out = list(map(Manifest.getIdentifier, out))

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

        apList = DynamicDependencyManager.computePrereqList(piList,
                                                            availablePackages)

        errorCount = 0
        if len(apList) > 0:
            self.logger.printVerbose("Installing %d pre-required package(s) in %s" %
                                     (len(apList), tmpRootFolder))
            if env is None:
                env = self.getLeafEnvironment()
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
                env = self.getLeafEnvironment()

            apToInstall = DynamicDependencyManager.computeApToInstall(piList,
                                                                      availablePackages,
                                                                      installedPackages,
                                                                      env)
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
                    self.logger.printDefault("Total size:", totalSize, "bytes")
                if not self.logger.confirm():
                    raise ValueError("Installation aborted")

                # Install prereq
                prereqIpsList = []
                for ap in apToInstall:
                    prereqIpsList += ap.getLeafRequires()

                if len(prereqIpsList) > 0:
                    prereqRootFolder = mkTmpLeafRootDir()
                    self.installPrereqFromRemotes(prereqIpsList,
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

        ipToRemove = DynamicDependencyManager.computeIpToUninstall(piList,
                                                                   installedPackages)

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
            for ip in ipToRemove:
                self.logger.printDefault("Removing", ip.getIdentifier())
                vr = VariableResolver(ip,
                                      self.listInstalledPackages().values())
                stepExec = StepExecutor(self.logger,
                                        ip,
                                        vr,
                                        env=self.getLeafEnvironment())
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

    def getPackageEnv(self, motifList, env=None):
        '''
        Get the env vars declared by given packages and their dependencies
        '''
        installedPackages = self.listInstalledPackages()
        piList = self.resolveLatest(motifList,
                                    ipMap=installedPackages,
                                    apMap=None)
        if env is None:
            env = self.getLeafEnvironment()

        ipList = DynamicDependencyManager.computeDependencyTree(piList,
                                                                installedPackages,
                                                                env)

        for ip in ipList:
            ipEnv = Environment("Exported by package %s" % ip.getIdentifier())
            env.addSubEnv(ipEnv)
            vr = VariableResolver(ip, installedPackages.values())
            for key, value in ip.getEnvMap().items():
                ipEnv.env.append((key,
                                  vr.resolve(value)))
        return env


class Workspace():
    '''
    Represent a workspace, where leaf profiles apply
    '''

    def __init__(self, rootFolder, app):
        self.app = app
        self.logger = app.logger
        self.rootFolder = rootFolder
        self.configFile = rootFolder / LeafFiles.WS_CONFIG_FILENAME
        self.dataFolder = rootFolder / LeafFiles.WS_DATA_FOLDERNAME
        self.currentLink = self.dataFolder / LeafFiles.CURRENT_PROFILE_LINKNAME

    def readConfiguration(self, initIfNeeded=False):
        '''
        Return the configuration and if current leaf version is supported
        '''
        if not self.configFile.exists() and initIfNeeded:
            self.writeConfiguration(WorkspaceConfiguration(OrderedDict()))
        wsc = WorkspaceConfiguration(jsonLoadFile(self.configFile))
        checkSupportedLeaf(wsc.jsonpath(JsonConstants.INFO_LEAF_MINVER),
                           exceptionMessage="Leaf has to be updated to work with this workspace")
        # Configure app with ws configuration
        self.app.updateUserConfiguration(remoteAddList=wsc.getRemotes())
        return wsc

    def writeConfiguration(self, wsc):
        '''
        Write the configuration and set the min leaf version to current version
        '''
        if not self.dataFolder.exists():
            self.dataFolder.mkdir()
        wsc.jsoninit(key=JsonConstants.WS_LEAFMINVERSION,
                     value=__version__,
                     force=True)
        tmpFile = self.dataFolder / ("tmp-" + LeafFiles.WS_CONFIG_FILENAME)
        jsonWriteFile(tmpFile, wsc.json, pp=True)
        tmpFile.rename(self.configFile)

    def updateWorkspaceConfiguration(self,
                                     envSetMap=None, envUnsetList=None,
                                     remoteAddList=None, remoteRmList=None):
        wsc = self.readConfiguration()
        wsc.updateEnv(envSetMap, envUnsetList)
        wsc.updateRemotes(remoteAddList, remoteRmList)
        self.writeConfiguration(wsc)

    def getAllProfiles(self, wsc=None):
        if wsc is None:
            wsc = self.readConfiguration()
        out = OrderedDict()
        for name, pfJson in wsc.getProfiles().items():
            out[name] = Profile(name,
                                self.dataFolder / name,
                                pfJson)
        try:
            out[self.getCurrentProfileName()].isCurrentProfile = True
        except:
            pass
        return out

    def retrieveCurrentProfile(self, pfMap=None):
        return self.retrieveProfile(self.getCurrentProfileName())

    def retrieveProfile(self, name, pfMap=None):
        if name is None:
            raise ValueError("Cannot retrieve profile")
        if pfMap is None:
            pfMap = self.getAllProfiles()
        if name not in pfMap:
            raise ValueError("Cannot find profile %s" % name)
        return pfMap.get(name)

    def checkProfile(self, pf, silent=False, raiseIfNotSync=True):
        # Check packages are linked
        installedPackages = self.app.listInstalledPackages()
        env = self.app.getLeafEnvironment()
        env.addSubEnv(self.readConfiguration().getEnvironment())
        env.addSubEnv(pf.getEnvironment())
        out = True
        try:
            ipList = DynamicDependencyManager.computeDependencyTree(pf.getPackageIdentifiers(),
                                                                    installedPackages,
                                                                    env)
            if ipList is not None:
                for ip in ipList:
                    linkedManifest = pf.folder / ip.getIdentifier().name / LeafFiles.MANIFEST
                    if InstalledPackage(linkedManifest).getIdentifier() != ip.getIdentifier():
                        raise ValueError("Missing package %s" %
                                         ip.getIdentifier())
        except:
            out = False

        if not out:
            if not silent:
                message = "Profile %s is out of sync, please run 'leaf sync'" % (
                    pf.name)
                if raiseIfNotSync:
                    raise ValueError(message)
                self.logger.printError(message)
            return False
        return True

    def getCurrentProfileName(self):
        if self.currentLink.is_symlink():
            try:
                return self.currentLink.resolve().name
            except Exception:
                self.currentLink.unlink()
                raise ValueError(
                    "No current profile, you need to select a profile first")
        else:
            raise ValueError(
                "No current profile, you need to select to a profile first")

    def deleteProfile(self, name):
        pf = self.retrieveProfile(name)
        if self.logger.confirm(
                question="Do you want to delete profile %s?" % pf.name):
            wsc = self.readConfiguration()
            del wsc.getProfiles()[pf.name]
            if pf.folder.exists():
                shutil.rmtree(str(pf.folder))
            self.writeConfiguration(wsc)
            if pf.isCurrentProfile:
                self.updateCurrentLink(None)
            return pf

    def createProfile(self, name):
        # Read configuration
        wsc = self.readConfiguration()

        name = Profile.checkValidName(name)

        # Check profile can be created
        if name in wsc.getProfiles():
            raise ValueError("Profile %s already exists" % name)

        # Create & update profile
        self.logger.printDefault("Create profile %s" % name)
        pf = Profile.emptyProfile(name, self.dataFolder / name)

        # Update & save configuration
        wsc.getProfiles()[name] = pf.json
        self.writeConfiguration(wsc)

        # Switch to new profile
        self.switchProfile(name)

        return pf

    def updateProfile(self,
                      name,
                      newName=None,
                      mpkgAddList=None, mpkgRmList=None,
                      envSetMap=None, envUnsetList=None):
        # Retrieve profile
        wsc = self.readConfiguration()
        pf = self.retrieveProfile(name)

        # Check new name is valid in case of rename
        if newName is not None:
            newName = Profile.checkValidName(newName)
            if newName != pf.name and newName in wsc.getProfiles():
                raise ValueError("Profile %s already exists" % newName)

        # Add needed packages
        pkgMap = pf.getPackageMap()
        if mpkgAddList is not None:
            piAddList = self.app.resolveLatest(mpkgAddList,
                                               ipMap=self.app.listInstalledPackages(),
                                               apMap=self.app.listAvailablePackages())
            for pi in piAddList:
                addPi = False
                if pi.name in pkgMap:
                    oldPi = pkgMap[pi.name]
                    if oldPi != pi:
                        addPi = self.logger.confirm(question="Do you want to update package %s from %s to %s?" % (
                            pi.name,
                            oldPi.version,
                            pi.version))
                else:
                    self.logger.printDefault("Add package %s" % (pi))
                    addPi = True
                if addPi:
                    pkgMap[pi.name] = pi

        # Remove needed packages
        if mpkgRmList is not None:
            for mpkg in mpkgRmList:
                pi = None
                if PackageIdentifier.isValidIdentifier(mpkg):
                    pi = PackageIdentifier.fromString(mpkg)
                elif mpkg in pkgMap:
                    pi = pkgMap[mpkg]
                else:
                    raise ValueError("Cannot find package %s in profile %s" %
                                     (mpkg, pf.name))
                self.logger.printDefault("Remove package %s" % (pi))
                del pkgMap[pi.name]

        # replace pkg list
        pf.setPackages(pkgMap.values())

        # Update profile
        pf.updateEnv(setMap=envSetMap,
                     unsetList=envUnsetList)

        # Handle rename
        if newName is not None and newName != pf.name:
            newFolder = self.dataFolder / newName
            if pf.folder.exists():
                pf.folder.rename(newFolder)
            if pf.isCurrentProfile:
                self.updateCurrentLink(newName)
            # Delete the previous profile
            del wsc.getProfiles()[pf.name]
            # Update the name/folder
            pf.name = newName
            pf.folder = newFolder

        # Update & save configuration
        wsc.getProfiles()[pf.name] = pf.json
        self.writeConfiguration(wsc)
        self.checkProfile(pf, raiseIfNotSync=False)
        return pf

    def switchProfile(self, name):
        pf = self.retrieveProfile(name)
        # Check folder exist
        if not pf.folder.exists():
            pf.folder.mkdir(parents=True)
        # Update symlink
        self.updateCurrentLink(pf.name)
        self.logger.printDefault("Current profile is now %s" % pf.name)
        return pf

    def updateCurrentLink(self, name):
        '''
        Update the current link without any check
        '''
        if self.currentLink.is_symlink():
            self.currentLink.unlink()
        if name is not None:
            self.currentLink.symlink_to(name)

    def provisionProfile(self, name):
        pf = self.retrieveProfile(name)
        # Ensure FS clean
        if not self.dataFolder.is_dir():
            self.dataFolder.mkdir()
        elif pf.folder.is_dir():
            shutil.rmtree(str(pf.folder))
        pf.folder.mkdir()

        # Do nothing for empty profiles
        if len(pf.getPackages()) > 0:
            env = self.getSkelEnvironement(pf)
            self.app.installFromRemotes(pf.getPackages(), env=env)
            installedPackages = self.app.listInstalledPackages()
            deps = DynamicDependencyManager.computeDependencyTree(pf.getPackageIdentifiers(),
                                                                  installedPackages,
                                                                  env)
            for ip in deps:
                piFolder = pf.folder / ip.getIdentifier().name
                if piFolder.exists():
                    piFolder = pf.folder / str(ip.getIdentifier())
                piFolder.symlink_to(ip.folder)

    def getProfileEnv(self, name):
        pf = self.retrieveProfile(name)
        self.checkProfile(pf, raiseIfNotSync=True)
        return self.app.getPackageEnv(pf.getPackages(),
                                      env=self.getSkelEnvironement(pf))

    def getSkelEnvironement(self, pf=None):
        out = self.app.getLeafEnvironment()
        out.env.append(("LEAF_WORKSPACE", self.rootFolder))
        out.addSubEnv(self.readConfiguration().getEnvironment())
        if pf is not None:
            out.env.append(("LEAF_PROFILE", pf.name))
            out.addSubEnv(pf.getEnvironment())
        return out
