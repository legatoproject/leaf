import fcntl
import os
from contextlib import ContextDecorator
from pathlib import Path

from leaf.constants import EnvConstants
from leaf.core.error import LockException


class AdvisoryLock(ContextDecorator):

    def __init__(self, lockfile, advisory=True, blocking=False):
        self.lockfile = lockfile
        if self.lockfile is not None and not self.isDisabled():
            self.lockfile.touch(exist_ok=True)
            self.flags = 0 if blocking else fcntl.LOCK_NB
            self.lockFunction = fcntl.lockf if advisory else fcntl.flock

    def isDisabled(self):
        return os.getenv(EnvConstants.DISABLE_LOCKS, "") != ""

    def __enter__(self):
        if self.lockfile is not None and not self.isDisabled():
            self.fp = self.lockfile.open('w')
            try:
                self.lockFunction(self.fp, fcntl.LOCK_EX | self.flags)
            except BlockingIOError:
                raise LockException(self.lockfile)

    def __exit__(self, type, value, traceback):
        if self.lockfile is not None and not self.isDisabled():
            fcntl.flock(self.fp, fcntl.LOCK_UN)
            self.fp.close()


class LockFile():

    def __init__(self, filename):
        self.file = Path(str(filename)) if filename is not None else None

    def acquire(self, advisory=True, blocking=False):
        return AdvisoryLock(self.file, advisory=advisory, blocking=blocking)
