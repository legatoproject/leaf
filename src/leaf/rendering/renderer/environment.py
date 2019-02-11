'''
Renderer for env command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from leaf.model.environment import Environment
from leaf.rendering.renderer.renderer import Renderer


class EnvironmentRenderer(Renderer):
    '''
    Renderer for env
    Same as before, no table is used here
    '''

    def __init__(self, env):
        Renderer.__init__(self)
        self.append(env)
        self.usePagerIfNeeded = False

    def _toStringQuiet(self):
        self.out = []

        def kvConsumer(k, v):
            self.out.append(Environment.exportCommand(k, v))

        self[0].printEnv(kvConsumer=kvConsumer)

        return '\n'.join(self.out)

    def _toStringDefault(self):
        self.out = []

        def commentConsumer(c):
            self.out.append(Environment.comment(c))

        def kvConsumer(k, v):
            self.out.append(Environment.exportCommand(k, v))

        self[0].printEnv(kvConsumer=kvConsumer,
                         commentConsumer=commentConsumer)

        return '\n'.join(self.out)

    def _toStringVerbose(self):
        return self._toStringDefault()
