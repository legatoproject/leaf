"""
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

import fcntl
from contextlib import ContextDecorator
from pathlib import Path

from leaf.core.constants import LeafSettings
from leaf.core.error import LockException


class AdvisoryLock(ContextDecorator):
    def __init__(self, lockfile, advisory=True, blocking=False):
        self.lockfile = lockfile
        if self.lockfile is not None and not self.disabled:
            self.lockfile.touch(exist_ok=True)
            self.flags = 0 if blocking else fcntl.LOCK_NB
            self.lockFunction = fcntl.lockf if advisory else fcntl.flock

    @property
    def disabled(self):
        return LeafSettings.DISABLE_LOCKS.as_boolean()

    def __enter__(self):
        if self.lockfile is not None and not self.disabled:
            self.fp = self.lockfile.open("w")
            try:
                self.lockFunction(self.fp, fcntl.LOCK_EX | self.flags)
            except BlockingIOError:
                raise LockException(self.lockfile)

    def __exit__(self, *exc):
        if self.lockfile is not None and not self.disabled:
            fcntl.flock(self.fp, fcntl.LOCK_UN)
            self.fp.close()


class LockFile:
    def __init__(self, filename):
        self.file = Path(str(filename)) if filename is not None else None

    def acquire(self, advisory=True, blocking=False):
        return AdvisoryLock(self.file, advisory=advisory, blocking=blocking)
