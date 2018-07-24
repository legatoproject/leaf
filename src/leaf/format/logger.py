'''
Leaf Package Manager

@author:    Sébastien MB <smassot@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from abc import ABC, abstractmethod
from enum import IntEnum, unique
import sys


@unique
class Verbosity(IntEnum):
    QUIET = 0
    DEFAULT = 1
    VERBOSE = 2


class ILogger(ABC):
    '''
    Logger interface
    '''

    def __init__(self, verbosity):
        self.verbosity = verbosity

    def getVerbosity(self):
        return self.verbosity

    def isQuiet(self):
        return self.getVerbosity() == Verbosity.QUIET

    def isVerbose(self):
        return self.getVerbosity() == Verbosity.VERBOSE

    @abstractmethod
    def printQuiet(self, *message, **kwargs):
        pass

    @abstractmethod
    def printDefault(self, *message, **kwargs):
        pass

    @abstractmethod
    def printVerbose(self, *message, **kwargs):
        pass

    @abstractmethod
    def printError(self, *message):
        pass

    @abstractmethod
    def progressWorked(self, message=None, worked=0, total=100, sameLine=False):
        pass

    @abstractmethod
    def confirm(self,
                question="Do you want to continue?",
                yes=["y"],
                no=["n"],
                failOnDecline=False):
        pass


class TextLogger (ILogger):
    '''
    Prints a lot of information
    '''

    def __init__(self, verbosity, nonInteractive=True):
        ILogger.__init__(self, verbosity)
        self.nonInteractive = nonInteractive

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

    def progressWorked(self, message=None, worked=0, total=100, sameLine=False):
        if message is not None:
            if total > 100 and worked <= total:
                message = "[%d%%] %s" % (worked * 100 / total, message)
            else:
                message = "[%d/%d] %s" % (worked, total, message)
            self.printDefault(message, end='\r' if sameLine else '\n')

    def confirm(self,
                question="Do you want to continue?",
                yes=["y"],
                no=["n"],
                failOnDecline=False):
        label = " (%s/%s) " % (
            "/".join(map(str.upper, yes)),
            "/".join(map(str.lower, no)))
        while True:
            print(question, label)
            if self.nonInteractive:
                return True
            answer = input().strip()
            if answer == "":
                return True
            if answer.lower() in map(str.lower, yes):
                return True
            if answer.lower() in map(str.lower, no):
                if failOnDecline:
                    raise ValueError("Operation aborted")
                return False
