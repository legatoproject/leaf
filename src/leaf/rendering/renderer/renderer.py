"""
Abstract parent for command renderers

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import errno
import signal
from abc import ABC, abstractmethod
from shutil import get_terminal_size
from subprocess import PIPE, Popen

from leaf.core.error import UserCancelException
from leaf.core.logger import Verbosity
from leaf.rendering.ansi import remove_ansi_chars
from leaf.rendering.formatutils import get_leaf_pager, isatty

TERMINAL_WIDTH, TERMINAL_HEIGHT = get_terminal_size((-1, -1))


class Renderer(list, ABC):

    """
    Abstract Renderer
    """

    def __init__(self, *items):
        list.__init__(self, *items)
        self.tm = None
        self.verbosity = None
        self.use_pager_if_needed = True

    def _custom_item_str(self, item):
        return str(item)

    def _tostring_quiet(self):
        """
        Render inputList in quiet verbosity
        """
        return "\n".join(map(self._custom_item_str, self))

    @abstractmethod
    def _tostring_default(self):
        """
        Render inputList in default verbosity
        """
        pass

    @abstractmethod
    def _tostring_verbose(self):
        """
        Render inputList in verbose verbosity
        """
        pass

    def __str__(self):
        if self.verbosity == Verbosity.QUIET:
            out = self._tostring_quiet()
        elif self.verbosity == Verbosity.VERBOSE:
            out = self._tostring_verbose()
        else:
            out = self._tostring_default()
        return str(out)

    def print_renderer(self):
        """
        Print or pipe to pager if necessary and possible
        """
        out = str(self)
        if len(out) > 0:
            pager = get_leaf_pager()
            if self._should_use_pager(out) and pager is not None:
                self._pipe_to_pager(pager, out)
            else:
                print(out)

    def _should_use_pager(self, printed):
        """
        Check the terminal size and return True if we need pager
        """
        if not self.use_pager_if_needed:
            return False

        if self.verbosity == Verbosity.QUIET:
            return False

        if not isatty():
            return False

        if TERMINAL_HEIGHT == -1 or TERMINAL_WIDTH == -1:
            return False

        lines = remove_ansi_chars(printed).split("\n")

        # Check height
        if len(lines) + 1 > TERMINAL_HEIGHT:  # +1 for prompt
            return True

        # Check width
        return max(map(len, lines)) > TERMINAL_WIDTH

    def _pipe_to_pager(self, pager, data):
        """
        Pipe toPrint to the given pager
        """
        p = Popen(pager, stdin=PIPE)
        try:
            try:
                p.stdin.write(data.encode())
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
        except UserCancelException:
            # Exit quietly on CTRL-C
            p.send_signal(signal.SIGTSTP)
