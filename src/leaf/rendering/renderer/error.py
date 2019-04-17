"""
Renderer for exceptions in leaf app

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
import sys

from leaf.core.error import HINTS_CMD_DELIMITER
from leaf.core.logger import print_trace
from leaf.rendering.ansi import ANSI
from leaf.rendering.renderer.renderer import Renderer


class HintsRenderer(Renderer):
    def __init__(self):
        Renderer.__init__(self)
        self.use_pager_if_needed = False

    def _colorize_hints(self, hints):
        if not ANSI.enabled:
            return hints
        is_cmd = hints.startswith(HINTS_CMD_DELIMITER)
        out = "  "
        for elt in hints.split(HINTS_CMD_DELIMITER):
            if is_cmd:
                out += self.tm.HINTS_COMMANDS(elt)
            else:
                out += self.tm.HINTS(elt)
            is_cmd = not is_cmd
        return out

    def _format_hints(self, hints):
        if len(hints) > 0:
            out = [self.tm.HINTS("HINTS:" if len(hints) > 1 else "HINT:")]
            out.extend(map(self._colorize_hints, hints))
            return out
        return []

    def _tostring_default(self):
        return "\n".join(self._format_hints(self))

    def _tostring_verbose(self):
        return self._tostring_default()


class LeafExceptionRenderer(HintsRenderer):
    def __init__(self, ex):
        self.append(ex)

    def print_renderer(self):
        out = str(self)
        if len(out) > 0:
            print(out, file=sys.stderr)
        print_trace()

    def _format_error(self, errmsg):
        return (self.tm.ERROR_TITLE("ERROR:"), self.tm.ERROR_MESSAGE("  " + errmsg))

    def _format_cause(self, cause):
        if cause is not None:
            return (self.tm.ERROR_TITLE("CAUSED BY:"), self.tm.ERROR_MESSAGE("  " + str(cause)))
        return []

    def _tostring_default(self):
        out = []
        out.extend(self._format_error(self[0].message))
        out.extend(self._format_cause(self[0].cause))
        out.extend(self._format_hints(self[0].get_hints()))
        return "\n".join(out)

    def _tostring_verbose(self):
        return self._tostring_default()
