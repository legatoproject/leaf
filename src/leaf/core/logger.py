'''
Leaf Package Manager

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

import sys
import traceback
from enum import IntEnum, unique

from leaf.core.constants import LeafSettings


def printTrace(message=None):
    if LeafSettings.DEBUG_MODE.as_boolean():
        if message is not None:
            print(message, file=sys.stderr)
        if sys.exc_info()[0] is not None:
            traceback.print_exc(file=sys.stderr)


@unique
class Verbosity(IntEnum):
    QUIET = 0
    DEFAULT = 1
    VERBOSE = 2

    @staticmethod
    def get_current():
        v = LeafSettings.VERBOSITY.value
        if v is not None:
            if v.lower() == "quiet":
                return Verbosity.QUIET
            if v.lower() == "verbose":
                return Verbosity.VERBOSE
        return Verbosity.DEFAULT


class TextLogger ():

    @property
    def verbosity(self):
        return Verbosity.get_current()

    def isQuiet(self):
        return self.verbosity == Verbosity.QUIET

    def isVerbose(self):
        return self.verbosity == Verbosity.VERBOSE

    def printQuiet(self, *message, **kwargs):
        if self.verbosity >= Verbosity.QUIET:
            print(*message, **kwargs)

    def printDefault(self, *message, **kwargs):
        if self.verbosity >= Verbosity.DEFAULT:
            print(*message, **kwargs)

    def printVerbose(self, *message, **kwargs):
        if self.verbosity >= Verbosity.VERBOSE:
            print(*message, **kwargs)

    def printError(self, *message):
        print(*message, file=sys.stderr)
        printTrace()
