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
from leaf.coreutils import StepExecutor, VariableResolver,\
    DynamicDependencyManager
from leaf.model import Manifest, InstalledPackage, AvailablePackage, LeafArtifact,\
    PackageIdentifier, RemoteRepository, Profile,\
    WorkspaceConfiguration, JsonObject, Environment
from leaf.utils import resolveUrl, getCachedArtifactName, isFolderIgnored,\
    markFolderAsIgnored, openOutputTarFile, computeSha1sum, downloadFile,\
    AptHelper, jsonLoadFile, checkSupportedLeaf, jsonWriteFile
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

    def __init__(self, logger, configurationFile, remoteCacheFile=LeafFiles.REMOTES_CACHE_FILE):
        '''
        Constructor
        '''
        super().__init__(logger)
        self.configurationFile = configurationFile
        self.cacheFile = remoteCacheFile
        # Create folders if needed
        os.makedirs(str(LeafFiles.FILES_CACHE_FOLDER), exist_ok=True)

    def readConfiguration(self):
        '''
        Read the configuration if it exists, else return the the default configuration
        '''
        if self.configurationFile.exists():
            return JsonObject(jsonLoadFile(self.configurationFile))
        # Default configuration here
        out = JsonObject(OrderedDict())
        out.jsoninit(key=JsonConstants.CONFIG_ROOT,
                     value=str(LeafFiles.DEFAULT_LEAF_ROOT))
        self.writeConfiguration(out)
        return out

    def writeConfiguration(self, config):
        '''
        Write the given configuration
        '''
        jsonWriteFile(self.configurationFile, config.json, pp=True)

    def getInstallFolder(self):
        out = LeafFiles.DEFAULT_LEAF_ROOT
        config = self.readConfiguration()
        root = config.jsonpath(JsonConstants.CONFIG_ROOT)
        if root is not None:
            out = Path(root)
        os.makedirs(str(out), exist_ok=True)
        return out

    def updateConfiguration(self, rootFolder=None, envMap=None):
        '''
        Update the configuration file
        '''
        config = self.readConfiguration()
        if rootFolder is not None:
            config.jsoninit(key=JsonConstants.CONFIG_ROOT,
                            value=str(rootFolder),
                            force=True)
        if envMap is not None:
            configEnv = config.jsoninit(key=JsonConstants.CONFIG_ENV,
                                        value=OrderedDict())
            configEnv.update(envMap)
        self.writeConfiguration(config)

    def getUserEnv(self):
        '''
        Returns the user custom env variables
        '''
        return self.readConfiguration().jsonpath(JsonConstants.CONFIG_ENV, default={})

    def getLeafEnvironment(self):
        out = Environment("Leaf variables")
        out.env.append(("LEAF_PLATFORM_SYSTEM", platform.system()))
        out.env.append(("LEAF_PLATFORM_MACHINE", platform.machine()))
        out.env.append(("LEAF_PLATFORM_RELEASE", platform.release()))
        out.addSubEnv(Environment("Exported by user config",
                                  self.getUserEnv()))
        return out

    def remoteAdd(self, url):
        '''
        Add url to configuration file
        '''
        config = self.readConfiguration()
        remoteList = config.jsoninit(key=JsonConstants.CONFIG_REMOTES,
                                     value=[])
        if url not in remoteList:
            remoteList.append(url)
            self.writeConfiguration(config)
            if self.cacheFile.exists():
                os.remove(str(self.cacheFile))

    def remoteRemove(self, url):
        '''
        Remote given url from configuration
        '''
        config = self.readConfiguration()
        remoteList = config.jsoninit(key=JsonConstants.CONFIG_REMOTES,
                                     value=[])
        if url in remoteList:
            remoteList.remove(url)
            self.writeConfiguration(config)
            if self.cacheFile.exists():
                os.remove(str(self.cacheFile))

    def getRemoteUrls(self):
        '''
        List all remotes from configuration
        '''
        return self.readConfiguration().jsonpath(JsonConstants.CONFIG_REMOTES,
                                                 default=[])

    def getRemoteRepositories(self, smartRefresh=True, onlyMaster=False):
        '''
        List all remotes from configuration
        '''
        if self.cacheFile.exists():
            if datetime.fromtimestamp(self.cacheFile.stat().st_mtime) < datetime.now() - LeafConstants.CACHE_DELTA:
                self.logger.printDefault("Cache file is outdated")
                if smartRefresh:
                    os.remove(str(self.cacheFile))

        if not self.cacheFile.exists():
            self.fetchRemotes()

        cache = jsonLoadFile(self.cacheFile)
        out = []
        masterUrls = self.getRemoteUrls()
        for url in masterUrls:
            rr = RemoteRepository(url, True, cache.get(url))
            out.append(rr)
        if not onlyMaster:
            for url, data in cache.items():
                if url not in masterUrls:
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
                for jsonPayload in rr.jsonpath(JsonConstants.REMOTE_PACKAGES, default=[]):
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
        urls = self.getRemoteUrls()
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
        jsonWriteFile(self.cacheFile, content)
        self.logger.progressDone('Fetch remote(s)')

    def listInstalledPackages(self):
        '''
        Return all installed packages
        @return: PackageIdentifier/InstalledPackage dict
        '''
        out = OrderedDict()
        for folder in self.getInstallFolder().iterdir():
            if folder.is_dir() and not isFolderIgnored(folder):
                manifest = folder / LeafConstants.MANIFEST
                if manifest.is_file():
                    ip = InstalledPackage(manifest)
                    out[ip.getIdentifier()] = ip
        return out

    def listDependencies(self, motifList, reverse=False, filterInstalled=False, aptDepends=False):
        '''                                                                                                                                                             
        List all dependencies for given packages                                                                                                                        
        @return: PackageIdentifier list                                                                                                                                 
                    or String list in case of apt dependencies                                                                                                          
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

        if aptDepends:
            debList = []
            for mf in out:
                for deb in mf.getAptDepends():
                    if deb not in debList:
                        debList.append(deb)
            if filterInstalled:
                ah = AptHelper()
                debList = [p for p in debList if not ah.isInstalled(p)]
            out = debList
        else:
            # Keep only PI
            out = list(map(Manifest.getIdentifier, out))

        return out

    def checkPackagesForInstall(self, mfList,
                                bypassLeafMinVersion=False,
                                bypassAptDepends=False):

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

        # Check dependencies
        if not bypassAptDepends:
            ah = AptHelper()
            missingAptDepends = []
            for mf in mfList:
                for deb in mf.getAptDepends():
                    if deb not in missingAptDepends and not ah.isInstalled(deb):
                        missingAptDepends.append(deb)
            if len(missingAptDepends) > 0:
                self.logger.printError(
                    "You may have to install missing dependencies by running:")
                self.logger.printError(
                    "  $ sudo apt-get update && sudo apt-get install %s" % ' '.join(missingAptDepends))
                raise ValueError("Missing apt dependencies")

    def downloadAvailablePackage(self, ap):
        '''
        Download given available package and returns the files in cache folder
        @return LeafArtifact 
        '''
        filename = getCachedArtifactName(ap.getFilename(),
                                         ap.getSha1sum())
        cachedFile = downloadFile(ap.getUrl(),
                                  LeafFiles.FILES_CACHE_FOLDER,
                                  self.logger,
                                  filename=filename,
                                  sha1sum=ap.getSha1sum())
        return LeafArtifact(cachedFile)

    def extractLeafArtifact(self, la, keepFolderOnError=False):
        '''
        Install a leaf artifact
        @return InstalledPackage
        '''
        targetFolder = self.getInstallFolder() / str(la.getIdentifier())
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
            out = InstalledPackage(targetFolder / LeafConstants.MANIFEST)
            vr = VariableResolver(out,
                                  self.listInstalledPackages().values())
            se = StepExecutor(self.logger,
                              out,
                              vr,
                              extraEnv=self.getUserEnv())
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

    def installFromRemotes(self, motifList,
                           extraEnv=None,
                           bypassAptDepends=False,
                           keepFolderOnError=False):
        '''
        Compute dependency tree, check compatibility, download from remotes and extract needed packages 
        @return: InstalledPackage list
        '''
        installedPackages = self.listInstalledPackages()
        availablePackages = self.listAvailablePackages()
        piList = self.resolveLatest(motifList,
                                    ipMap=installedPackages,
                                    apMap=availablePackages)

        # Build env to resolve dynamic dependencies
        env = Environment()
        env.addSubEnv(self.getLeafEnvironment())
        env.addSubEnv(extraEnv)

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
            self.checkPackagesForInstall(apToInstall,
                                         bypassAptDepends=bypassAptDepends)

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

            # Download ap list
            laList = []
            for ap in apToInstall:
                la = self.downloadAvailablePackage(ap)
                laList.append(la)
                self.logger.progressWorked('Installation',
                                           message="Downloaded %s" % ap.getIdentifier(),
                                           worked=len(laList),
                                           total=len(apToInstall) * 2)

            # Extract la list
            for la in laList:
                ip = self.extractLeafArtifact(la,
                                              keepFolderOnError=keepFolderOnError)
                out.append(ip)
                self.logger.progressWorked('Installation',
                                           message="Installed %s" % la.getIdentifier(),
                                           worked=len(laList) + len(out),
                                           total=len(apToInstall) * 2)

        self.logger.progressDone('Installation')
        return out

    def installFromFiles(self, files,
                         bypassLeafDepends=False,
                         bypassAptDepends=False,
                         keepFolderOnError=False):
        '''
        Install packages from leaf artifacts
        @return: InstalledPackage list
        '''
        out = []
        installedPackages = self.listInstalledPackages()

        # Build the list of artifact to install
        laList = []
        for f in files:
            la = f if isinstance(f, LeafArtifact) else LeafArtifact(f)
            if la.getIdentifier() in installedPackages:
                self.logger.printVerbose(la.getIdentifier(),
                                         "is already installed")
            elif la not in laList:
                laList.append(la)

        # Check nothing to do
        if len(laList) == 0:
            self.logger.printDefault("All packages are installed")
        else:
            # Check ap list can be installed
            self.checkPackagesForInstall(laList,
                                         bypassLeafDepends=bypassLeafDepends,
                                         bypassAptDepends=bypassAptDepends)

            # Extract la list
            for la in laList:
                ip = self.extractLeafArtifact(la,
                                              keepFolderOnError=keepFolderOnError)
                out.append(ip)
                self.logger.progressWorked('Installation',
                                           message="Installed %s" % la.getIdentifier(),
                                           worked=len(out),
                                           total=len(laList) * 2)

        self.logger.progressDone('Installation')
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
                                        extraEnv=self.getUserEnv())
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
            for key, value in ip.getMfEnv().items():
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
        self.currentLink = self.dataFolder / LeafFiles.CURRENT_PROFILE

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
        for url in wsc.getWsRemotes():
            self.app.remoteAdd(url)
        return wsc

    def writeConfiguration(self, wsc):
        '''
        Write the configuration and set the min leaf version to current version
        '''
        self.dataFolder.mkdir(exist_ok=True)
        wsc.jsoninit(key=JsonConstants.WS_LEAFMINVERSION,
                     value=__version__,
                     force=True)
        tmpFile = self.dataFolder / ("tmp-" + LeafFiles.WS_CONFIG_FILENAME)
        jsonWriteFile(tmpFile, wsc.json, pp=True)
        tmpFile.rename(self.configFile)

    def updateWorkspace(self, remotes=None, envMap=None, modules=None):
        wsc = self.readConfiguration()
        if remotes is not None:
            for remote in remotes:
                if remote not in wsc.getWsRemotes():
                    wsc.getWsRemotes().append(remote)
        if envMap is not None:
            wsc.getWsEnv().update(envMap)
        if modules is not None:
            wsc.getWsSupportedModules().extend(modules)
        self.writeConfiguration(wsc)

    def getAllProfiles(self, wsc=None):
        if wsc is None:
            wsc = self.readConfiguration()
        out = OrderedDict()
        for name, pfJson in wsc.getWsProfiles().items():
            out[name] = Profile(name,
                                self.dataFolder / name,
                                pfJson)
        try:
            out[self.getCurrentProfileName()].isCurrentProfile = True
        except:
            pass
        return out

    def retrieveProfile(self, name=None, pfMap=None):
        if name is None:
            name = self.getCurrentProfileName()
        if pfMap is None:
            pfMap = self.getAllProfiles()
        if name not in pfMap:
            raise ValueError("Cannot find profile %s" % name)
        return pfMap.get(name)

    def checkProfile(self, pf):
        # Check packages are linked
        installedPackages = self.app.listInstalledPackages()
        env = self.app.getLeafEnvironment()
        env.addSubEnv(self.readConfiguration().getWsEnvironment())
        env.addSubEnv(pf.getPfEnvironment())
        for ip in DynamicDependencyManager.computeDependencyTree(pf.getPfPackageIdentifiers(),
                                                                 installedPackages,
                                                                 env):
            piLink = pf.folder / ip.getIdentifier().name
            if not piLink.is_symlink():
                raise ValueError("Some packages are not linked, please run 'leaf sync %s'" %
                                 (pf.name))

    def getCurrentProfileName(self):
        if self.currentLink.is_symlink():
            try:
                return self.currentLink.resolve().name
            except Exception:
                self.currentLink.unlink()
                raise ValueError(
                    "No current profile, you need to switch to a profile first")
        else:
            raise ValueError(
                "No current profile, you need to switch to a profile first")

    def deleteProfile(self, name):
        pf = self.retrieveProfile(name)
        if self.logger.confirm(
                question="Do you want to delete profile %s?" % pf.name):
            wsc = self.readConfiguration()
            del wsc.getWsProfiles()[pf.name]
            if pf.folder.exists():
                shutil.rmtree(str(pf.folder))
            self.writeConfiguration(wsc)
            if pf.isCurrentProfile:
                self.updateCurrentLink(None)
            return pf

    def createProfile(self, name=None, motifList=None, envMap=None):
        # Read configuration
        wsc = self.readConfiguration()

        # Resolves package list
        piList = []
        if motifList is not None:
            piList = self.app.resolveLatest(motifList, ipMap=True, apMap=True)

        # compute if needed and check name
        if name is None:
            name = Profile.genDefaultName(piList)
        else:
            name = Profile.checkValidName(name)

        # Check profile can be created
        if name in wsc.getWsProfiles():
            raise ValueError("Profile %s already exists" % name)

        # Create & update profile
        self.logger.printDefault("Create profile %s" % name)
        pf = Profile.emptyProfile(name, self.dataFolder / name)
        self.internalUpdateProfile(pf, motifList, envMap)

        # Update & save configuration
        wsc.getWsProfiles()[name] = pf.json
        self.writeConfiguration(wsc)
        return pf

    def updateProfile(self, name=None, motifList=None, envMap=None, newName=None):
        # Retrieve profile
        wsc = self.readConfiguration()
        pf = self.retrieveProfile(name)

        # Check new name is valid in case of rename
        if newName is not None:
            newName = Profile.checkValidName(newName)
            if newName != pf.name and newName in wsc.getWsProfiles():
                raise ValueError("Profile %s already exists" % newName)

        # Update profile content
        self.internalUpdateProfile(pf, motifList, envMap)

        # Update & save configuration
        if newName is not None and newName != pf.name:
            newFolder = self.dataFolder / newName
            if pf.folder.exists():
                pf.folder.rename(newFolder)
            if pf.isCurrentProfile:
                self.updateCurrentLink(newName)
            # Delete the previous profile
            del wsc.getWsProfiles()[pf.name]
            # Update the name/folder
            pf.name = newName
            pf.folder = newFolder
            # Save the new profile
            wsc.getWsProfiles()[pf.name] = pf.json
        else:
            # Update the profile
            wsc.getWsProfiles()[pf.name] = pf.json

        self.writeConfiguration(wsc)
        return pf

    def internalUpdateProfile(self, pf, motifList=None, envMap=None):
        # Update profile
        if motifList is not None:
            piList = self.app.resolveLatest(motifList,
                                            ipMap=self.app.listInstalledPackages(),
                                            apMap=self.app.listAvailablePackages())
            profilePiMap = pf.getPfPackageIdentifierMap()
            for pi in piList:
                if pi.name in profilePiMap:
                    self.logger.printDefault("Update %s, version %s -> %s" % (
                        pi.name,
                        profilePiMap[pi.name].version,
                        pi.version))
                else:
                    self.logger.printDefault("Add %s, version %s" % (
                        pi.name,
                        pi.version))
                profilePiMap[pi.name] = pi
            pf.setPiList(profilePiMap.values())

        if envMap is not None and len(envMap) > 0:
            self.logger.printDefault("Update environment")
            pf.getPfEnv().update(envMap)

    def switchProfile(self, name):
        # if no name and no current, use 1st profile
        if name is None:
            try:
                self.getCurrentProfileName()
            except:
                pfMap = self.getAllProfiles()
                if len(pfMap) == 0:
                    raise ValueError("There is no profile defined")
                name = next(iter(pfMap))
        # Retrieve profile
        pf = self.retrieveProfile(name)
        # Provision profile
        self.provisionProfile(pf)
        # Update symlink
        self.updateCurrentLink(pf.name)
        return pf

    def updateCurrentLink(self, name):
        '''
        Update the current link without any check
        '''
        if self.currentLink.is_symlink():
            self.currentLink.unlink()
        if name is not None:
            self.currentLink.symlink_to(name)

    def provisionProfile(self, pf):
        # Ensure FS clean
        if not self.dataFolder.is_dir():
            self.dataFolder.mkdir()
        elif pf.folder.is_dir():
            shutil.rmtree(str(pf.folder))
        pf.folder.mkdir()

        # Do nothing for empty profiles
        if len(pf.getPfPackages()) > 0:
            env = self.app.getLeafEnvironment()
            env.addSubEnv(self.readConfiguration().getWsEnvironment())
            env.addSubEnv(pf.getPfEnvironment())
            self.app.installFromRemotes(pf.getPfPackages(), env)
            installedPackages = self.app.listInstalledPackages()
            deps = DynamicDependencyManager.computeDependencyTree(pf.getPfPackageIdentifiers(),
                                                                  installedPackages,
                                                                  env)
            for ip in deps:
                piFolder = pf.folder / ip.getIdentifier().name
                if piFolder.exists():
                    piFolder = pf.folder / str(ip.getIdentifier())
                piFolder.symlink_to(ip.folder)

    def getProfileEnv(self, name=None):
        wsc = self.readConfiguration()
        pf = self.retrieveProfile(name)
        self.checkProfile(pf)
        env = self.app.getLeafEnvironment()
        env.env.append(("LEAF_WORKSPACE", self.rootFolder))
        env.env.append(("LEAF_PROFILE", pf.name))
        env.addSubEnv(wsc.getWsEnvironment())
        env.addSubEnv(pf.getPfEnvironment())
        return self.app.getPackageEnv(pf.getPfPackages(), env)
