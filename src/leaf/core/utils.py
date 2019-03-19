"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import hashlib
import os
import random
import re
import shutil
import string
import sys
import tempfile
import time
import urllib
from collections import OrderedDict
from pathlib import Path
from shutil import copyfile
from time import sleep
from urllib.parse import urlparse, urlunparse
from urllib.request import urlretrieve

import requests

from leaf import __version__
from leaf.core.constants import LeafConstants, LeafSettings
from leaf.core.error import InvalidHashException, LeafException, LeafOutOfDateException
from leaf.core.logger import TextLogger, print_trace

_IGNORED_PATTERN = re.compile("^.*_ignored[0-9]*$")
_VERSION_SEPARATOR = re.compile("[-_.~]")


def check_leaf_min_version(minversion, currentversion=__version__, exception_message=None):
    # Handle dev version
    if minversion is not None:
        if version_comparator_lt(currentversion, minversion):
            if exception_message is not None:
                raise LeafOutOfDateException(exception_message)
            return False
    return True


def version_string_to_tuple(version):
    def tryint(x):
        try:
            return int(x)
        except Exception:
            return x

    return tuple(tryint(x) for x in _VERSION_SEPARATOR.split(version))


def version_comparator_lt(a: str, b: str):
    if a == b:
        return False
    if not isinstance(a, str) or not isinstance(b, str):
        raise ValueError()
    a = version_string_to_tuple(a)
    b = version_string_to_tuple(b)
    i = 0
    while True:
        if i >= len(a):
            return True
        if i >= len(b):
            return False
        itema = a[i]
        itemb = b[i]
        if not type(itema) == type(itemb):
            itema = str(itema)
            itemb = str(itemb)
        if not itema == itemb:
            return itema < itemb
        i += 1


def check_supported_python_version():
    # Check python version
    if sys.version_info < LeafConstants.MIN_PYTHON_VERSION:
        print(
            "Unsupported Python version, please use at least Python {version}.".format(version=".".join(map(str, LeafConstants.MIN_PYTHON_VERSION))),
            file=sys.stderr,
        )
        sys.exit(1)


def url_resolve(url: str, subpath: str):
    """
    Resolves a relative URL
    """
    url = urlparse(url)
    newpath = Path(url.path).parent / subpath
    url = url._replace(path=str(newpath))
    return urlunparse(url)


def get_cached_artifact_name(filename: str, hashstr: str):
    """
    Compute a unique name for files in cache
    """
    length = 7
    if hashstr is not None:
        prefix = hash_parse(hashstr)[1][:length]
    else:
        prefix = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))
    return prefix + "-" + filename


def is_folder_ignored(folder: Path):
    """
    Checks if a package folder should be ignored
    """
    return _IGNORED_PATTERN.match(folder.name) is not None


def mark_folder_as_ignored(folder: Path):
    """
    Marks the given folder as ignored
    """
    oldname = folder.name
    newname = oldname + "_ignored" + str(int(time.time()))
    if _IGNORED_PATTERN.match(newname) is None:
        raise ValueError("Invalid ignored folder name: " + newname)
    out = folder.parent / newname
    folder.rename(out)
    return out


def download_data(url, outputfile=None):
    """
    Download data and write it to outputFile
    or return the data if outputFile is None
    """
    parsedurl = urlparse(url)
    if parsedurl.scheme == "":
        with open(parsedurl.path, "rb") as fp:
            if outputfile is None:
                return fp.read()
            with outputfile.open("wb") as fp:
                fp.write(fp.read())
    else:
        with urllib.request.urlopen(url, timeout=LeafSettings.DOWNLOAD_TIMEOUT.as_int()) as stream:
            if outputfile is None:
                return stream.read()
            with outputfile.open("wb") as fp:
                fp.write(stream.read())


def download_file_with_resume(url: str, output: Path, logger: TextLogger, message: str, timeout: int = None, resume: bool = None, buffer_size: int = 262144):
    # Handle default values
    if timeout is None:
        timeout = LeafSettings.DOWNLOAD_TIMEOUT.as_int()
    if resume is None:
        resume = LeafSettings.DOWNLOAD_RESUME.as_boolean()

    headers = {}
    size_current = 0
    open_mode = "wb"

    if resume and output.exists():
        size_current = output.stat().st_size
        headers = {"Range": "bytes={0}-".format(size_current)}
        open_mode = "ab"

    with output.open(open_mode) as fp:
        req = requests.get(url, stream=True, headers=headers, timeout=timeout)
        # Get total size on first request
        size_total = int(req.headers.get("content-length", -1)) + size_current

        # Read remote data and write to output file
        for data in req.iter_content(buffer_size):
            size_current += fp.write(data)
            display_progress(logger, message, size_current, size_total)

        # Rare case when no exception raised and download is not finished
        if 0 < size_current < size_total:
            raise ValueError("Incomplete download")

        return size_current


def download_file_with_retry(url: str, output: Path, logger: TextLogger, message: str, retry: int = None, **kwargs):
    # Handle default values
    if retry is None:
        retry = LeafSettings.DOWNLOAD_RETRY.as_int()

    iteration = 0
    while True:
        try:
            return download_file_with_resume(url, output, logger, message, **kwargs)
        except (ValueError, requests.RequestException, requests.ConnectionError, requests.HTTPError, requests.Timeout) as e:
            iteration += 1
            # Check retry
            if iteration > retry:
                raise e
            # Log the retry attempt
            logger.print_default("\nError while downloading, retry {0}/{1}".format(iteration, retry))
            print_trace()
            # Prevent imediate retry
            sleep(1)


def download_and_check_file(url: str, folder: Path, logger: TextLogger, filename: str = None, hashstr: str = None):
    """
    Download an artifact and check its hash if given
    """
    parsedurl = urlparse(url)
    if filename is None:
        filename = Path(parsedurl.path).name
    if not folder.exists():
        folder.mkdir(parents=True)
    targetfile = folder / filename
    if targetfile.exists():
        if hashstr is None:
            logger.print_verbose("File exists but cannot be verified, {file.name} will be re-downloaded".format(file=targetfile))
            os.remove(str(targetfile))
        elif not hash_check(targetfile, hashstr, raise_exception=False):
            logger.print_verbose("File exists but hash differs, {file.name} will be re-downloaded".format(file=targetfile))
            os.remove(str(targetfile))
        else:
            logger.print_verbose("File {file.name} is already in cache".format(file=targetfile))

    if not targetfile.exists():
        try:
            message = "Getting {file.name}".format(file=targetfile)
            if parsedurl.scheme == "":
                # file mode, simple file copy
                message = "Copying {file.name}".format(file=targetfile)
                display_progress(logger, message, 0, 1)
                copyfile(parsedurl.path, str(targetfile))
            elif parsedurl.scheme.startswith("http"):
                # http/https mode, get file length before
                message = "Downloading {file.name}".format(file=targetfile)
                display_progress(logger, message, 0, 1)
                download_file_with_retry(url, targetfile, logger, message)
            else:
                # other scheme, use urllib
                display_progress(logger, message, 0, 1)
                urlretrieve(url, str(targetfile))
            display_progress(logger, message, 1, 1)
        finally:
            # End line since all progress message are on the same line
            logger.print_default("")
        if hashstr is not None:
            hash_check(targetfile, hashstr, raise_exception=True)
    return targetfile


def display_progress(logger: TextLogger, message: str, worked: int, total: int, end: str = "", try_percent=True):
    kwargs = {"message": message, "worked": worked, "total": total, "progress": "??"}
    if try_percent and 0 <= worked <= total and total > 0:
        kwargs["progress"] = "{0:.0%}".format(worked / total)
    else:
        kwargs["progress"] = "{0}/{1}".format(worked, total)
    logger.print_default("\r[{progress}] {message} ".format(**kwargs), end=end, flush=True)


def env_list_to_map(kv_list: list):
    out = OrderedDict()
    if kv_list is not None:
        for line in kv_list:
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
            else:
                out[line] = ""
    return out


def fs_compute_total_size(item: Path):
    """
    Get the size of a file or a folder (reccursive)
    """
    if not item.exists():
        return -1
    if not item.is_dir():
        return item.stat().st_size
    out = 0
    for sub in item.iterdir():
        out += fs_compute_total_size(sub)
    return out


def mkdirs(folder: Path):
    if not folder.is_dir():
        folder.mkdir(parents=True)
    return folder


def mkdir_tmp_leaf_dir():
    return Path(tempfile.mkdtemp(prefix="leaf-alt-root_"))


def chmod_write(item: Path):
    if item.exists() and not item.is_symlink():
        item.chmod(item.stat().st_mode | 0o222)
    if item.is_dir():
        for i in item.iterdir():
            chmod_write(i)


def rmtree_force(item: Path):
    if item.exists():
        chmod_write(item)
        shutil.rmtree(str(item), ignore_errors=True)
        if item.exists():
            raise IOError("Could not remove {0}".format(item))


__HASH_NAME = "sha384"
__HASH_FACTORY = hashlib.sha384
__HASH_LEN = 96
__HASH_BLOCKSIZE = 4096


def hash_parse(hashstr: str):
    parts = hashstr.split(":")
    if len(parts) != 2:
        raise LeafException("Invalid hash format {hash}".format(hash=hashstr))
    if parts[0] != __HASH_NAME:
        raise LeafException("Unsupported hash method, expecting {hash}".format(hash=__HASH_NAME))
    if len(parts[1]) != __HASH_LEN:
        raise LeafException("Hash value '{hash}' has not the correct length, expecting {len}".format(hash=parts[1], len=__HASH_LEN))
    return parts


def hash_compute(file: Path):
    """
    Return the hash of the given file
    """
    hasher = __HASH_FACTORY()
    with file.open("rb") as fp:
        buf = fp.read(__HASH_BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = fp.read(__HASH_BLOCKSIZE)
    return __HASH_NAME + ":" + hasher.hexdigest()


def hash_check(file: Path, expected: str, raise_exception: bool = False):
    hash_parse(expected)
    actual = hash_compute(file)
    if actual != expected:
        if raise_exception is True:
            raise InvalidHashException(file, actual, expected)
        return False
    return True
