'''
Abstract parent for command renderers

@author:    Nicolas Lambert <nlambert@sierrawireless.com>
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <developerstudio@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from abc import ABC, abstractmethod
from shutil import get_terminal_size
from subprocess import Popen, PIPE
import errno

from leaf.format.ansi import removeAnsiChars
from leaf.format.formatutils import getPager, isatty
from leaf.format.logger import Verbosity


TERMINAL_WIDTH, TERMINAL_HEIGHT = get_terminal_size((-1, -1))


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

    def print(self):
        '''
        Print or pipe to pager if necessary and possible
        '''
        out = str(self)
        if len(out) > 0:
            pager = getPager()
            if self._shouldUsePager(out) and pager is not None:
                self._pipeToPager(pager, out)
            else:
                print(out)

    def _shouldUsePager(self, printed):
        '''
        Check the terminal size and return True if we need pager
        '''
        if not isatty():
            return False

        if TERMINAL_HEIGHT == -1 or TERMINAL_WIDTH == - 1:
            return False

        lines = removeAnsiChars(printed).split('\n')

        # Check height
        if len(lines) + 1 > TERMINAL_HEIGHT:  # +1 for prompt
            return True

        # Check width
        return max(map(len, lines)) > TERMINAL_WIDTH

    def _pipeToPager(self, pager, toPrint):
        '''
        Pipe toPrint to the given pager
        '''
        p = Popen(pager, stdin=PIPE)
        try:
            p.stdin.write(toPrint.encode())
        except IOError as e:
            if e.errno == errno.EPIPE or e.errno == errno.EINVAL:
                # Stop loop on "Invalid pipe" or "Invalid argument".
                # No sense in continuing with broken pipe.
                return
            else:
                # Raise any other error.
                raise
        p.stdin.close()
        p.wait()

        # This should always be printed below any output written to page.
        # It avoid to have a '%' char at the end when user pipe to cat for
        # example
        print("")
