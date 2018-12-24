'''
Renderer for exceptions in leaf app

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''

from leaf.format.renderer.renderer import Renderer


class QuestionRenderer(Renderer):
    '''
    Renderer for LeafException
    '''

    def __init__(self, message):
        Renderer.__init__(self)
        self.message = message

    def _toStringQuiet(self):
        return self.message

    def _toStringDefault(self):
        return self.tm.QUESTION(self.message)

    def _toStringVerbose(self):
        return self.tm.QUESTION(self.message)
