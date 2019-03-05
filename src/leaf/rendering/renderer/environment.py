"""
Renderer for env command

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from leaf.model.environment import Environment
from leaf.rendering.renderer.renderer import Renderer


class EnvironmentRenderer(Renderer):

    """
    Renderer for env
    Same as before, no table is used here
    """

    def __init__(self, env):
        Renderer.__init__(self)
        self.append(env)
        self.use_pager_if_needed = False

    def _tostring_quiet(self):
        self.out = []

        def kv_consumer(k, v):
            self.out.append(Environment.tostring_export(k, v))

        self[0].print_env(kv_consumer=kv_consumer)

        return "\n".join(self.out)

    def _tostring_default(self):
        self.out = []

        def comment_consumer(c):
            self.out.append(Environment.tostring_comment(c))

        def kv_consumer(k, v):
            self.out.append(Environment.tostring_export(k, v))

        self[0].print_env(kv_consumer=kv_consumer, comment_consumer=comment_consumer)

        return "\n".join(self.out)

    def _tostring_verbose(self):
        return self._tostring_default()
