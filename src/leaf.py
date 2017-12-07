#!/usr/bin/env python3
# encoding: utf-8
'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2017 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/

'''
__version__ = 0.1
from _collections import OrderedDict
import apt
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import argparse
from code import InteractiveConsole
import datetime
from functools import total_ordering
import hashlib
import io
import json
import os
from pathlib import Path
import re
import requests
import semver
import shutil
import subprocess
import sys
from tarfile import TarFile
import time
from urllib.parse import urlparse, urlunparse
import urllib.request


class LeafConstants():
    '''
    Constants needed by Leaf
    '''
    MIN_PYTHON_VERSION = (3, 5)
    DEFAULT_LEAF_ROOT = Path.home() / 'legato' / 'packages'
    DEFAULT_CONFIG_FILE = Path.home() / '.leaf-config.json'
    CACHE_FOLDER = Path.home() / '.cache' / 'leaf'
    FILES_CACHE_FOLDER = CACHE_FOLDER / "files"
    REMOTES_CACHE_FILE = CACHE_FOLDER / 'remotes.json'
    LICENSES_CACHE_FILE = CACHE_FOLDER / 'licenses.json'

    DEFAULT_CONFIGURATION = {
        'remotes': [
            "https://raw.githubusercontent.com/seb-sierra/leaf/master/leaf-core/src/test/resources/repo/index.json"]}
    EXTENSION_JSON = '.json'
    MANIFEST = 'manifest' + EXTENSION_JSON
    VAR_PREFIX = '@'


class JsonConstants():
    '''
    Constants for Json grammar
    '''
    # Configuration
    CONFIG_REMOTES = 'remotes'
    CONFIG_ENV = 'env'
    CONFIG_ROOT = 'rootfolder'
    CONFIG_VARIABLES = 'variables'

    # Index
    REMOTE_NAME = 'name'
    REMOTE_DATE = 'date'
    REMOTE_DESCRIPTION = 'description'
    REMOTE_COMPOSITE = 'composite'
    REMOTE_PACKAGES = 'packages'
    REMOTE_PACKAGE_SIZE = 'size'
    REMOTE_PACKAGE_FILE = 'file'
    REMOTE_PACKAGE_SHA1SUM = 'sha1sum'

    # Manifest
    INFO = 'info'
    INFO_NAME = 'name'
    INFO_VERSION = 'version'
    INFO_DEPENDS = 'depends'
    INFO_DEPENDS_LEAF = 'leaf'
    INFO_DEPENDS_DEB = 'deb'
    INFO_MASTER = 'master'
    INFO_DESCRIPTION = 'description'
    INFO_LICENSES = 'licenses'
    INSTALL = 'install'
    UNINSTALL = 'uninstall'
    STEP_TYPE = 'type'
    STEP_EXEC = 'exec'
    STEP_EXEC_ENV = 'env'
    STEP_EXEC_COMMAND = 'command'
    STEP_EXEC_VERBOSE = 'verbose'
    STEP_LINK = 'link'
    STEP_LINK_NAME = 'name'
    STEP_LINK_TARGET = 'target'
    STEP_COPY = 'copy'
    STEP_COPY_SOURCE = 'source'
    STEP_COPY_DESTINATION = 'destination'
    STEP_DELETE = 'delete'
    STEP_DELETE_FILES = 'files'
    STEP_DOWNLOAD = 'download'
    STEP_DOWNLOAD_URL = 'url'
    STEP_DOWNLOAD_RELATIVEURL = 'relativeUrl'
    STEP_DOWNLOAD_FILENAME = 'filename'
    STEP_DOWNLOAD_SHA1SUM = REMOTE_PACKAGE_SHA1SUM
    INSTALLED_DETAILS = 'details'
    INSTALLED_DETAILS_SOURCE = 'source'
    INSTALLED_DETAILS_DATE = 'installDate'
    ENV = 'env'

    # Extra
    INFO_SUPPORTEDMODULES = 'supportedModules'
    INFO_SUPPORTEDOS = 'supportedOs'


class LeafUtils():
    '''
    Useful simple methods
    '''
    _IGNORED_PATTERN = re.compile('^.*_ignored[0-9]*$')
    _LEAF_EXT = {'.xz': 'xz',
                 '.bz2': 'bz2',
                 '.tgz': 'gz',
                 '.gz': 'gz'}

    @staticmethod
    def askYesNo(message, default=None):
        label = " (yes/no)"
        if default == True:
            label = " (YES/no)"
        elif default == False:
            label = " (yes/NO)"
        while True:
            answer = InteractiveConsole().raw_input(
                message + label + "\n").strip()
            if answer == "":
                if default == True:
                    answer = 'y'
                elif default == False:
                    answer = 'n'
            if answer.lower() == 'y' or answer.lower() == 'yes':
                return True
            if answer.lower() == 'n' or answer.lower() == 'no':
                return False

    @staticmethod
    def jsonGet(json, path, default=None):
        '''
        Utility to browse json and reduce None testing
        '''
        if path is None or len(path) == 0:
            return json
        k = path[0]
        if not isinstance(json, dict) or k not in json:
            return default
        return LeafUtils.jsonGet(json.get(k), path[1:], default)

    @staticmethod
    def isFolderIgnored(folder):
        return LeafUtils._IGNORED_PATTERN.match(folder.name) is not None

    @staticmethod
    def markFolderAsIgnored(folder):
        oldname = folder.name
        newname = oldname + "_ignored" + str(int(time.time()))
        if LeafUtils._IGNORED_PATTERN.match(newname) is None:
            raise ValueError('Invalid ignored folder name: ' + newname)
        out = folder.parent / newname
        folder.rename(out)
        return out

    @staticmethod
    def guessCompression(path, prefix=""):
        '''
        Guess the compression from the file extension
        '''
        return prefix + LeafUtils._LEAF_EXT.get(path.suffix, 'xz')

    @staticmethod
    def now():
        '''
        Return the current date as string
        '''
        return str(datetime.datetime.utcnow())

    @staticmethod
    def findPackageIdentifiers(motifList, contentDict):
        '''
        Search a package given a full packageidentifier 
        or only a name (latest version will be returned then.
        '''

        out = []
        for motif in motifList:
            pi = PackageIdentifier.fromString(motif)
            if pi is None:
                for pi in sorted(filter(lambda pi: pi.name == motif, contentDict.keys())):
                    # loop to get the last item
                    pass
            if pi is not None and pi not in out:
                out.append(pi)
            else:
                raise ValueError(
                    "Cannot find package matching: " + motif)
        return out

    @staticmethod
    def resolveUrl(remoteUrl, subPath):
        '''
        Resolves a relative URL
        '''
        url = urlparse(remoteUrl)
        newPath = Path(url.path).parent / subPath
        url = url._replace(path=str(newPath))
        return urlunparse(url)

    @staticmethod
    def getMissingAptDepends(availablePackages):
        '''
        List all apt missing packages needed by given leaf available packages
        '''
        out = set()
        cache = apt.Cache()
        for ap in availablePackages:
            out.update(LeafUtils.jsonGet(
                ap.getNodeInfo(), [JsonConstants.INFO_DEPENDS, JsonConstants.INFO_DEPENDS_DEB], []))
        return [deb for deb in out if deb not in cache or not cache[deb].installed]

    @staticmethod
    def getDependencies(piList, content, outList):
        '''
        Recursively search dependencies
        '''
        for pi in piList:
            pack = content.get(pi)
            if pack is None:
                raise ValueError(
                    "Cannot findPackageIdentifiers package: " + pi)
            if pack not in outList:
                outList.append(pack)
                LeafUtils.getDependencies(
                    pack.getLeafDepends(), content, outList)

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
            if ip.isMaster() and ip not in out:
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

    @staticmethod
    def sha1sum(file):
        '''
        Return the sha1 of the given file
        '''
        BLOCKSIZE = 4096
        hasher = hashlib.sha1()
        with open(str(file), 'rb') as fp:
            buf = fp.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = fp.read(BLOCKSIZE)
        return hasher.hexdigest()

    @staticmethod
    def download(url, folder, filename=None, sha1sum=None):
        '''
        Download an artifact 
        '''
        if filename is None:
            parsedUrl = urlparse(url)
            filename = Path(parsedUrl.path).name
        targetFile = folder / filename
        if targetFile.exists():
            if sha1sum is None:
                print("File exists but cannot be verified,",
                      targetFile.name, " will be re-downloaded")
                os.remove(str(targetFile))
            elif sha1sum != LeafUtils.sha1sum(targetFile):
                print("File exists but SHA1 differs,",
                      targetFile.name, " will be re-downloaded")
                os.remove(str(targetFile))
            else:
                print("File already in cache:", targetFile.name)
        if not targetFile.exists():
            req = requests.get(url, stream=True)
            total_size = int(req.headers.get('content-length', 0))
            current_size = 0
            with open(str(targetFile), 'wb') as fp:
                for data in req.iter_content(1024 * 1024):
                    current_size += len(data)
                    progress = "[{0}%]".format(
                        int(current_size * 100 / total_size))
                    print("Downloading", targetFile.name, progress,
                          end='\r', flush=True)
                    fp.write(data)
            print("File downloaded", targetFile)
            if sha1sum is not None and sha1sum != LeafUtils.sha1sum(targetFile):
                raise ValueError(
                    "Invalid SHA1 sum for " + targetFile.name + ", expecting " + sha1sum)
        return targetFile


@total_ordering
class PackageIdentifier ():

    _REGEX = re.compile('^([a-zA-Z-]+)$')
    _SEPARATOR = '_'

    @staticmethod
    def fromString(pis):
        split = pis.partition(PackageIdentifier._SEPARATOR)
        if PackageIdentifier._REGEX.match(split[0]) and semver._REGEX.match(split[2]):
            return PackageIdentifier(split[0], split[2])

    @staticmethod
    def isValidName(name):
        match = PackageIdentifier._REGEX.match(name)
        return match is not None

    def __init__(self, name, version):
        if not PackageIdentifier.isValidName(name):
            raise ValueError("Invalid package name: " + name)
        self.name = name
        self.version = version

    def __str__(self):
        return self.name + PackageIdentifier._SEPARATOR + self.version

    def _is_valid_operand(self, other):
        return (hasattr(other, "name") and
                hasattr(other, "version"))

    def __hash__(self):
        return hash((self.name, self.version))

    def __eq__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        return self.name == other.name and self.version == other.version

    def __lt__(self, other):
        if not self._is_valid_operand(other):
            return NotImplemented
        if self.name == other.name:
            return semver.compare(self.version, other.version) < 0
        return self.name < other.name


class Manifest():
    '''
    Represent a Manifest model object
    '''

    def __init__(self, json):
        self.json = json

    def __str__(self):
        return str(self.getIdentifier())

    def getNodeInfo(self):
        return self.json[JsonConstants.INFO]

    def getName(self):
        return self.getNodeInfo()[JsonConstants.INFO_NAME]

    def getVersion(self):
        return self.getNodeInfo()[JsonConstants.INFO_VERSION]

    def getIdentifier(self):
        return PackageIdentifier(self.getName(), self.getVersion())

    def getDescription(self):
        return self.getNodeInfo().get(JsonConstants.INFO_DESCRIPTION)

    def isMaster(self):
        info = self.getNodeInfo()
        return JsonConstants.INFO_MASTER in info and info[JsonConstants.INFO_MASTER]

    def getLicenses(self):
        return LeafUtils.jsonGet(self.getNodeInfo(), [JsonConstants.INFO_LICENSES], [])

    def getLeafDepends(self):
        return [PackageIdentifier.fromString(pis)
                for pis in LeafUtils.jsonGet(self.getNodeInfo(),
                                             [JsonConstants.INFO_DEPENDS,
                                              JsonConstants.INFO_DEPENDS_LEAF], [])]

    def getSupportedModules(self):
        return self.getNodeInfo().get(JsonConstants.INFO_SUPPORTEDMODULES)


class LeafArtifact(Manifest):
    '''
    Represent a tar/xz or a single manifest.json file
    '''

    def __init__(self, path):
        self.path = path
        if self.isJsonOnly():
            with open(str(self.path), 'r') as fp:
                Manifest.__init__(self, json.load(fp))
        else:
            with TarFile.open(str(self.path), 'r') as tarfile:
                Manifest.__init__(self, json.load(io.TextIOWrapper(
                    tarfile.extractfile(LeafConstants.MANIFEST))))

    def isJsonOnly(self):
        return self.path.suffix == LeafConstants.EXTENSION_JSON


class AvailablePackage(Manifest):
    '''
    Represent a package available in a remote repository
    '''

    def __init__(self, jsonPayload, remoteUrl):
        super().__init__(jsonPayload)
        self.remoteUrl = remoteUrl

    def __str__(self, *args, **kwargs):
        return "{pi} [{path}] ({size} bytes)".format(
            pi=str(self.getIdentifier()),
            path=self.getSubPath(),
            size=self.getSize())

    def getSize(self):
        return self.json.get(JsonConstants.REMOTE_PACKAGE_SIZE)

    def getSha1sum(self):
        return self.json.get(JsonConstants.REMOTE_PACKAGE_SHA1SUM)

    def getSubPath(self):
        return self.json.get(JsonConstants.REMOTE_PACKAGE_FILE)

    def getUrl(self):
        return LeafUtils.resolveUrl(self.remoteUrl, self.getSubPath())


class InstalledPackage(Manifest):
    '''
    Represent an installed package
    '''

    def __init__(self, manifestFile):
        with open(str(manifestFile), 'r') as fp:
            super().__init__(json.load(fp))
        self.folder = manifestFile.parent

    def __str__(self):
        return "{pi} [{path}]".format(pi=self.getIdentifier(), path=str(self.folder))

    def setDetail(self, key, value):
        details = LeafUtils.jsonGet(
            self.json, [JsonConstants.INSTALLED_DETAILS], {})
        details[key] = value
        self.json[JsonConstants.INSTALLED_DETAILS] = details
        with open(str(self.folder / LeafConstants.MANIFEST), 'w') as output:
            json.dump(self.json, output, indent=4, separators=(',', ': '))

    def getDetail(self, key):
        return LeafUtils.jsonGet(self.json, [JsonConstants.INSTALLED_DETAILS, key])


class LicenseManager ():
    '''
    Handle license acceptation
    '''

    def readLicenses(self):
        '''
        Read license cache
        '''
        out = {}
        if LeafConstants.LICENSES_CACHE_FILE.exists():
            with open(str(LeafConstants.LICENSES_CACHE_FILE), 'r') as fp:
                out = json.load(fp)
        return out

    def writeLicenses(self, licenses):
        '''
        Write the given licenses
        '''
        with open(str(LeafConstants.LICENSES_CACHE_FILE), 'w') as fp:
            json.dump(licenses, fp, indent=2, separators=(',', ': '))

    def checkLicenses(self, packageList):
        '''
        Checks that all given packages have their licenses accepted
        '''
        out = []
        licenses = self.readLicenses()
        for pack in packageList:
            for lic in pack.getLicenses():
                if lic not in out and lic not in licenses:
                    out.append(lic)
        return out

    def acceptLicense(self, lic):
        print("You need to accept the license:", lic)
        if LeafUtils.askYesNo("Do you want to display the license text?", default=False):
            with urllib.request.urlopen(lic) as req:
                text = io.TextIOWrapper(req).read()
                print(text)
        out = LeafUtils.askYesNo("Do you accept the license?", default=True)
        if out:
            licenses = self.readLicenses()
            licenses[lic] = LeafUtils.now()
            self.writeLicenses(licenses)
        return out


class StepExecutor():
    '''
    Used to execute post install & pre uninstall steps
    '''

    def __init__(self, package, otherPackages, extraEnv=None):
        self.extraEnv = extraEnv
        self.verbose = False
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

    def postInstall(self, installedPackage):
        if JsonConstants.INSTALL in installedPackage.json:
            print("Execute post-install steps for:",
                  installedPackage.getIdentifier())
            self.runSteps(
                installedPackage.json[JsonConstants.INSTALL], installedPackage)

    def preUninstall(self, installedPackage):
        if JsonConstants.UNINSTALL in installedPackage.json:
            print("Execute pre-uninstall steps for:",
                  installedPackage.getIdentifier())
            self.runSteps(
                installedPackage.json[JsonConstants.UNINSTALL], installedPackage)

    def runSteps(self, stepsJsonArray, ip):
        for step in stepsJsonArray:
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

    def doExec(self, step):
        command = [self.resolve(arg)
                   for arg in step[JsonConstants.STEP_EXEC_COMMAND]]
        print("Exec:", ' '.join(command))
        env = dict(os.environ)
        for k, v in LeafUtils.jsonGet(step, [JsonConstants.STEP_EXEC_ENV], {}).items():
            v = self.resolve(v)
            env[k] = v
            if self.verbose:
                print("(manifest) ENV: %s=%s" % (k, v))
        if self.extraEnv is not None:
            for k, v in self.extraEnv.items():
                v = self.resolve(v)
                env[k] = v
                if self.verbose:
                    print("(user) ENV: %s=%s" % (k, v))
        env["LEAF_VERSION"] = str(__version__)
        stdout = subprocess.DEVNULL
        if self.verbose or LeafUtils.jsonGet(step, [JsonConstants.STEP_EXEC_VERBOSE], default=False):
            stdout = None
        subprocess.run(command,
                       cwd=str(self.targetFolder),
                       env=env,
                       check=True,
                       stdout=stdout,
                       stderr=subprocess.STDOUT)

    def doCopy(self, step):
        src = self.resolve(
            step[JsonConstants.STEP_COPY_SOURCE], prefixWithFolder=True)
        dst = self.resolve(
            step[JsonConstants.STEP_COPY_DESTINATION], prefixWithFolder=True)
        print("Copy:", src, "->", dst)
        shutil.copy2(src, dst)

    def doLink(self, step):
        target = self.resolve(
            step[JsonConstants.STEP_LINK_NAME], prefixWithFolder=True)
        source = self.resolve(
            step[JsonConstants.STEP_LINK_TARGET], prefixWithFolder=True)
        print("Link:", source, " -> ", target)
        os.symlink(source, target)

    def doDelete(self, step):
        for file in step[JsonConstants.STEP_DELETE_FILES]:
            resolvedFile = self.resolve(file, prefixWithFolder=True)
            print("Delete:", resolvedFile)
            os.remove(resolvedFile)

    def doDownload(self, step, ip):
        url = None
        if JsonConstants.STEP_DOWNLOAD_URL in step:
            url = step[JsonConstants.STEP_DOWNLOAD_URL]
        elif JsonConstants.STEP_DOWNLOAD_RELATIVEURL in step:
            url = LeafUtils.resolveUrl(ip.getDetail(JsonConstants.INSTALLED_DETAILS_SOURCE),
                                       step[JsonConstants.STEP_DOWNLOAD_RELATIVEURL])
        else:
            raise ValueError("No url to download")
        LeafUtils.download(url,
                           self.targetFolder,
                           step.get(JsonConstants.STEP_DOWNLOAD_FILENAME),
                           step.get(JsonConstants.STEP_DOWNLOAD_SHA1SUM))

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

    def pack(self, manifestFile, outputFile):
        '''
        Create a leaf artifact from given the manifest.
        if the output file ands with .json, a *manifest only* package will be generated.
        Output file can ends with tar.[gz,xz,bz2] of json
        '''
        with open(str(manifestFile), 'r') as fp:
            manifest = Manifest(json.load(fp))
            print("Found:", manifest.getIdentifier())
            if outputFile.suffix == LeafConstants.EXTENSION_JSON:
                shutil.copy(str(manifestFile), str(outputFile))
                print("Manifest copied:", manifestFile, "-->", outputFile)
            else:
                print("Create tar:", manifestFile, "-->", outputFile)
                with TarFile.open(str(outputFile),
                                  LeafUtils.guessCompression(outputFile, prefix="w:")) as tf:
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
        infoNode[JsonConstants.REMOTE_DATE] = LeafUtils.now()

        rootNode = OrderedDict()
        rootNode[JsonConstants.INFO] = infoNode
        if composites is not None and len(composites) > 0:
            rootNode[JsonConstants.REMOTE_COMPOSITE] = composites

        packagesNode = []
        rootNode[JsonConstants.REMOTE_PACKAGES] = packagesNode
        for a in artifacts:
            la = LeafArtifact(a)
            print("Found:", la.getIdentifier())
            fileNode = OrderedDict()
            fileNode[JsonConstants.REMOTE_PACKAGE_FILE] = str(
                Path(a).relative_to(outputFile.parent))
            fileNode[JsonConstants.REMOTE_PACKAGE_SHA1SUM] = str(
                LeafUtils.sha1sum(a))
            fileNode[JsonConstants.REMOTE_PACKAGE_SIZE] = a.stat().st_size
            fileNode[JsonConstants.INFO] = la.getNodeInfo()
            packagesNode.append(fileNode)

        with open(str(outputFile), 'w') as out:
            json.dump(rootNode, out, indent=2)
            print("Index created:", str(outputFile))


class LeafApp(LeafRepository):
    '''
    Main API for using Leaf
    '''

    def __init__(self, configurationFile):
        '''
        Constructor
        '''
        self.configurationFile = configurationFile
        # Create folders if needed
        LeafConstants.FILES_CACHE_FOLDER.mkdir(parents=True, exist_ok=True)

    def readConfiguration(self):
        '''
        Read the configuration if it exists, else return the the default configuration
        '''
        if self.configurationFile.exists():
            with open(str(self.configurationFile), 'r') as fp:
                return json.load(fp)
        # Default configuration here
        out = dict(LeafConstants.DEFAULT_CONFIGURATION)
        self.writeConfiguration(out)
        return out

    def writeConfiguration(self, config):
        '''
        Write the given configuration
        '''
        with open(str(self.configurationFile), 'w') as fp:
            json.dump(config, fp, indent=2, separators=(',', ': '))

    def readRemotesCache(self):
        if LeafConstants.REMOTES_CACHE_FILE.exists():
            with open(str(LeafConstants.REMOTES_CACHE_FILE), 'r') as fp:
                return json.load(fp)

    def getInstallFolder(self):
        out = LeafConstants.DEFAULT_LEAF_ROOT
        config = self.readConfiguration()
        if config is not None:
            root = config.get(JsonConstants.CONFIG_ROOT)
            if root is not None:
                out = Path(root)
        out.mkdir(parents=True, exist_ok=True)
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
        return LeafUtils.jsonGet(config, [JsonConstants.CONFIG_ENV], {})

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
            print("Fetch:", remoteurl)
            with urllib.request.urlopen(remoteurl) as url:
                data = json.loads(url.read().decode())
                content[remoteurl] = data
                composites = data.get(JsonConstants.REMOTE_COMPOSITE)
                if composites is not None:
                    for composite in composites:
                        self.fetchUrl(LeafUtils.resolveUrl(
                            remoteurl, composite), content)

    def fetchRemotes(self):
        '''
        Fetch remotes
        '''
        content = OrderedDict()
        for remote in self.remoteList():
            try:
                self.fetchUrl(remote, content)
            except Exception as e:
                print("Error fetching:", remote, ":", e)

        with open(str(LeafConstants.REMOTES_CACHE_FILE), 'w') as output:
            json.dump(content, output)

    def listInstalledPackages(self):
        '''
        Return all installed packages
        '''
        out = {}
        for folder in self.getInstallFolder().iterdir():
            if folder.is_dir() and not LeafUtils.isFolderIgnored(folder):
                manifest = folder / LeafConstants.MANIFEST
                if manifest.is_file():
                    ip = InstalledPackage(manifest)
                    out[ip.getIdentifier()] = ip
        return out

    def install(self, motifList,
                verbose=False,
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
            print("All packages are already installed")
            return True

        # Check dependencies
        missingAptDepends = LeafUtils.getMissingAptDepends(apToInstall)
        if len(missingAptDepends) > 0:
            print("You may have to install missing dependencies by running:")
            print("  $ sudo apt-get install", ' '.join(missingAptDepends))
            if not forceInstall and not downloadOnly:
                raise ValueError("Missing dependencies: " +
                                 ' '.join(missingAptDepends))

        if not skipLicenses:
            lm = LicenseManager()
            for lic in lm.checkLicenses(apToInstall):
                if not lm.acceptLicense(lic):
                    raise ValueError("License must be accepted: " + lic)

        print("Packages to be installed:",
              ', '.join(str(m.getIdentifier()) for m in apToInstall))

        toInstall = OrderedDict()
        # Download package if needed
        for ap in apToInstall:
            toInstall[ap] = LeafArtifact(LeafUtils.download(
                ap.getUrl(), LeafConstants.FILES_CACHE_FOLDER, sha1sum=ap.getSha1sum()))

        if not downloadOnly:
            # Extract package
            for ap, la in toInstall.items():
                self.extractPackage(la,
                                    installedPackages,
                                    ap.getUrl(),
                                    verbose=verbose,
                                    keepFolderOnError=keepFolderOnError)

    def extractPackage(self, leafArtifact, installedPackages=None, urlSource=None, verbose=False, keepFolderOnError=False):
        '''
        Extract & post install given package
        '''
        print("Installing", leafArtifact.getIdentifier())

        if installedPackages is None:
            installedPackages = self.listInstalledPackages()

        targetFolder = self.getInstallFolder() / str(leafArtifact.getIdentifier())
        if targetFolder.is_dir():
            raise ValueError("Folder already exists: " + targetFolder)

        # Create folder
        targetFolder.mkdir(parents=True, exist_ok=False)
        try:
            if leafArtifact.isJsonOnly():
                print("Copy manifest in", targetFolder)
                shutil.copy(str(leafArtifact.path), str(
                    targetFolder / LeafConstants.MANIFEST))
            else:
                print("Extract", leafArtifact.path, "in", targetFolder)
                with TarFile.open(str(leafArtifact.path)) as tf:
                    tf.extractall(str(targetFolder))

            # Execute post install steps
            newPackage = InstalledPackage(
                targetFolder / LeafConstants.MANIFEST)
            if urlSource is not None:
                newPackage.setDetail(
                    JsonConstants.INSTALLED_DETAILS_SOURCE, urlSource)
            stepExec = StepExecutor(
                newPackage, installedPackages, extraEnv=self.getUserEnvVariables())
            stepExec.verbose = verbose
            stepExec.postInstall(newPackage)
            newPackage.setDetail(
                JsonConstants.INSTALLED_DETAILS_DATE, LeafUtils.now())
            installedPackages[newPackage.getIdentifier()] = newPackage
            print("Package", newPackage.getIdentifier(), "has been installed")
            return newPackage
        except Exception as e:
            print("Error during installation:", e)
            if keepFolderOnError:
                targetFolderIgnored = LeafUtils.markFolderAsIgnored(
                    targetFolder)
                print("Mark folder as ignored:", targetFolderIgnored)
            else:
                print("Remove folder:", targetFolder)
                shutil.rmtree(str(targetFolder), True)
            raise e

    def uninstall(self, motifList, verbose=False):
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
            print("No package to remove (to keep dependencies)")
        else:
            print("Packages to be removed:",
                  ', '.join(str(m.getIdentifier()) for m in ipToRemove))
            for ip in ipToRemove:
                stepExec = StepExecutor(
                    ip, installedPackages, extraEnv=self.getUserEnvVariables())
                stepExec.verbose = verbose
                stepExec.preUninstall(ip)
                print("Remove folder:", ip.folder)
                shutil.rmtree(str(ip.folder))
                print("Package removed:", ip.getIdentifier())
                del [installedPackages[ip.getIdentifier()]]

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
                stepExec = StepExecutor(ip, installedPackages)
                for key, value in env.items():
                    value = stepExec.resolve(value, True, False)
                    out[key] = value
        return out


class LeafCli():
    _PROG_NAME = os.path.basename(sys.argv[0])
    _PROG_VERSION = "v%s" % __version__
    _PROG_LICENSE = '''
  Copyright 2017 Sierra Wireless. All rights reserved.

  Licensed under the Mozilla Public License Version 2.0
  https://www.mozilla.org/en-US/MPL/2.0/

  Leaf is part of the Legato Project, http://legato.io/

USAGE
'''
    _ACTION_CONFIG = 'config'
    _ACTION_REMOTE = 'remote'
    _ACTION_LIST = 'list'
    _ACTION_FETCH = 'fetch'
    _ACTION_SEARCH = 'search'
    _ACTION_INSTALL = 'install'
    _ACTION_REMOVE = 'remove'
    _ACTION_ENV = 'env'
    _ACTION_PACK = 'pack'
    _ACTION_INDEX = 'index'
    _ACTION_CLEAN = 'clean'
    _ACTION_ALIASES = {
        _ACTION_LIST: ['ls'],
        _ACTION_REMOVE: ['rm'],
        _ACTION_INSTALL: ['i']
    }

    def __init__(self):
        # Setup argument parser
        self.parser = ArgumentParser(
            description=LeafCli._PROG_LICENSE,
            formatter_class=RawDescriptionHelpFormatter)

        self.parser.add_argument('-V', '--version',
                                 action='version',
                                 version=LeafCli._PROG_VERSION)
        self.parser.add_argument("-v", "--verbose",
                                 dest="verbose",
                                 action="store_true",
                                 help="increase output verbosity")
        self.parser.add_argument("--config",
                                 metavar='CONFIG_FILE',
                                 dest="customConfig",
                                 type=Path,
                                 help="use custom configuration file")

        subparsers = self.parser.add_subparsers(dest='verb',
                                                description='supported commands',
                                                help='actions to execute')

        def newParser(action, verb_help):
            return subparsers.add_parser(action,
                                         help=verb_help,
                                         aliases=LeafCli._ACTION_ALIASES.get(action, []))

        # CONFIG
        subparser = newParser(LeafCli._ACTION_CONFIG, "manage configuration")
        subparser.add_argument('--root',
                               dest='root_folder',
                               metavar='DIR',
                               help="set the root folder, default: " + str(LeafConstants.DEFAULT_LEAF_ROOT))
        subparser.add_argument('--env',
                               dest='config_env',
                               action='append',
                               metavar='KEY=VALUE',
                               help="set custom env variables for exec steps")

        # CLEAN

        subparser = newParser(LeafCli._ACTION_CLEAN, "clean cache folder")

        # REMOTE
        subparser = newParser(LeafCli._ACTION_REMOTE,
                              "manage remote repositories")
        subparser.add_argument('--add',
                               dest='remote_add',
                               action='append',
                               metavar='URL',
                               help='add given remote url')
        subparser.add_argument('--rm',
                               dest='remote_rm',
                               action='append',
                               metavar='URL',
                               help='remove given remote url')

        # FETCH
        subparser = newParser(LeafCli._ACTION_FETCH,
                              "fetch remote repositories packages list")

        # LIST
        subparser = newParser(LeafCli._ACTION_LIST, "list installed packages")
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument("-m", "--module",
                               dest="modules",
                               action="append",
                               metavar="MODULE",
                               help="filter packages supporting given module")
        subparser.add_argument('keywords', nargs=argparse.ZERO_OR_MORE)

        # SEARCH
        subparser = newParser(LeafCli._ACTION_SEARCH,
                              "search for available packages")
        subparser.add_argument("-a", "--all",
                               dest="allPackages",
                               action="store_true",
                               help="display all packages, not only master packages")
        subparser.add_argument("-m", "--module",
                               dest="modules",
                               action="append",
                               metavar="MODULE",
                               help="filter packages supporting given module")
        subparser.add_argument('keywords', nargs=argparse.ZERO_OR_MORE)

        # INSTALL
        subparser = newParser(LeafCli._ACTION_INSTALL,
                              "install packages")
        subparser.add_argument("--skip-licenses",
                               dest="skipLicenses",
                               action="store_true",
                               help="skip license display and accept, assume yes")
        subparser.add_argument('-f', "--force",
                               dest="force",
                               action="store_true",
                               help="force installation in case of warnings")
        subparser.add_argument('-d', "--download-only",
                               dest="downloadOnly",
                               action="store_true",
                               help="only download artifacts in cache, do not install them")
        subparser.add_argument('-k', "--keep",
                               dest="keepOnError",
                               action="store_true",
                               help="keep package folder in case of installation error")
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

        # REMOVE
        subparser = newParser(LeafCli._ACTION_REMOVE,
                              "remove packages")
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

        # ENV
        subparser = newParser(LeafCli._ACTION_ENV,
                              "display environment variables exported by packages")
        subparser.add_argument('packages', nargs=argparse.REMAINDER)

        # PACK
        subparser = newParser(LeafCli._ACTION_PACK,
                              "create a package")
        subparser.add_argument('-o',
                               metavar='FILE',
                               required=True,
                               type=Path,
                               dest='pack_output',
                               help='output file')
        subparser.add_argument('manifest',
                               type=Path,
                               help='the manifest file to package')

        # INDEX
        subparser = newParser(LeafCli._ACTION_INDEX,
                              "build a repository index.json")
        subparser.add_argument('-o',
                               metavar='FILE',
                               required=True,
                               type=Path,
                               dest='index_output',
                               help='output file')
        subparser.add_argument('--name',
                               metavar='NAME',
                               dest='index_name',
                               help='name of the repository')
        subparser.add_argument('--description',
                               metavar='STRING',
                               dest='index_description',
                               help='description of the repository')
        subparser.add_argument('--composite',
                               dest='index_composites',
                               metavar='FILE',
                               action='append',
                               help='reference composite index file')
        subparser.add_argument('artifacts',
                               type=Path,
                               nargs=argparse.REMAINDER,
                               help='leaf artifacts')

    def execute(self, argv=None):
        '''
        Entry point
        '''

        if argv is None:
            argv = sys.argv
        else:
            sys.argv.extend(argv)

        try:
            # Process arguments
            args = self.parser.parse_args()

            configFile = LeafConstants.DEFAULT_CONFIG_FILE
            if args.customConfig is not None:
                configFile = args.customConfig

            app = LeafApp(configFile)

            action = args.verb
            for k, v in LeafCli._ACTION_ALIASES.items():
                if action in v:
                    action = k
                    break
            # DEBUG only, print parsed args
            # print(args)
            if action == LeafCli._ACTION_CONFIG:
                if args.root_folder is not None:
                    app.updateConfiguration(rootFolder=args.root_folder)
                if args.config_env is not None:
                    app.updateConfiguration(env=args.config_env)
                print("Configuration file:", app.configurationFile)
                print(json.dumps(app.readConfiguration(),
                                 sort_keys=True,
                                 indent=2,
                                 separators=(',', ': ')))
            elif action == LeafCli._ACTION_CLEAN:
                print("Clean cache folder: ", LeafConstants.CACHE_FOLDER)
                shutil.rmtree(str(LeafConstants.FILES_CACHE_FOLDER), True)
                if LeafConstants.REMOTES_CACHE_FILE.exists():
                    os.remove(str(LeafConstants.REMOTES_CACHE_FILE))
                shutil.rmtree(str(LeafConstants.FILES_CACHE_FOLDER), True)
            elif action == LeafCli._ACTION_REMOTE:
                if args.remote_add is not None:
                    for url in args.remote_add:
                        app.remoteAdd(url)
                if args.remote_rm is not None:
                    for url in args.remote_rm:
                        app.remoteRemove(url)
                for remote, info in app.remoteList().items():
                    content = OrderedDict()
                    if info is None:
                        content["Status"] = "not fetched yet"
                    else:
                        content["Name"] = info.get(JsonConstants.REMOTE_NAME)
                        content["Description"] = info.get(
                            JsonConstants.REMOTE_DESCRIPTION)
                        content["Last update"] = info.get(
                            JsonConstants.REMOTE_DATE)
                    self.printContent(remote, content)
            elif action == LeafCli._ACTION_FETCH:
                app.fetchRemotes()
            elif action == LeafCli._ACTION_LIST:
                for pack in self.filterPackageList(app.listInstalledPackages().values(), keywords=args.keywords, modules=args.modules):
                    if args.allPackages or pack.isMaster():
                        self.displayPackage(pack, args.verbose)
            elif action == LeafCli._ACTION_SEARCH:
                for pack in self.filterPackageList(app.listAvailablePackages().values(), args.keywords, args.modules):
                    if args.allPackages or pack.isMaster():
                        self.displayPackage(pack, args.verbose)
            elif action == LeafCli._ACTION_INSTALL:
                app.install(args.packages,
                            downloadOnly=args.downloadOnly,
                            forceInstall=args.force,
                            verbose=args.verbose,
                            keepFolderOnError=args.keepOnError,
                            skipLicenses=args.skipLicenses)
            elif action == LeafCli._ACTION_REMOVE:
                app.uninstall(args.packages,
                              verbose=args.verbose)
            elif action == LeafCli._ACTION_ENV:
                for k, v in app.getEnv(args.packages).items():
                    print('export %s="%s"' % (k, v))
            elif action == LeafCli._ACTION_PACK:
                app.pack(args.manifest, args.pack_output)
            elif action == LeafCli._ACTION_INDEX:
                app.index(args.index_output,
                          args.artifacts,
                          args.index_name,
                          args.index_description,
                          args.index_composites)

            return 0
        except KeyboardInterrupt:
            ### handle keyboard interrupt ###
            return 0
        except Exception as e:
            if args.verbose:
                raise e
            print(e, file=sys.stderr)
            return 2

    def filterPackageList(self, content, keywords=None, modules=None, sort=True):
        '''
        Filter a list of packages given optional criteria
        '''
        out = list(content)

        def my_filter(p):
            out = True
            if modules is not None and len(modules) > 0 and p.getSupportedModules() is not None:
                out = False
                for m in modules:
                    if m.lower() in map(str.lower, p.getSupportedModules()):
                        out = True
                        break
            if out and keywords is not None and len(keywords) > 0:
                out = False
                for k in keywords:
                    k = k.lower()
                    if k in str(p.getIdentifier()).lower() or (p.getDescription() is not None and k in p.getDescription().lower()):
                        out = True
                        break
            return out
        out = filter(my_filter, out)
        if sort:
            out = sorted(out, key=Manifest.getIdentifier)
        return out

    def displayPackage(self, pack, verbose):
        '''
        Display information of an installed/available package
        '''
        content = OrderedDict()
        content["Description"] = pack.getDescription()
        if isinstance(pack, AvailablePackage):
            content["Size"] = (pack.getSize(), 'bytes')
            content["Source:"] = pack.getUrl()
        elif isinstance(pack, InstalledPackage):
            content["Folder"] = pack.folder
            content["Installation date"] = pack.getDetail(
                JsonConstants.INSTALLED_DETAILS_DATE)
        content["Depends"] = pack.getLeafDepends()
        content["Modules"] = pack.getSupportedModules()
        content["Licenses"] = pack.getLicenses()
        self.printContent(pack.getIdentifier(), content, verbose=verbose)

    def printContent(self, firstLine, content, indent=4, separator=':', ralign=False, verbose=True):
        '''
        Display formatted content 
        '''
        if firstLine is not None:
            print(firstLine)
        if verbose and content is not None:
            maxlen = 0
            if ralign:
                maxlen = len(
                    max(filter(lambda k: content.get(k) is not None, content), key=len))
            for k, v in content.items():
                if isinstance(v, dict) or isinstance(v, list):
                    if len(v) > 0:
                        print(" " * indent,
                              k.rjust(maxlen),
                              separator,
                              str(v[0]))
                        for o in v[1:]:
                            print(" " * indent,
                                  (' ' * len(k)).rjust(maxlen),
                                  ' ' * len(separator),
                                  str(o))
                elif isinstance(v, tuple):
                    if len(v) > 0 and v[0] is not None:
                        print(" " * indent,
                              k.rjust(maxlen),
                              separator,
                              ' '.join(map(str, v)))
                elif v is not None:
                    print(" " * indent,
                          k.rjust(maxlen),
                          separator,
                          str(v))


if __name__ == "__main__":
    # Check python version
    currentPythonVersion = sys.version_info
    if (currentPythonVersion[0], currentPythonVersion[1]) < LeafConstants.MIN_PYTHON_VERSION:
        print('Unsuported Python version, please use at least Python %d.%d.' % LeafConstants.MIN_PYTHON_VERSION,
              file=sys.stderr)
        sys.exit(1)
    sys.exit(LeafCli().execute())
