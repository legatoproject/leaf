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
from leaf.model import Manifest, InstalledPackage, AvailablePackage, LeafArtifact,\
    PackageIdentifier, RemoteRepository, Profile
from leaf.utils import resolveUrl, getCachedArtifactName, isFolderIgnored,\
    markFolderAsIgnored, openOutputTarFile, computeSha1sum, downloadFile,\
    AptHelper, jsonLoadFile
import os
from pathlib import Path
import shutil
import subprocess
from tarfile import TarFile
import urllib.request


class DependencyManager():

    def __init__(self):
        self.content = OrderedDict()

    def addContent(self, mfMap, clear=False):
        if clear:
            self.content.clear()
        for pi, mf in mfMap.items():
            if pi not in self.content:
                self.content[pi] = mf

    def resolve(self, pi):
        out = self.content.get(pi)
        if out is None:
            raise ValueError("Cannot find package: " + str(pi))
        return out

    def getDependencyTree(self, piList, acc=None):
        '''
        Return the list of PackageIdentifiers of the given list plus all needed dependencies
        @return: PackageIdentifiers list
        '''
        out = [] if acc is None else acc
        for pi in piList:
            if pi not in out:
                mf = self.resolve(pi)
                out.append(pi)
                self.getDependencyTree(
                    PackageIdentifier.fromStringList(mf.getLeafDepends()),
                    acc=out)
        return out

    def filterAndSort(self, piList, reverse=False, ignoredPiList=None):
        '''
        Sort and filter the given PackageIdentifiers
        @return: PackageIdentifiers list
        '''
        out = []

        def checker(mf):
            for pi in PackageIdentifier.fromStringList(mf.getLeafDepends()):
                if pi in out:
                    continue
                if ignoredPiList is not None and pi in ignoredPiList:
                    continue
                return False
            return True

        piList = list(piList)
        # Ordering
        while len(piList) > 0:
            for pi in piList:
                mf = self.content[pi]
                if mf is None:
                    raise ValueError('Cannot sort dependency list')
                if checker(mf):
                    out.append(pi)
            piList = [pi for pi in piList if pi not in out]
        # filter
        if ignoredPiList is not None:
            out = [pi for pi in out if pi not in ignoredPiList]
        # reverse
        if reverse:
            out.reverse()
        return out

    def filterMissingDependencies(self, piList):
        '''
        Returns the list of PackageIdentifiers not in internal content
        @return: PackageIdentifier list
        '''
        return [pi for pi in piList if pi not in self.content]

    def maintainDependencies(self, piList):
        '''
        @return: PackageIdentifiers list
        '''
        otherPiList = [pi for pi in self.content.keys() if pi not in piList]
        keepList = self.getDependencyTree(otherPiList)
        return [pi for pi in piList if pi not in keepList]


class StepExecutor():
    '''
    Used to execute post install & pre uninstall steps
    '''

    def __init__(self, logger, package, otherPackages, extraEnv=None):
        self.logger = logger
        self.package = package
        self.extraEnv = extraEnv
        self.targetFolder = package.folder
        self.variables = dict()
        self.variables[LeafConstants.VAR_PREFIX +
                       "{DIR}"] = str(package.folder)
        self.variables[LeafConstants.VAR_PREFIX +
                       "{NAME}"] = package.getName()
        self.variables[LeafConstants.VAR_PREFIX +
                       "{VERSION}"] = package.getVersion()
        for pi, pack in otherPackages.items():
            key = "%s{DIR:%s}" % (LeafConstants.VAR_PREFIX, str(pi))
            self.variables[key] = str(pack.folder)

    def postInstall(self, ):
        steps = self.package.jsonpath(JsonConstants.INSTALL, default=[])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Post-install")

    def preUninstall(self):
        steps = self.package.jsonpath(JsonConstants.UNINSTALL, default=[])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Pre-uninstall")

    def runSteps(self, steps, ip, label=""):
        self.logger.progressStart('Execute steps', total=len(steps))
        worked = 0
        for step in steps:
            if JsonConstants.STEP_LABEL in step:
                self.logger.printDefault(step[JsonConstants.STEP_LABEL])
            stepType = step[JsonConstants.STEP_TYPE]
            if stepType == JsonConstants.STEP_EXEC:
                self.doExec(step)
            elif stepType == JsonConstants.STEP_COPY:
                self.doCopy(step)
            elif stepType == JsonConstants.STEP_LINK:
                self.doLink(step)
            elif stepType == JsonConstants.STEP_DELETE:
                self.doDelete(step)
            elif stepType == JsonConstants.STEP_DOWNLOAD:
                self.doDownload(step, ip)
            worked += 1
            self.logger.progressWorked('Execute steps',
                                       worked=worked,
                                       total=len(steps))
        self.logger.progressDone('Execute steps')

    def doExec(self, step):
        command = [self.resolve(arg)
                   for arg in step[JsonConstants.STEP_EXEC_COMMAND]]
        self.logger.printVerbose("Exec:", ' '.join(command))
        env = dict(os.environ)
        for k, v in step.get(JsonConstants.STEP_EXEC_ENV, {}).items():
            v = self.resolve(v)
            env[k] = v
        if self.extraEnv is not None:
            for k, v in self.extraEnv.items():
                v = self.resolve(v)
                env[k] = v
        env["LEAF_VERSION"] = str(__version__)
        stdout = subprocess.DEVNULL
        if self.logger.isVerbose() or step.get(JsonConstants.STEP_EXEC_VERBOSE,
                                               False):
            stdout = None
        rc = subprocess.call(command,
                             cwd=str(self.targetFolder),
                             env=env,
                             stdout=stdout,
                             stderr=subprocess.STDOUT)
        if rc != 0:
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose("Return code is",
                                         rc,
                                         "but step ignores failure")
            else:
                raise ValueError("Step exited with return code " + str(rc))

    def doCopy(self, step):
        src = self.resolve(
            step[JsonConstants.STEP_COPY_SOURCE], prefixWithFolder=True)
        dst = self.resolve(
            step[JsonConstants.STEP_COPY_DESTINATION], prefixWithFolder=True)
        self.logger.printVerbose("Copy:", src, "->", dst)
        shutil.copy2(src, dst)

    def doLink(self, step):
        target = self.resolve(
            step[JsonConstants.STEP_LINK_NAME], prefixWithFolder=True)
        source = self.resolve(
            step[JsonConstants.STEP_LINK_TARGET], prefixWithFolder=True)
        self.logger.printVerbose("Link:", source, " -> ", target)
        os.symlink(source, target)

    def doDelete(self, step):
        for file in step[JsonConstants.STEP_DELETE_FILES]:
            resolvedFile = self.resolve(file, prefixWithFolder=True)
            self.logger.printVerbose("Delete:", resolvedFile)
            os.remove(resolvedFile)

    def doDownload(self, step, ip):
        try:
            downloadFile(step[JsonConstants.STEP_DOWNLOAD_URL],
                         self.targetFolder,
                         self.logger,
                         step.get(JsonConstants.STEP_DOWNLOAD_FILENAME),
                         step.get(JsonConstants.STEP_DOWNLOAD_SHA1SUM))
        except Exception as e:
            if step.get(JsonConstants.STEP_IGNORE_FAIL, False):
                self.logger.printVerbose(
                    "Download failed, but step ignores failure")
            else:
                raise e

    def resolve(self, value, failOnUnknownVariable=True, prefixWithFolder=False):
        out = str(value)
        for key, value in self.variables.items():
            out = out.replace(key, value)
        if failOnUnknownVariable and (LeafConstants.VAR_PREFIX + '{') in out:
            raise ValueError("Cannot resolve all variables for: " + out)
        if prefixWithFolder:
            return str(self.targetFolder / out)
        return out


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

        with open(str(outputFile), 'w') as out:
            json.dump(rootNode, out, indent=2)
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
            return jsonLoadFile(self.configurationFile)
        # Default configuration here
        out = dict()
        out[JsonConstants.CONFIG_ROOT] = str(LeafFiles.DEFAULT_LEAF_ROOT)
        self.writeConfiguration(out)
        return out

    def writeConfiguration(self, config):
        '''
        Write the given configuration
        '''
        with open(str(self.configurationFile), 'w') as fp:
            json.dump(config, fp, indent=2, separators=(',', ': '))

    def getInstallFolder(self):
        out = LeafFiles.DEFAULT_LEAF_ROOT
        config = self.readConfiguration()
        if config is not None:
            root = config.get(JsonConstants.CONFIG_ROOT)
            if root is not None:
                out = Path(root)
        os.makedirs(str(out), exist_ok=True)
        return out

    def updateConfiguration(self, rootFolder=None, env=None):
        '''
        Update the configuration file
        '''
        config = self.readConfiguration()
        if rootFolder is not None:
            config[JsonConstants.CONFIG_ROOT] = str(rootFolder)
        if env is not None:
            for line in env:
                k, v = line.split('=', 1)
                if JsonConstants.CONFIG_ENV not in config:
                    config[JsonConstants.CONFIG_ENV] = OrderedDict()
                config[JsonConstants.CONFIG_ENV][k.strip()] = v.strip()
        self.writeConfiguration(config)

    def getUserEnvVariables(self):
        '''
        Returns the user custom env variables
        '''
        config = self.readConfiguration()
        return config.get(JsonConstants.CONFIG_ENV, {})

    def remoteAdd(self, url):
        '''
        Add url to configuration file
        '''
        config = self.readConfiguration()
        remotes = config.get(JsonConstants.CONFIG_REMOTES)
        if remotes is None:
            remotes = []
            config[JsonConstants.CONFIG_REMOTES] = remotes
        if url not in remotes:
            remotes.append(url)
            self.writeConfiguration(config)
            if self.cacheFile.exists():
                os.remove(str(self.cacheFile))

    def remoteRemove(self, url):
        '''
        Remote given url from configuration
        '''
        config = self.readConfiguration()
        remotes = config.get(JsonConstants.CONFIG_REMOTES)
        if remotes is not None:
            if url in remotes:
                remotes.remove(url)
                self.writeConfiguration(config)
                if self.cacheFile.exists():
                    os.remove(str(self.cacheFile))

    def getRemoteUrls(self):
        '''
        List all remotes from configuration
        '''
        return self.readConfiguration().get(JsonConstants.CONFIG_REMOTES, [])

    def getRemoteRepositories(self, smartRefresh=True):
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
                    self.logger.printDefault("Fetched", remoteurl)
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
        self.logger.progressStart('Fetch remote(s)', total=len(urls))
        worked = 0
        for url in urls:
            self.recursiveFetchUrl(url, content)
            worked += 1
            self.logger.progressWorked('Fetch remote(s)',
                                       worked=worked,
                                       total=len(urls))
        with open(str(self.cacheFile), 'w') as output:
            json.dump(content, output)
        self.logger.progressDone('Fetch remote(s)')

    def listInstalledPackages(self):
        '''
        Return all installed packages
        @return: PackageIdentifier/InstalledPackage dict
        '''
        out = {}
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

        dm = DependencyManager()
        dm.addContent(installedPackages)
        dm.addContent(availablePackages)

        out = dm.getDependencyTree(piList)
        out = dm.filterAndSort(out,
                               reverse,
                               installedPackages.keys() if filterInstalled else None)

        if aptDepends:
            debList = []
            for pi in out:
                for deb in dm.resolve(pi).getAptDepends():
                    if deb not in debList:
                        debList.append(deb)
            if filterInstalled:
                ah = AptHelper()
                debList = [p for p in debList if not ah.isInstalled(p)]
            out = debList

        return out

    def downloadPackages(self, motifList):
        '''
        Download given available package and returns the files in cache folder
        @return AvailablePackage/LeafArtifact dict
        '''
        availablePackages = self.listAvailablePackages()
        piList = self.resolveLatest(motifList, apMap=availablePackages)
        apList = []
        for pi in piList:
            ap = availablePackages.get(pi)
            if ap is None:
                raise ValueError("Cannot find available package: " + str(pi))
            if ap not in apList:
                apList.append(ap)

        out = OrderedDict()
        if len(apList) == 0:
            self.logger.printDefault("Nothing to do")
        else:
            self.logger.progressStart('Download package(s)',
                                      message="Downloading %d package(s)" % (
                                          len(apList)),
                                      total=len(apList))
            # Download package if needed
            for ap in apList:
                filename = getCachedArtifactName(
                    ap.getFilename(), ap.getSha1sum())
                cachedFile = downloadFile(ap.getUrl(),
                                          LeafFiles.FILES_CACHE_FOLDER,
                                          self.logger,
                                          filename=filename,
                                          sha1sum=ap.getSha1sum())
                la = LeafArtifact(cachedFile)
                out[ap] = la
                self.logger.progressWorked('Download package(s)',
                                           worked=len(out),
                                           total=len(apList))
            self.logger.progressDone('Download package(s)')
        return out

    def extractPackages(self, files,
                        bypassSupportedOsCheck=False,
                        bypassLeafDependsCheck=False,
                        bypassAptDependsCheck=False,
                        keepFolderOnError=False):
        '''
        Extract & post install given packages
        @return: InstalledPackage list
        '''
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

        # Check dependencies
        if not bypassLeafDependsCheck:
            dm = DependencyManager()
            dm.addContent(installedPackages)
            for la in laList:
                missingDeps = dm.filterMissingDependencies(
                    PackageIdentifier.fromStringList(la.getLeafDepends()))
                if len(missingDeps) > 0:
                    raise ValueError("Missing dependencies for " +
                                     str(la.getIdentifier()))
                dm.addContent({la.getIdentifier(): la})

        # Check supported Os
        if not bypassSupportedOsCheck:
            incompatibleLaList = [la for la in laList if not la.isSupported()]
            if len(incompatibleLaList) > 0:
                self.logger.printError("Some packages are not compatible with your system: ",
                                       ", ".join([str(ap.getIdentifier()) for ap in incompatibleLaList]))
                raise ValueError("Unsupported system")

        # Check dependencies
        if not bypassAptDependsCheck:
            ah = AptHelper()
            missingAptDepends = []
            for la in laList:
                for deb in la.getAptDepends():
                    if deb not in missingAptDepends and not ah.isInstalled(deb):
                        missingAptDepends.append(deb)
            if len(missingAptDepends) > 0:
                self.logger.printError(
                    "You may have to install missing dependencies by running:")
                self.logger.printError("  $",
                                       "sudo apt-get update",
                                       "&&",
                                       "sudo apt-get install",
                                       ' '.join(missingAptDepends))
                raise ValueError("Missing dependencies")

        # Extract packages
        outIpList = []
        self.logger.progressStart('Extract package(s)', total=len(laList))
        for la in laList:
            targetFolder = self.getInstallFolder() / str(la.getIdentifier())
            if targetFolder.is_dir():
                raise ValueError("Folder already exists: " + str(targetFolder))

            # Create folder
            os.makedirs(str(targetFolder))
            try:
                self.logger.printVerbose("Extract",
                                         la.path,
                                         "in",
                                         targetFolder)
                with TarFile.open(str(la.path)) as tf:
                    tf.extractall(str(targetFolder))

                # Execute post install steps
                newPackage = InstalledPackage(
                    targetFolder / LeafConstants.MANIFEST)
                StepExecutor(self.logger,
                             newPackage,
                             installedPackages,
                             extraEnv=self.getUserEnvVariables()).postInstall()
                installedPackages[newPackage.getIdentifier()] = newPackage
                outIpList.append(newPackage)
                self.logger.progressWorked('Extract package(s)',
                                           message="Package %s extracted" % (
                                               la.getIdentifier()),
                                           worked=len(outIpList),
                                           total=len(laList))
            except Exception as e:
                self.logger.printError("Error during installation:", e)
                if keepFolderOnError:
                    targetFolderIgnored = markFolderAsIgnored(targetFolder)
                    self.logger.printVerbose("Mark folder as ignored:",
                                             targetFolderIgnored)
                else:
                    self.logger.printVerbose("Remove folder:", targetFolder)
                    shutil.rmtree(str(targetFolder), True)
                raise e
        self.logger.progressDone('Extract package(s)')
        return outIpList

    def installPackages(self, motifList, **kwargs):
        '''
        Compute dependency tree, download and extract needed packages
        @return: InstalledPackage list
        '''
        out = []
        piList = self.listDependencies(motifList, filterInstalled=True)
        if len(piList) == 0:
            self.logger.printDefault("Nothing to do")
        else:
            self.logger.progressStart('Install package(s)', total=2)
            packageMap = self.downloadPackages(piList)
            self.logger.progressWorked('Install package(s)', worked=1, total=2)
            out = self.extractPackages(packageMap.values(), **kwargs)
            self.logger.progressWorked('Install package(s)', worked=2, total=2)
            self.logger.progressDone('Install package(s)')
        return out

    def uninstallPackages(self, motifList,
                          keepUnusedDepends=False):
        '''
        Remove given package
        '''
        installedPackages = self.listInstalledPackages()
        piList = self.resolveLatest(motifList, ipMap=installedPackages)

        if not keepUnusedDepends:
            dm = DependencyManager()
            dm.addContent(installedPackages)
            piList = dm.getDependencyTree(piList)

        # List of packages to install
        piList = dm.maintainDependencies(piList)

        if len(piList) == 0:
            self.logger.printDefault(
                "No package to remove (to keep dependencies)")
        else:
            total = len(piList)
            worked = 0
            self.logger.progressStart('Uninstall package(s)',
                                      message="Package(s) to remove: " +
                                      ' '.join([str(pi) for pi in piList]),
                                      total=total)
            for pi in piList:
                ip = installedPackages.get(pi)
                self.logger.printDefault("Removing", ip.getIdentifier())
                stepExec = StepExecutor(self.logger,
                                        ip,
                                        installedPackages,
                                        extraEnv=self.getUserEnvVariables())
                stepExec.preUninstall()
                self.logger.printVerbose("Remove folder:", ip.folder)
                shutil.rmtree(str(ip.folder))
                worked += 1
                self.logger.progressWorked('Uninstall package(s)',
                                           worked=worked,
                                           total=total)
                del [installedPackages[pi]]
            self.logger.progressDone('Uninstall package(s)',
                                     message="%d package(s) removed" % (len(piList)))

    def getEnv(self, motifList):
        '''
        Get the env vars declared by given packages and their dependencies
        '''
        piList = self.listDependencies(motifList)
        installedPackages = self.listInstalledPackages()
        out = []
        for pi in piList:
            ip = installedPackages[pi]
            env = ip.jsonpath(JsonConstants.ENV)
            if env is not None:
                stepExec = StepExecutor(self.logger, ip, installedPackages)
                for key, value in env.items():
                    value = stepExec.resolve(value, True, False)
                    out.append((key, value))
        return out


class Workspace():
    '''
    Represent a workspace, where leaf profiles apply
    '''

    def __init__(self, rootFolder, app):
        self.rootFolder = rootFolder
        self.configFile = rootFolder / LeafFiles.PROFILES_FILENAME
        self.dataFolder = rootFolder / LeafFiles.PROFILES_FOLDERNAME
        self.currentLink = self.dataFolder / LeafFiles.CURRENT_PROFILE
        self.app = app

    def getProfileMap(self):
        out = OrderedDict()
        for name, payload in jsonLoadFile(self.configFile).items():
            out[name] = Profile(name,
                                self.dataFolder / name,
                                payload)
        try:
            out[self.getCurrentProfileName()].isCurrentProfile = True
        except:
            pass
        return out

    def getProfile(self, name=None):
        if name is None:
            name = self.getCurrentProfileName()
        pfMap = self.getProfileMap()
        if name not in pfMap:
            raise ValueError("Cannot find profile %s" % name)
        return pfMap.get(name)

    def checkProfile(self, pf):
        # Check packages are installed
        missingPiList = self.app.listDependencies(pf.getPackages(),
                                                  filterInstalled=True)
        if len(missingPiList) > 0:
            raise ValueError("Some packages are not installed, please run 'leaf switch %s'" %
                             (pf.name))
        # Check packages are linked
        installedPackages = self.app.listInstalledPackages()
        for pis in pf.getPackages():
            pi = PackageIdentifier.fromString(pis)
            if pi not in installedPackages:
                piLink = pf.folder / pi.name
                if not piLink.is_symlink():
                    raise ValueError("Some packages are not linked, please run 'leaf switch %s'" %
                                     (pf.name))

    def writeProfiles(self, pfMap):
        self.dataFolder.mkdir(exist_ok=True)
        tmpFile = self.dataFolder / ("tmp-" + LeafFiles.PROFILES_FILENAME)
        with open(str(tmpFile), 'w') as fp:
            payload = OrderedDict()
            for name, pf in pfMap.items():
                payload[name] = pf.json
            json.dump(payload, fp, indent=2, separators=(',', ': '))
        tmpFile.rename(self.configFile)

    def getCurrentProfileName(self):
        if self.currentLink.is_symlink():
            return self.currentLink.resolve().name
        else:
            raise ValueError(
                "No current profile, you need to switch to a profile first")

    def deleteProfile(self, name):
        pfMap = self.getProfileMap()
        if name not in pfMap:
            raise ValueError("Cannot find profile %s" % name)
        out = pfMap[name]
        del pfMap[name]
        self.writeProfiles(pfMap)
        return out

    def createProfile(self, name, motifList=None, envMap=None, initConfigFile=False):
        if name == LeafFiles.CURRENT_PROFILE:
            raise ValueError("%s is not a valid profile name" % name)
        pfMap = {} if initConfigFile else self.getProfileMap()
        if name in pfMap:
            raise ValueError("Profile %s already exists" % name)
        pf = Profile.emptyProfile(name, self.dataFolder / name)
        if motifList is not None:
            pf.addPackages(self.app.resolveLatest(motifList,
                                                  ipMap=self.app.listInstalledPackages(),
                                                  apMap=self.app.listAvailablePackages()))
        pf.addEnv(envMap)
        pfMap[name] = pf
        self.writeProfiles(pfMap)
        return pf

    def updateProfile(self, name=None, motifList=None, envMap=None):
        pf = self.getProfile(name)
        if motifList is not None:
            pf.addPackages(self.app.resolveLatest(motifList,
                                                  ipMap=self.app.listInstalledPackages(),
                                                  apMap=self.app.listAvailablePackages()))
        pf.addEnv(envMap)
        pfMap = self.getProfileMap()
        pfMap[pf.name] = pf
        self.writeProfiles(pfMap)
        return pf

    def switchProfile(self, name):
        pf = self.getProfile(name)
        self.provisionProfile(pf)

        if self.currentLink.is_symlink():
            self.currentLink.unlink()

        self.currentLink.symlink_to(pf.name)
        return pf

    def provisionProfile(self, pf):
        if not self.dataFolder.is_dir():
            self.dataFolder.mkdir()
        elif pf.folder.is_dir():
            shutil.rmtree(str(pf.folder))
        pf.folder.mkdir()
        if len(pf.getPackages()) > 0:
            self.app.installPackages(pf.getPackages())
            installedPackages = self.app.listInstalledPackages()
            for pi in self.app.listDependencies(pf.getPackages()):
                piFolder = pf.folder / pi.name
                if piFolder.exists():
                    piFolder = pf.folder / str(pi)
                ip = installedPackages.get(pi)
                if ip is None:
                    raise ValueError("Cannot find package %s" % pi)
                piFolder.symlink_to(ip.folder)

    def getProfileEnv(self, name=None):
        pf = self.getProfile(name)
        self.checkProfile(pf)
        out = self.app.getEnv(pf.getPackages())
        out.extend(pf.getEnv().items())
        return out
