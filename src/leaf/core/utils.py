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
import time
from collections import OrderedDict
from functools import total_ordering
from itertools import zip_longest
from pathlib import Path

from leaf import __version__
from leaf.core.constants import LeafConstants
from leaf.core.error import InvalidHashException, LeafException, NotEnoughSpaceException

_IGNORED_PATTERN = re.compile("^.*_ignored[0-9]*$")
_VERSION_SEPARATOR = re.compile("[-_.~]")


@total_ordering
class Version:
    def __init__(self, version: str):
        self.__version = version

    @property
    def value(self):
        return self.__version.strip()

    def __str__(self):
        return self.value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.__eq__(Version(other))
        if not isinstance(other, Version):
            return NotImplemented
        return version_comparator(self.value, other.value) == 0

    def __lt__(self, other):
        if isinstance(other, str):
            return self.__lt__(Version(other))
        return version_comparator(self.value, other.value) < 0


CURRENT_LEAF_VERSION = Version(__version__)


def version_string_to_tuple(version):
    def tryint(x):
        try:
            return int(x)
        except Exception:
            return x

    return tuple(tryint(x) for x in _VERSION_SEPARATOR.split(version.strip()))


def version_comparator(a: str, b: str, implicit_zero: bool = False):
    # Check string given
    if not isinstance(a, str) or not isinstance(b, str):
        raise ValueError()

    # extract tuples
    a, b = version_string_to_tuple(a), version_string_to_tuple(b)

    if implicit_zero:
        # Fill with 0 the shortest
        if len(a) < len(b):
            a += (0,) * (len(b) - len(a))
        elif len(b) < len(a):
            b += (0,) * (len(a) - len(b))
        assert len(a) == len(b)

    # Check equality
    if a == b:
        return 0

    # Iterate over values
    for va, vb in zip_longest(a, b):
        # Detect shorter version
        if va is None:
            return -1
        if vb is None:
            return 1
        # If different type, use str comparison
        if type(va) != type(vb):
            va, vb = str(va), str(vb)
        if va < vb:
            return -1
        if va > vb:
            return 1

    # Tuple are equal
    return 0


def version_comparator_lt(a: str, b: str):
    return version_comparator(a, b) < 0


def check_supported_python_version():
    # Check python version
    if sys.version_info < LeafConstants.MIN_PYTHON_VERSION:
        print(
            "Unsupported Python version, please use at least Python {version}.".format(version=".".join(map(str, LeafConstants.MIN_PYTHON_VERSION))),
            file=sys.stderr,
        )
        sys.exit(1)


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


def fs_get_free_space(folder: Path) -> int:
    statvfs = os.statvfs(str(folder))
    return statvfs.f_frsize * statvfs.f_bavail


def fs_check_free_space(folder: Path, neededspace: int):
    freespace = fs_get_free_space(folder)
    if neededspace > freespace:
        raise NotEnoughSpaceException(folder, freespace, neededspace)


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
