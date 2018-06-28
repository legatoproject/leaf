'''
Abstract parent for command renderers

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from abc import ABC, abstractmethod
from leaf.format.logger import Verbosity


class Renderer(list, ABC):
    '''
    Abstract Renderer
    '''

    def _toStringQuiet(self):
        '''
        Render inputList in quiet verbosity
        '''
        return '\n'.join(map(str, self))

    @abstractmethod
    def _toStringDefault(self):
        '''
        Render inputList in default verbosity
        '''
        pass

    @abstractmethod
    def _toStringVerbose(self):
        '''
        Render inputList in verbose verbosity
        '''
        pass

    def __str__(self):
        if self.verbosity == Verbosity.QUIET:
            out = self._toStringQuiet()
        elif self.verbosity == Verbosity.VERBOSE:
            out = self._toStringVerbose()
        else:
            out = self._toStringDefault()
        return str(out)
