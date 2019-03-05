"""
Renderer for exceptions in leaf app

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""

from leaf.rendering.renderer.renderer import Renderer


class QuestionRenderer(Renderer):

    """
    Renderer for LeafException
    """

    def __init__(self, message):
        Renderer.__init__(self)
        self.message = message

    def _tostring_quiet(self):
        return self.message

    def _tostring_default(self):
        return self.tm.QUESTION(self.message)

    def _tostring_verbose(self):
        return self.tm.QUESTION(self.message)
