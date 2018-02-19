'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/

'''
import apt
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import argparse
from collections import OrderedDict
import datetime
from functools import total_ordering
import hashlib
import io
import json
from leaf import __version__
import os
from pathlib import Path
import platform
import random
import re
import requests
import shutil
import string
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
    MIN_PYTHON_VERSION = (3, 4)
    USER_HOME = Path(os.path.expanduser("~"))
    DEFAULT_LEAF_ROOT = USER_HOME / 'legato' / 'packages'
    DEFAULT_CONFIG_FILE = USER_HOME / '.leaf-config.json'
    CACHE_FOLDER = USER_HOME / '.cache' / 'leaf'
    FILES_CACHE_FOLDER = CACHE_FOLDER / "files"
    REMOTES_CACHE_FILE = CACHE_FOLDER / 'remotes.json'
    LICENSES_CACHE_FILE = CACHE_FOLDER / 'licenses.json'
    MANIFEST = 'manifest.json'
    VAR_PREFIX = '@'
    DOWNLOAD_TIMEOUT = 5


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
    STEP_LABEL = 'label'
    STEP_IGNORE_FAIL = 'ignoreFail'
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
    ENV = 'env'

    # Extra
    INFO_SUPPORTEDMODULES = 'supportedModules'
    INFO_SUPPORTEDOS = 'supportedOs'


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
    _ARCHS = {'x86_64': '64', 'i386': '32'}
    _CURRENTOS = platform.system().lower() + _ARCHS.get(platform.machine(), "")
    _IGNORED_PATTERN = re.compile('^.*_ignored[0-9]*$')
    _LEAF_EXT = {'.tar': '',
                 '.xz': 'xz',
                 '.bz2': 'bz2',
                 '.tgz': 'gz',
                 '.gz': 'gz'}

    @staticmethod
    def tuplesLt(a, b):
        if a == b:
            return False
        i = 0
        while True:
            if i >= len(a):
                return True
            if i >= len(b):
                return False
            ai = a[i]
            bi = b[i]
            if not type(ai) == type(bi):
                ai = str(ai)
                bi = str(bi)
            if not ai == bi:
                return ai < bi
            i += 1

    @staticmethod
    def getArtifactName(ap):
        prefixLen = 7
        prefix = ap.getSha1sum()
        if prefix is not None and len(prefix) >= prefixLen:
            prefix = prefix[:prefixLen]
        else:
            prefix = ''.join(random.choice(string.ascii_uppercase + string.digits)
                             for _ in range(prefixLen))
        return "%s-%s" % (prefix,
                          Path(urlparse(ap.getUrl()).path).name)

    @staticmethod
    def askYesNo(logger, message, default=None):
        label = " (yes/no)"
        if default == True:
            label = " (YES/no)"
        elif default == False:
            label = " (yes/NO)"
        while True:
            logger.printMessage(message + label + " ")
            answer = input().strip()
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
        suffix = LeafUtils._LEAF_EXT.get(path.suffix, 'xz')
        if len(suffix) > 0:
            return prefix + ":" + suffix
        return prefix

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
            for deb in LeafUtils.jsonGet(ap.getNodeInfo(),
                                         [JsonConstants.INFO_DEPENDS,
                                             JsonConstants.INFO_DEPENDS_DEB],
                                         []):
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
    def download(url, folder, logger, filename=None, sha1sum=None):
        '''
        Download an artifact
        '''
        parsedUrl = urlparse(url)
        if filename is None:
            filename = Path(parsedUrl.path).name
        targetFile = folder / filename
        if targetFile.exists():
            if sha1sum is None:
                logger.printDetail("File exists but cannot be verified,",
                                   targetFile.name, " will be re-downloaded")
                os.remove(str(targetFile))
            elif sha1sum != LeafUtils.sha1sum(targetFile):
                logger.printDetail("File exists but SHA1 differs,",
                                   targetFile.name, " will be re-downloaded")
                os.remove(str(targetFile))
            else:
                logger.printDetail(
                    "File already in cache:", targetFile.name)
        if not targetFile.exists():
            if parsedUrl.scheme.startswith("http"):
                req = requests.get(
                    url, stream=True, timeout=LeafConstants.DOWNLOAD_TIMEOUT)
                size = int(req.headers.get('content-length', -1))
                logger.progressStart('download', total=size)
                currentSize = 0
                with open(str(targetFile), 'wb') as fp:
                    for data in req.iter_content(1024 * 1024):
                        currentSize += len(data)
                        logger.progressWorked('download',
                                              "Downloading " + targetFile.name,
                                              worked=currentSize,
                                              total=size,
                                              sameLine=True)
                        fp.write(data)
            else:
                logger.progressStart('download')
                urllib.request.urlretrieve(url, str(targetFile))
            logger.progressDone(
                'download', "File downloaded: " + str(targetFile))
            if sha1sum is not None and sha1sum != LeafUtils.sha1sum(targetFile):
                raise ValueError(
                    "Invalid SHA1 sum for " + targetFile.name + ", expecting " + sha1sum)
        return targetFile


@total_ordering
class PackageIdentifier ():

    _NAME_REGEX = re.compile('^[a-zA-Z0-9][-a-zA-Z0-9]*$')
    _VERSION_REGEX = re.compile('^[a-zA-Z0-9][-._a-zA-Z0-9]*$')
    _VERSION_SEPARATOR = re.compile("[-_.]")
    _SEPARATOR = '_'

    @staticmethod
    def isValidIdentifier(pis):
        split = pis.partition(PackageIdentifier._SEPARATOR)
        return (PackageIdentifier._NAME_REGEX.match(split[0]) is not None and
                PackageIdentifier._VERSION_REGEX.match(split[2]) is not None)

    @staticmethod
    def fromString(pis):
        split = pis.partition(PackageIdentifier._SEPARATOR)
        return PackageIdentifier(split[0], split[2])

    def __init__(self, name, version):
        if PackageIdentifier._NAME_REGEX.match(name) is None:
            raise ValueError("Invalid package name: " + name)
        if PackageIdentifier._VERSION_REGEX.match(version) is None:
            raise ValueError("Invalid package version: " + version)
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
            va = self.getVersion()
            vb = other.getVersion()
            if va == vb:
                return self.version < other.version
            return LeafUtils.tuplesLt(va, vb)
        return self.name < other.name

    def getVersion(self):
        def tryint(x):
            try:
                return int(x)
            except:
                return x
        return tuple(tryint(x) for x in PackageIdentifier._VERSION_SEPARATOR.split(self.version))


class Manifest():
    '''
    Represent a Manifest model object
    '''

    @staticmethod
    def parse(manifestFile):
        with open(str(manifestFile), 'r') as fp:
            return Manifest(json.load(fp))

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

    def getSupportedOS(self):
        return self.getNodeInfo().get(JsonConstants.INFO_SUPPORTEDOS)

    def isSupported(self):
        supportedOs = self.getSupportedOS()
        return supportedOs is None or len(supportedOs) == 0 or LeafUtils._CURRENTOS in supportedOs


class LeafArtifact(Manifest):
    '''
    Represent a tar/xz or a single manifest.json file
    '''

    def __init__(self, path):
        self.path = path
        with TarFile.open(str(self.path), 'r') as tarfile:
            Manifest.__init__(self, json.load(io.TextIOWrapper(
                tarfile.extractfile(LeafConstants.MANIFEST))))


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


class LicenseManager ():
    '''
    Handle license acceptation
    '''

    def __init__(self, logger):
        self.logger = logger

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
        self.logger.printMessage("You need to accept the license:", lic)
        if LeafUtils.askYesNo(self.logger,
                              "Do you want to display the license text?",
                              default=False):
            with urllib.request.urlopen(lic) as req:
                text = io.TextIOWrapper(req).read()
                self.logger.printMessage(text)
        out = LeafUtils.askYesNo(self.logger,
                                 "Do you accept the license?",
                                 default=True)
        if out:
            licenses = self.readLicenses()
            licenses[lic] = LeafUtils.now()
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
        steps = LeafUtils.jsonGet(self.package.json, [
                                  JsonConstants.INSTALL], [])
        if len(steps) > 0:
            self.runSteps(steps, self.package, label="Post-install")

    def preUninstall(self):
        steps = LeafUtils.jsonGet(self.package.json, [
                                  JsonConstants.UNINSTALL], [])
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
        for k, v in LeafUtils.jsonGet(step, [JsonConstants.STEP_EXEC_ENV], {}).items():
            v = self.resolve(v)
            env[k] = v
        if self.extraEnv is not None:
            for k, v in self.extraEnv.items():
                v = self.resolve(v)
                env[k] = v
        env["LEAF_VERSION"] = str(__version__)
        stdout = subprocess.DEVNULL
        if self.logger.isVerbose() or LeafUtils.jsonGet(step,
                                                        [JsonConstants.STEP_EXEC_VERBOSE],
                                                        default=False):
            stdout = None
        rc = subprocess.call(command,
                             cwd=str(self.targetFolder),
                             env=env,
                             stdout=stdout,
                             stderr=subprocess.STDOUT)
        if rc != 0:
            if LeafUtils.jsonGet(step,
                                 [JsonConstants.STEP_IGNORE_FAIL],
                                 False):
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
            LeafUtils.download(step[JsonConstants.STEP_DOWNLOAD_URL],
                               self.targetFolder,
                               self.logger,
                               step.get(JsonConstants.STEP_DOWNLOAD_FILENAME),
                               step.get(JsonConstants.STEP_DOWNLOAD_SHA1SUM))
        except Exception as e:
            if LeafUtils.jsonGet(step, [JsonConstants.STEP_IGNORE_FAIL], False):
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
            with TarFile.open(str(outputFile),
                              LeafUtils.guessCompression(outputFile, prefix="w")) as tf:
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
            self.logger.printMessage("Found:", la.getIdentifier())
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
            self.logger.printMessage("Index created:", outputFile)


class LeafApp(LeafRepository):
    '''
    Main API for using Leaf
    '''

    def __init__(self, logger, configurationFile):
        '''
        Constructor
        '''
        super().__init__(logger)
        self.configurationFile = configurationFile
        # Create folders if needed
        os.makedirs(str(LeafConstants.FILES_CACHE_FOLDER), exist_ok=True)

    def readConfiguration(self):
        '''
        Read the configuration if it exists, else return the the default configuration
        '''
        if self.configurationFile.exists():
            with open(str(self.configurationFile), 'r') as fp:
                return json.load(fp)
        # Default configuration here
        out = dict()
        out[JsonConstants.CONFIG_ROOT] = str(LeafConstants.DEFAULT_LEAF_ROOT)
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
            if LeafConstants.REMOTES_CACHE_FILE.exists():
                os.remove(str(LeafConstants.REMOTES_CACHE_FILE))
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
                if LeafConstants.REMOTES_CACHE_FILE.exists():
                    os.remove(str(LeafConstants.REMOTES_CACHE_FILE))
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
                            self.fetchUrl(LeafUtils.resolveUrl(
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
        with open(str(LeafConstants.REMOTES_CACHE_FILE), 'w') as output:
            json.dump(content, output)
        self.logger.progressDone('fetch',
                                 message="Fetched %d remote repositories" % (len(remotes)))

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
            toInstall[ap] = LeafArtifact(LeafUtils.download(
                ap.getUrl(),
                LeafConstants.FILES_CACHE_FOLDER,
                self.logger,
                filename=LeafUtils.getArtifactName(ap),
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
                targetFolderIgnored = LeafUtils.markFolderAsIgnored(
                    targetFolder)
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


class LeafCli():
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

        self.parser.add_argument("--json",
                                 dest="json",
                                 action="store_true",
                                 help="output json format")
        self.parser.add_argument('-V', '--version',
                                 action='version',
                                 version="v%s" % __version__)
        self.parser.add_argument("--config",
                                 metavar='CONFIG_FILE',
                                 dest="customConfig",
                                 type=Path,
                                 help="use custom configuration file")

        subparsers = self.parser.add_subparsers(dest='command',
                                                description='supported commands',
                                                metavar="COMMAND",
                                                help='actions to execute')
        subparsers.required = True

        def newParser(action, command_help):
            out = subparsers.add_parser(action,
                                        help=command_help,
                                        aliases=LeafCli._ACTION_ALIASES.get(action, []))
            out.add_argument("-v", "--verbose",
                             dest="verbose",
                             action='count',
                             help="increase output verbosity")
            return out

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
            logger = VerboseLogger() if args.verbose else QuietLogger()
            if args.json:
                logger = JsonLogger()

            configFile = LeafConstants.DEFAULT_CONFIG_FILE
            if args.customConfig is not None:
                configFile = args.customConfig

            app = LeafApp(logger, configFile)

            action = args.command
            for k, v in LeafCli._ACTION_ALIASES.items():
                if action in v:
                    action = k
                    break
            if action == LeafCli._ACTION_CONFIG:
                if args.root_folder is not None:
                    app.updateConfiguration(rootFolder=args.root_folder)
                if args.config_env is not None:
                    app.updateConfiguration(env=args.config_env)
                logger.printMessage("Configuration file:",
                                    app.configurationFile)
                logger.printMessage(json.dumps(app.readConfiguration(),
                                               sort_keys=True,
                                               indent=2,
                                               separators=(',', ': ')))
            elif action == LeafCli._ACTION_CLEAN:
                logger.printMessage(
                    "Clean cache folder: ", LeafConstants.CACHE_FOLDER)
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
                for url, info in app.remoteList().items():
                    logger.displayRemote(url, info)
            elif action == LeafCli._ACTION_FETCH:
                app.fetchRemotes()
            elif action == LeafCli._ACTION_LIST:
                for pack in self.filterPackageList(app.listInstalledPackages().values(), keywords=args.keywords, modules=args.modules):
                    if args.allPackages or pack.isMaster():
                        logger.displayPackage(pack)
            elif action == LeafCli._ACTION_SEARCH:
                for pack in self.filterPackageList(app.listAvailablePackages().values(), args.keywords, args.modules):
                    if args.allPackages or (pack.isMaster() and pack.isSupported()):
                        logger.displayPackage(pack)
            elif action == LeafCli._ACTION_INSTALL:
                app.install(args.packages,
                            downloadOnly=args.downloadOnly,
                            forceInstall=args.force,
                            keepFolderOnError=args.keepOnError,
                            skipLicenses=args.skipLicenses)
            elif action == LeafCli._ACTION_REMOVE:
                app.uninstall(args.packages)
            elif action == LeafCli._ACTION_ENV:
                for k, v in app.getEnv(args.packages).items():
                    logger.printMessage('export %s="%s"' % (k, v))
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
            return 1
        except Exception as e:
            if args.verbose:
                raise e
            logger.printError(e, exception=e)
            return 2

    def filterPackageList(self, content, keywords=None, modules=None, sort=True):
        '''
        Filter a list of packages given optional criteria
        '''
        out = list(content)

        def my_filter(p):
            out = True
            if modules is not None and len(modules) > 0:
                out = False
                if p.getSupportedModules() is not None:
                    for m in modules:
                        if m.lower() in map(str.lower, p.getSupportedModules()):
                            out = True
                            break
            if out and keywords is not None and len(keywords) > 0:
                out = False
                for k in keywords:
                    k = k.lower()
                    if k in str(p.getIdentifier()).lower():
                        out = True
                        break
                    if p.getDescription() is not None and k in p.getDescription().lower():
                        out = True
                        break
            return out
        out = filter(my_filter, out)
        if sort:
            out = sorted(out, key=Manifest.getIdentifier)
        return out
