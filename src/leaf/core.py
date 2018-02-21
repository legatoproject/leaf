'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import apt
from collections import OrderedDict
import datetime
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tarfile import TarFile
import urllib.request

from leaf import __version__
from leaf.constants import JsonConstants, LeafConstants, LeafFiles
from leaf.model import Manifest, InstalledPackage, AvailablePackage, LeafArtifact,\
    PackageIdentifier
from leaf.ui import askYesNo
from leaf.utils import resolveUrl, getCachedArtifactName, isFolderIgnored,\
    markFolderAsIgnored, openOutputTarFile, computeSha1sum, downloadFile


class QuietLogger ():
    '''
    Print only important informations
    '''

    def isVerbose(self):
        return False

    def progressStart(self, task, message=None, total=-1):
        if message is not None:
            print(message)

    def progressWorked(self, task, message=None, worked=0, total=100, sameLine=False):
        if message is not None:
            if total > 0 and worked <= total:
                message += " [%d%%]" % (worked * 100 / total)
            else:
                message += " [%d/%d]" % (worked, total)
            if sameLine:
                print(message, end='\r')
            else:
                print(message)

    def progressDone(self, task, message=None):
        if message is not None:
            print(message)

    def printMessage(self, *message):
        print(*message)

    def printDetail(self, *message):
        pass

    def printError(self, *message, exception=None):
        print(*message, file=sys.stderr)

    def displayPackage(self, pack):
        print(pack.getIdentifier())

    def displayRemote(self, url, info):
        print(url)


class VerboseLogger (QuietLogger):
    '''
    Prints a lot of information
    '''

    def isVerbose(self):
        return True

    def printDetail(self, *message):
        print(*message)

    def printError(self, *message, exception=None):
        QuietLogger.printError(self, *message)
        if exception is not None:
            print(exception, file=sys.stderr)

    def displayPackage(self, pack):
        QuietLogger.displayPackage(self, pack)
        content = OrderedDict()
        content["Description"] = pack.getDescription()
        if isinstance(pack, AvailablePackage):
            content["Size"] = (pack.getSize(), 'bytes')
            content["Source"] = pack.getUrl()
        elif isinstance(pack, InstalledPackage):
            content["Folder"] = pack.folder
        content["Systems"] = pack.getSupportedOS()
        content["Depends"] = pack.getLeafDepends()
        content["Modules"] = pack.getSupportedModules()
        content["Licenses"] = pack.getLicenses()
        self.prettyprintContent(content)

    def displayRemote(self, url, info):
        QuietLogger.displayRemote(self, url, info)
        content = OrderedDict()
        if info is None:
            content["Status"] = "not fetched yet"
        else:
            content["Name"] = info.get(JsonConstants.REMOTE_NAME)
            content["Description"] = info.get(
                JsonConstants.REMOTE_DESCRIPTION)
            content["Last update"] = info.get(
                JsonConstants.REMOTE_DATE)
        self.prettyprintContent(content)

    def prettyprintContent(self, content, indent=4, separator=':', ralign=False):
        '''
        Display formatted content
        '''
        if content is not None:
            maxlen = 0
            indentString = ' ' * indent
            if ralign:
                maxlen = len(
                    max(filter(lambda k: content.get(k) is not None, content), key=len))
            for k, v in content.items():
                if isinstance(v, dict) or isinstance(v, list):
                    if len(v) > 0:
                        print(indentString + k.rjust(maxlen),
                              separator,
                              str(v[0]))
                        for o in v[1:]:
                            print(indentString + (' ' * len(k)).rjust(maxlen),
                                  ' ' * len(separator),
                                  str(o))
                elif isinstance(v, tuple):
                    if len(v) > 0 and v[0] is not None:
                        print(indentString + k.rjust(maxlen),
                              separator,
                              ' '.join(map(str, v)))
                elif v is not None:
                    print(indentString + k.rjust(maxlen),
                          separator,
                          str(v))


class JsonLogger(QuietLogger):
    '''
    Print information in a machine readable format (json)
    '''

    def printJson(self, content):
        print(json.dumps(content, sort_keys=True, indent=None), flush=True)

    def isVerbose(self):
        return False

    def progressStart(self, task, message=None, total=-1):
        self.printJson({
            'event': "progressStart",
            'task': task,
            'message': message,
            'total': total
        })

    def progressWorked(self, task, message=None, worked=0, total=100, sameLine=False):
        self.printJson({
            'event': "progressWorked",
            'task': task,
            'message': message,
            'worked': worked,
            'total': total
        })

    def progressDone(self, task, message=None):
        self.printJson({
            'event': "progressDone",
            'task': task,
            'message': message
        })

    def printMessage(self, *message):
        self.printJson({
            'event': "message",
            'message': " ".join(map(str, message)),
        })

    def printDetail(self, *message):
        self.printJson({
            'event': "detail",
            'message': " ".join(map(str, message)),
        })

    def printError(self, *message, exception=None):
        self.printJson({
            'event': "error",
            'message': " ".join(map(str, message)),
        })

    def displayPackage(self, pack):
        content = {
            'event': "displayPackage",
            'manifest': pack.json,
        }
        if isinstance(pack, InstalledPackage):
            content['folder'] = str(pack.folder)
        elif isinstance(pack, AvailablePackage):
            content['url'] = pack.getUrl()
        self.printJson(content)
        pass

    def displayRemote(self, url, info):
        self.printJson({
            'event': "displayRemote",
            'url': url,
            'data': info,
        })


class LeafUtils():
    '''
    Useful simple methods
    '''
    @staticmethod
    def findPackageIdentifiers(motifList, contentDict):
        '''
        Search a package given a full packageidentifier
        or only a name (latest version will be returned then.
        '''
        out = []
        for motif in motifList:
            pi = None
            if PackageIdentifier.isValidIdentifier(motif):
                pi = PackageIdentifier.fromString(motif)
            else:
                for pi in sorted(filter(lambda pi: pi.name == motif, contentDict.keys())):
                    # loop to get the last item
                    pass
            if pi is not None:
                out.append(pi)
            else:
                raise ValueError(
                    "Cannot find package matching: " + motif)
        return out

    @staticmethod
    def getMissingAptDepends(apList):
        '''
        List all apt missing packages needed by given leaf available packages
        '''
        out = set()
        cache = apt.Cache()
        for ap in apList:
            for deb in ap.jsonpath(JsonConstants.INFO, JsonConstants.INFO_DEPENDS, JsonConstants.INFO_DEPENDS_DEB, default=[]):
                if cache.is_virtual_package(deb):
                    if len([p for p in cache.get_providing_packages(deb) if cache[p].installed]) == 0:
                        out.add(deb)
                elif deb not in cache:
                    out.add(deb)
                elif not cache[deb].installed:
                    out.add(deb)
        return out

    @staticmethod
    def getDependencies(piList, content, outList):
        '''
        Recursively search dependencies
        '''
        for pi in piList:
            pack = content.get(pi)
            if pack is None:
                raise ValueError("Cannot find package: " + str(pi))
            if pack not in outList:
                outList.append(pack)
                LeafUtils.getDependencies(pack.getLeafDepends(),
                                          content,
                                          outList)

    @staticmethod
    def computePackagesToInstall(piList, apContent):
        '''
        Build the ordered list of packages to install
        '''
        out = []
        LeafUtils.getDependencies(piList, apContent, out)
        out = LeafUtils.sortPackagesByDependencies(out)
        return out

    @staticmethod
    def computePackagesToUninstall(piList, ipContent):
        '''
        Build the list of package to uninstall and keep dependencies needed by master packages
        '''
        out = []
        LeafUtils.getDependencies(piList, ipContent, out)
        out = LeafUtils.sortPackagesByDependencies(out, masterFirst=True)
        for ip in ipContent.values():
            if ip not in out:
                keep = []
                LeafUtils.getDependencies(
                    [ip.getIdentifier()], ipContent, keep)
                out = [p for p in out if p not in keep]
        return out

    @staticmethod
    def sortPackagesByDependencies(packList, masterFirst=False):
        '''
        Sort package to respect dependencies for install/uninstall
        '''
        inList = list(packList)
        outList = []

        def checker(pack):
            for pi in pack.getLeafDepends():
                if pi not in map(Manifest.getIdentifier, outList):
                    return False
            return True
        while True:
            packagesWithSatisfiedDependencies = list(filter(checker, inList))
            for pack in packagesWithSatisfiedDependencies:
                inList.remove(pack)
                outList.append(pack)
            if len(inList) == 0:
                break
            elif len(packagesWithSatisfiedDependencies) == 0:
                raise ValueError('Dependency error: ' +
                                 ', '.join(str(m.getIdentifier()) for m in inList))
        if masterFirst:
            outList.reverse()
        return outList


class LicenseManager ():
    '''
    Handle license acceptation
    '''

    def __init__(self, logger, cacheFile=LeafFiles.LICENSES_CACHE_FILE):
        self.cacheFile = cacheFile
        self.logger = logger

    def readLicenses(self):
        '''
        Read license cache
        '''
        out = {}
        if self.cacheFile.exists():
            with open(str(self.cacheFile), 'r') as fp:
                out = json.load(fp)
        return out

    def writeLicenses(self, licenses):
        '''
        Write the given licenses
        '''
        with open(str(self.cacheFile), 'w') as fp:
            json.dump(licenses, fp, indent=2, separators=(',', ': '))

    def checkLicenses(self, packageList):
        '''
        Checks that all given packages have their licenses accepted
        '''
        out = []
        licenses = self.readLicenses()
        for pack in packageList:
            licenses = pack.getLicenses()
            if licenses is not None:
                for lic in licenses:
                    if lic not in out and lic not in licenses:
                        out.append(lic)
        return out

    def acceptLicense(self, lic):
        self.logger.printMessage("You need to accept the license:", lic)
        if askYesNo(self.logger,
                    "Do you want to display the license text?",
                    default=False):
            with urllib.request.urlopen(lic) as req:
                text = io.TextIOWrapper(req).read()
                self.logger.printMessage(text)
        out = askYesNo(self.logger,
                       "Do you accept the license?",
                       default=True)
        if out:
            licenses = self.readLicenses()
            licenses[lic] = str(datetime.datetime.utcnow())
            self.writeLicenses(licenses)
        return out


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
        self.logger.progressStart('steps', total=len(steps))
        worked = 0
        for step in steps:
            if JsonConstants.STEP_LABEL in step:
                self.logger.printMessage(step[JsonConstants.STEP_LABEL])
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
            self.logger.progressWorked('steps',
                                       worked=worked,
                                       total=len(steps))
        self.logger.progressDone('steps')

    def doExec(self, step):
        command = [self.resolve(arg)
                   for arg in step[JsonConstants.STEP_EXEC_COMMAND]]
        self.logger.printDetail("Exec:", ' '.join(command))
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
                self.logger.printDetail(
                    "Return code is ", rc, ", but step ignores failure")
            else:
                raise ValueError("Step exited with return code " + str(rc))

    def doCopy(self, step):
        src = self.resolve(
            step[JsonConstants.STEP_COPY_SOURCE], prefixWithFolder=True)
        dst = self.resolve(
            step[JsonConstants.STEP_COPY_DESTINATION], prefixWithFolder=True)
        self.logger.printDetail("Copy:", src, "->", dst)
        shutil.copy2(src, dst)

    def doLink(self, step):
        target = self.resolve(
            step[JsonConstants.STEP_LINK_NAME], prefixWithFolder=True)
        source = self.resolve(
            step[JsonConstants.STEP_LINK_TARGET], prefixWithFolder=True)
        self.logger.printDetail("Link:", source, " -> ", target)
        os.symlink(source, target)

    def doDelete(self, step):
        for file in step[JsonConstants.STEP_DELETE_FILES]:
            resolvedFile = self.resolve(file, prefixWithFolder=True)
            self.logger.printDetail("Delete:", resolvedFile)
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
                self.logger.printDetail(
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
        with open(str(manifestFile), 'r') as fp:
            manifest = Manifest(json.load(fp))
            self.logger.printMessage("Found:", manifest.getIdentifier())
            self.logger.printMessage(
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
        infoNode[JsonConstants.REMOTE_DATE] = str(datetime.datetime.utcnow())

        rootNode = OrderedDict()
        rootNode[JsonConstants.INFO] = infoNode
        if composites is not None and len(composites) > 0:
            rootNode[JsonConstants.REMOTE_COMPOSITE] = composites

        packagesNode = []
        rootNode[JsonConstants.REMOTE_PACKAGES] = packagesNode
        for a in artifacts:
            la = LeafArtifact(a)
            self.logger.printMessage("Found:", la.getIdentifier())
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
            self.logger.printMessage("Index created:", outputFile)


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
            with open(str(self.configurationFile), 'r') as fp:
                return json.load(fp)
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

    def readRemotesCache(self):
        if self.cacheFile.exists():
            with open(str(self.cacheFile), 'r') as fp:
                return json.load(fp)

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
                self.logger.printMessage(
                    "Remotes have changed, you need to fetch content")

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
                    self.logger.printMessage(
                        "Remotes have changed, you need to fetch content")

    def remoteList(self):
        '''
        List all remotes from configuration
        '''
        config = self.readConfiguration()
        out = OrderedDict()
        cache = self.readRemotesCache()
        for remote in config.get(JsonConstants.CONFIG_REMOTES, []):
            if cache is not None and remote in cache:
                out[remote] = cache[remote].get(JsonConstants.INFO)
            else:
                out[remote] = None
        return out

    def listAvailablePackages(self):
        '''
        List all available package
        '''
        out = {}
        cache = self.readRemotesCache()
        if cache is not None:
            for url, content in cache.items():
                packages = content.get(JsonConstants.REMOTE_PACKAGES)
                if packages is not None:
                    for package in packages:
                        ap = AvailablePackage(package, url)
                        out[ap.getIdentifier()] = ap
        return out

    def fetchUrl(self, remoteurl, content):
        '''
        Fetch an URL content and keep it in the given dict
        '''
        if remoteurl not in content:
            try:
                with urllib.request.urlopen(remoteurl, timeout=LeafConstants.DOWNLOAD_TIMEOUT) as url:
                    data = json.loads(url.read().decode())
                    self.logger.printMessage("Fetched", remoteurl)
                    content[remoteurl] = data
                    composites = data.get(JsonConstants.REMOTE_COMPOSITE)
                    if composites is not None:
                        for composite in composites:
                            self.fetchUrl(resolveUrl(
                                remoteurl, composite), content)
            except Exception as e:
                self.logger.printError("Error fetching", remoteurl, ":", e)

    def fetchRemotes(self):
        '''
        Fetch remotes
        '''
        content = OrderedDict()
        remotes = self.remoteList()
        self.logger.progressStart('fetch', total=len(remotes))
        worked = 0
        for remote in self.remoteList():
            self.fetchUrl(remote, content)
            worked += 1
            self.logger.progressWorked('fetch',
                                       worked=worked,
                                       total=len(remotes))
        with open(str(self.cacheFile), 'w') as output:
            json.dump(content, output)
        self.logger.progressDone('fetch',
                                 message="Fetched %d remote repositories" % (len(remotes)))

    def listInstalledPackages(self):
        '''
        Return all installed packages
        '''
        out = {}
        for folder in self.getInstallFolder().iterdir():
            if folder.is_dir() and not isFolderIgnored(folder):
                manifest = folder / LeafConstants.MANIFEST
                if manifest.is_file():
                    ip = InstalledPackage(manifest)
                    out[ip.getIdentifier()] = ip
        return out

    def install(self, motifList,
                forceInstall=False,
                downloadOnly=False,
                keepFolderOnError=False,
                skipLicenses=False):
        '''
        To download & install packages with dependencies
        '''
        installedPackages = self.listInstalledPackages()
        availablePackages = self.listAvailablePackages()
        packageIdentifiers = LeafUtils.findPackageIdentifiers(
            motifList, availablePackages)

        # List of packages to install
        apToInstall = LeafUtils.computePackagesToInstall(
            packageIdentifiers, availablePackages)

        # Check if already installed
        apToInstall[:] = [
            ap for ap in apToInstall if not ap.getIdentifier() in installedPackages]
        if len(apToInstall) == 0:
            self.logger.printMessage("All packages are already installed")
            return True

        # Check supported Os
        apIncompatible = [ap for ap in apToInstall if not ap.isSupported()]
        if len(apIncompatible) > 0:
            self.logger.printError("Some packages are not compatible with your system: ",
                                   ", ".join([str(ap.getIdentifier()) for ap in apIncompatible]))
            if not forceInstall:
                raise ValueError("Unsupported system")

        # Check dependencies
        missingAptDepends = LeafUtils.getMissingAptDepends(apToInstall)
        if len(missingAptDepends) > 0:
            self.logger.printError(
                "You may have to install missing dependencies by running:")
            self.logger.printError("  $",
                                   "sudo apt-get update",
                                   "&&",
                                   "sudo apt-get install",
                                   ' '.join(missingAptDepends))
            if not forceInstall and not downloadOnly:
                raise ValueError("Missing dependencies")

        if not skipLicenses:
            lm = LicenseManager(self.logger)
            for lic in lm.checkLicenses(apToInstall):
                if not lm.acceptLicense(lic):
                    raise ValueError("License must be accepted: " + lic)

        total = len(apToInstall)
        if not downloadOnly:
            total *= 2
        worked = 0
        self.logger.progressStart('install',
                                  message="Packages to install: " +
                                  '\n\t'.join([str(m.getIdentifier())
                                               for m in apToInstall]),
                                  total=total)

        toInstall = OrderedDict()
        # Download package if needed
        for ap in apToInstall:
            toInstall[ap] = LeafArtifact(downloadFile(ap.getUrl(),
                                                      LeafFiles.FILES_CACHE_FOLDER,
                                                      self.logger,
                                                      filename=getCachedArtifactName(
                ap.getFilename(), ap.getSha1sum()),
                sha1sum=ap.getSha1sum()))
            worked += 1
            self.logger.progressWorked('install', worked=worked, total=total)

        if downloadOnly:
            self.logger.progressDone(
                'install',
                message="%d %s been downloaded" % (
                    len(toInstall),
                    "packages have" if len(toInstall) > 1 else "package has"))
        else:
            # Extract package
            for ap, la in toInstall.items():
                self.logger.printMessage("Installing", ap.getIdentifier())
                self.extractPackage(la,
                                    installedPackages,
                                    ap.getUrl(),
                                    keepFolderOnError=keepFolderOnError)
                worked += 1
                self.logger.progressWorked(
                    'install', worked=worked, total=total)
            self.logger.progressDone(
                'install',
                message="%d %s been installed" % (
                    len(toInstall),
                    "packages have" if len(toInstall) > 1 else "package has"))

    def extractPackage(self, leafArtifact, installedPackages=None, urlSource=None, keepFolderOnError=False):
        '''
        Extract & post install given package
        '''

        if installedPackages is None:
            installedPackages = self.listInstalledPackages()

        targetFolder = self.getInstallFolder() / str(leafArtifact.getIdentifier())
        if targetFolder.is_dir():
            raise ValueError("Folder already exists: " + str(targetFolder))

        # Create folder
        os.makedirs(str(targetFolder))
        try:
            self.logger.printDetail(
                "Extract", leafArtifact.path, "in", targetFolder)
            with TarFile.open(str(leafArtifact.path)) as tf:
                tf.extractall(str(targetFolder))

            # Execute post install steps
            newPackage = InstalledPackage(
                targetFolder / LeafConstants.MANIFEST)
            StepExecutor(self.logger,
                         newPackage,
                         installedPackages,
                         extraEnv=self.getUserEnvVariables()).postInstall()
            installedPackages[newPackage.getIdentifier()] = newPackage
            return newPackage
        except Exception as e:
            self.logger.printError("Error during installation:", e)
            if keepFolderOnError:
                targetFolderIgnored = markFolderAsIgnored(targetFolder)
                self.logger.printDetail("Mark folder as ignored:",
                                        targetFolderIgnored)
            else:
                self.logger.printDetail("Remove folder:", targetFolder)
                shutil.rmtree(str(targetFolder), True)
            raise e

    def uninstall(self, motifList):
        '''
        Remove given package
        '''
        installedPackages = self.listInstalledPackages()
        packageIdentifiers = LeafUtils.findPackageIdentifiers(
            motifList, installedPackages)

        # List of packages to install
        ipToRemove = LeafUtils.computePackagesToUninstall(
            packageIdentifiers, installedPackages)
        if len(ipToRemove) == 0:
            self.logger.printMessage(
                "No package to remove (to keep dependencies)")
        else:
            total = len(ipToRemove)
            worked = 0
            self.logger.progressStart('uninstall',
                                      message="Packages to remove: " + '\n\t'.join(
                                          [str(m.getIdentifier()) for m in ipToRemove]),
                                      total=total)
            for ip in ipToRemove:
                self.logger.printMessage("Removing", ip.getIdentifier())
                stepExec = StepExecutor(self.logger,
                                        ip,
                                        installedPackages,
                                        extraEnv=self.getUserEnvVariables())
                stepExec.preUninstall()
                self.logger.printDetail("Remove folder:", ip.folder)
                shutil.rmtree(str(ip.folder))
                worked += 1
                self.logger.progressWorked('uninstall',
                                           worked=worked,
                                           total=total)
                del [installedPackages[ip.getIdentifier()]]
            self.logger.progressDone(
                'uninstall',
                message="%d %s been removed" % (
                    len(ipToRemove),
                    "packages have" if len(ipToRemove) > 1 else "package has"))

    def getEnv(self, motifList):
        '''
        Get the env vars declared by given packages and their dependencies
        '''
        installedPackages = self.listInstalledPackages()
        packageIdentifiers = LeafUtils.findPackageIdentifiers(
            motifList, installedPackages)

        out = OrderedDict()
        ipList = []
        LeafUtils.getDependencies(
            packageIdentifiers, installedPackages, ipList)
        LeafUtils.sortPackagesByDependencies(ipList)
        for ip in ipList:
            env = ip.json.get(JsonConstants.ENV)
            if env is not None:
                stepExec = StepExecutor(self.logger, ip, installedPackages)
                for key, value in env.items():
                    value = stepExec.resolve(value, True, False)
                    out[key] = value
        return out
