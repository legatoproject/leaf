'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import apt
from collections import OrderedDict
import hashlib
import json
from leaf import __version__
from leaf.constants import LeafConstants, LeafFiles
import os
from pathlib import Path
import random
import re
import requests
import string
import sys
from tarfile import TarFile
import time
import urllib
from urllib.parse import urlparse, urlunparse


_IGNORED_PATTERN = re.compile('^.*_ignored[0-9]*$')
_VERSION_SEPARATOR = re.compile("[-_.~]")


def checkSupportedLeaf(minVersion, currentVersion=__version__, exceptionMessage=None):
    # Handle dev version
    if minVersion is not None and not currentVersion == '0.0.0':
        if versionComparator_lt(currentVersion, minVersion):
            if exceptionMessage is not None:
                raise ValueError(exceptionMessage)
            return False
    return True


def stringToTuple(version):
    def tryint(x):
        try:
            return int(x)
        except:
            return x
    return tuple(tryint(x) for x in _VERSION_SEPARATOR.split(version))


def versionComparator_lt(versionA, versionB):
    if versionA == versionB:
        return False
    if not isinstance(versionA, tuple):
        versionA = stringToTuple(str(versionA))
    if not isinstance(versionB, tuple):
        versionB = stringToTuple(str(versionB))
    i = 0
    while True:
        if i >= len(versionA):
            return True
        if i >= len(versionB):
            return False
        a = versionA[i]
        b = versionB[i]
        if not type(a) == type(b):
            a = str(a)
            b = str(b)
        if not a == b:
            return a < b
        i += 1


def checkPythonVersion():
    # Check python version
    currentPythonVersion = sys.version_info
    if (currentPythonVersion[0], currentPythonVersion[1]) < LeafConstants.MIN_PYTHON_VERSION:
        print(
            'Unsupported Python version, please use at least Python %d.%d.' % LeafConstants.MIN_PYTHON_VERSION,
            file=sys.stderr)
        sys.exit(1)


def resolveUrl(remoteUrl, subPath):
    '''
    Resolves a relative URL
    '''
    url = urlparse(remoteUrl)
    newPath = Path(url.path).parent / subPath
    url = url._replace(path=str(newPath))
    return urlunparse(url)


def getCachedArtifactName(filename, sha1sum):
    '''
    Compute a unique name for files in cache
    '''
    prefixLen = 7
    if sha1sum is not None and len(sha1sum) >= prefixLen:
        prefix = sha1sum[:prefixLen]
    else:
        prefix = ''.join(random.choice(string.ascii_uppercase + string.digits)
                         for _ in range(prefixLen))
    return "%s-%s" % (prefix, filename)


def isFolderIgnored(folder):
    '''
    Checks if a package folder should be ignored
    '''
    return _IGNORED_PATTERN.match(folder.name) is not None


def markFolderAsIgnored(folder):
    '''
    Marks the given folder as ignored
    '''
    oldname = folder.name
    newname = oldname + "_ignored" + str(int(time.time()))
    if _IGNORED_PATTERN.match(newname) is None:
        raise ValueError('Invalid ignored folder name: ' + newname)
    out = folder.parent / newname
    folder.rename(out)
    return out


def openOutputTarFile(path):
    '''
    Opens a tar file with the correct compression given its extension
    '''
    suffix = LeafConstants.LEAF_COMPRESSION.get(path.suffix, 'xz')
    mode = "w"
    if len(suffix) > 0:
        mode += ":" + suffix
    return TarFile.open(str(path), mode)


def computeSha1sum(file):
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


def downloadFile(url, folder, logger, filename=None, sha1sum=None):
    '''
    Download an artifact and eventually check its sha1
    '''
    parsedUrl = urlparse(url)
    if filename is None:
        filename = Path(parsedUrl.path).name
    targetFile = folder / filename
    if targetFile.exists():
        if sha1sum is None:
            logger.printVerbose("File exists but cannot be verified, %s will be re-downloaded" %
                                targetFile.name)
            os.remove(str(targetFile))
        elif sha1sum != computeSha1sum(targetFile):
            logger.printVerbose("File exists but SHA1 differs, %s will be re-downloaded" %
                                targetFile.name)
            os.remove(str(targetFile))
        else:
            logger.printVerbose("File %s is already in cache" %
                                targetFile.name)
    if not targetFile.exists():
        if parsedUrl.scheme.startswith("http"):
            req = requests.get(url,
                               stream=True,
                               timeout=LeafConstants.DOWNLOAD_TIMEOUT)
            size = int(req.headers.get('content-length', -1))
            logger.progressStart('Download file', total=size)
            currentSize = 0
            with open(str(targetFile), 'wb') as fp:
                for data in req.iter_content(1024 * 1024):
                    currentSize += len(data)
                    logger.progressWorked('Download file',
                                          "Downloading %s" % targetFile.name,
                                          worked=currentSize,
                                          total=size,
                                          sameLine=True)
                    fp.write(data)
        else:
            logger.progressStart('Download file')
            urllib.request.urlretrieve(url, str(targetFile))
        logger.progressDone('Download file',
                            "[100%%] Downloading %s" % targetFile.name)
        if sha1sum is not None and sha1sum != computeSha1sum(targetFile):
            raise ValueError("Invalid SHA1 sum for %s, expecting %s" %
                             (targetFile.name, sha1sum))
    return targetFile


def envListToMap(envList):
    out = OrderedDict()
    if envList is not None:
        for line in envList:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def jsonWriteFile(file, data, pp=False):
    kw = {}
    if pp:
        kw.update({'indent': 4,
                   'separators': (',', ': ')})
    with open(str(file), 'w') as fp:
        json.dump(data, fp, **kw)


def jsonLoadFile(file):
    with open(str(file), 'r') as fp:
        return jsonLoad(fp)


def jsonLoad(fp):
    return json.load(fp, object_pairs_hook=OrderedDict)


def isWorkspaceRoot(folder):
    return (folder / LeafFiles.WS_CONFIG_FILENAME).exists()


def findWorkspaceRoot():
    currentFolder = Path(os.getcwd())
    if isWorkspaceRoot(currentFolder):
        return currentFolder
    for parent in currentFolder.parents:
        if isWorkspaceRoot(parent):
            return parent
    raise ValueError("Cannot find workspace root from %s" % os.getcwd())


def genEnvScript(envKvList, activateFile=None, deactivateFile=None):
    if deactivateFile is not None:
        resetMap = OrderedDict()
        for k, _ in envKvList:
            resetMap[k] = os.environ.get(k)
        with open(str(deactivateFile), "w") as fp:
            for k, v in resetMap.items():
                if v is None:
                    fp.write("unset %s;\n" % k)
                else:
                    fp.write("export %s=\"%s\";\n" % (k, v))
    if activateFile is not None:
        with open(str(activateFile), "w") as fp:
            for k, v in envKvList:
                fp.write("export %s=\"%s\";\n" % (k, v))


class AptHelper():
    '''
    Util class to check if apt packages are available/installed
    '''

    def __init__(self):
        self.cache = apt.Cache()

    def isInstallable(self, pack):
        return self.cache.is_virtual_package(pack) or pack in self.cache

    def isInstalled(self, pack):
        if self.cache.is_virtual_package(pack):
            return len([p for p in self.cache.get_providing_packages(pack) if self.cache[p].installed]) > 0
        if pack in self.cache:
            return self.cache[pack].installed is not None
        return False