'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import hashlib
import json
import os
import random
import re
import string
import sys
import tempfile
import time
import urllib
from collections import OrderedDict
from pathlib import Path
from tarfile import TarFile
from urllib.parse import urlparse, urlunparse

import requests

from leaf import __version__
from leaf.constants import LeafConstants

_IGNORED_PATTERN = re.compile('^.*_ignored[0-9]*$')
_VERSION_SEPARATOR = re.compile("[-_.~]")


def checkSupportedLeaf(minVersion, currentVersion=__version__, exceptionMessage=None):
    # Handle dev version
    if minVersion is not None:
        if versionComparator_lt(currentVersion, minVersion):
            if exceptionMessage is not None:
                raise ValueError(exceptionMessage)
            return False
    return True


def stringToTuple(version):
    def tryint(x):
        try:
            return int(x)
        except Exception:
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


def getCachedArtifactName(filename, hash):
    '''
    Compute a unique name for files in cache
    '''
    prefixLen = 7
    if hash is not None:
        prefix = parseHash(hash)[1][:prefixLen]
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


def downloadData(url, outputFile=None, timeout=LeafConstants.DOWNLOAD_TIMEOUT):
    '''
    Download data and write it to outputFile
    or return the data if outputFile is None
    '''
    with urllib.request.urlopen(url, timeout=timeout) as stream:
        if outputFile is None:
            return stream.read()
        with open(str(outputFile), 'wb') as fp:
            fp.write(stream.read())


def downloadFile(url, folder, logger, filename=None, hash=None):
    '''
    Download an artifact and check its hash if given
    '''
    parsedUrl = urlparse(url)
    if filename is None:
        filename = Path(parsedUrl.path).name
    if not folder.exists():
        folder.mkdir(parents=True)
    targetFile = folder / filename
    if targetFile.exists():
        if hash is None:
            logger.printVerbose("File exists but cannot be verified, %s will be re-downloaded" %
                                targetFile.name)
            os.remove(str(targetFile))
        elif not checkHash(targetFile, hash):
            logger.printVerbose("File exists but hash differs, %s will be re-downloaded" %
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
            currentSize = 0
            with open(str(targetFile), 'wb') as fp:
                for data in req.iter_content(1024 * 1024):
                    currentSize += len(data)
                    logger.progressWorked("Downloading %s" % targetFile.name,
                                          worked=currentSize,
                                          total=size,
                                          sameLine=True)
                    fp.write(data)
        else:
            urllib.request.urlretrieve(url, str(targetFile))
        logger.printDefault("[100%%] Downloading %s" % targetFile.name)
        if hash is not None and not checkHash(targetFile, hash):
            raise ValueError("Invalid hash for %s (expecting %s)" %
                             (targetFile.name, hash))
    return targetFile


def envListToMap(envList):
    out = OrderedDict()
    if envList is not None:
        for line in envList:
            if '=' in line:
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip()
            else:
                out[line] = ""
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


def mkTmpLeafRootDir():
    return Path(tempfile.mkdtemp(prefix="leaf-alt-root_"))


def getAltEnvPath(envKey=None, defaultPath=None, mkdirIfNeeded=False):
    '''
    Returns 'defaultPath' unless 'envKey' exists in env, then returns 'envKey'
    as a Path
    '''
    out = defaultPath
    if envKey is not None and envKey in os.environ:
        out = Path(os.environ[envKey])
    if defaultPath is None:
        raise ValueError("Unknown path")
    if mkdirIfNeeded and not out.is_dir():
        out.mkdir(parents=True)
    return out


__HASH_NAME = 'sha384'
__HASH_FACTORY = hashlib.sha384
__HASH_BLOCKSIZE = 4096


def parseHash(hash):
    parts = hash.split(':')
    if len(parts) != 2:
        raise ValueError("Invalid hash format %s" % hash)
    if parts[0] != __HASH_NAME:
        raise ValueError(
            "Unsupported hash method, expecting %s" % __HASH_NAME)
    return parts


def computeHash(file):
    '''
    Return the hash of the given file
    '''
    hasher = __HASH_FACTORY()
    with open(str(file), 'rb') as fp:
        buf = fp.read(__HASH_BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fp.read(__HASH_BLOCKSIZE)
    return __HASH_NAME + ':' + hasher.hexdigest()


def checkHash(file, value):
    parseHash(value)
    return computeHash(file) == value


def getTotalSize(item):
    '''
    Get the size of a file or a folder (reccursive)
    '''
    if not item.exists():
        return -1
    if not item.is_dir():
        return item.stat().st_size
    out = 0
    for sub in item.iterdir():
        out += getTotalSize(sub)
    return out
