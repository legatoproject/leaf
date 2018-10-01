'''
Renderer for exceptions in leaf app

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
import sys

from leaf.format.ansi import ANSI
from leaf.format.renderer.renderer import Renderer

from leaf.core.error import HINTS_CMD_DELIMITER, printTrace


class HintsRenderer(Renderer):
    '''
    Renderer for LeafException
    '''

    def __init__(self):
        Renderer.__init__(self)

    def _colorizeHints(self, hints):
        if not ANSI.isEnabled():
            return hints
        isCmd = hints.startswith(HINTS_CMD_DELIMITER)
        out = ""
        for elt in hints.split(HINTS_CMD_DELIMITER):
            if isCmd:
                out += self.tm.HINTS_COMMANDS(elt)
            else:
                out += self.tm.HINTS(elt)
            isCmd = not isCmd
        return out

    def _formatHints(self, hints):
        if len(hints) > 0:
            out = [self.tm.HINTS("HINTS:" if len(hints) > 1 else "HINT:")]
            out.extend(map(self._colorizeHints, hints))
            return out
        return []

    def _toStringDefault(self):
        return '\n'.join(self._formatHints(self))

    def _toStringVerbose(self):
        return self._toStringDefault()


class LeafExceptionRenderer(HintsRenderer):
    '''
    Renderer for LeafException
    '''

    def __init__(self, ex):
        self.append(ex)

    def print(self):
        out = str(self)
        if len(out) > 0:
            print(out, file=sys.stderr)
        printTrace()

    def _formatError(self, errmsg):
        return ("ERROR:", errmsg)

    def _formatCause(self, cause):
        if cause is not None:
            return ("CAUSED BY:", str(cause))
        return []

    def _toStringDefault(self):
        out = []
        out.extend(self._formatError(self[0].msg))
        out.extend(self._formatCause(self[0].cause))
        out.extend(self._formatHints(self[0].getHints()))
        return '\n'.join(out)

    def _toStringVerbose(self):
        return self._toStringDefault()
