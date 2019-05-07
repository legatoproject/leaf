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
        out = []
        self[0].activate(
            kv_consumer=lambda k, v: out.append(Environment.tostring_export(k, v)), file_consumer=lambda f: out.append(Environment.tostring_file(f))
        )
        return "\n".join(out)

    def _tostring_default(self):
        out = []
        self[0].activate(
            comment_consumer=lambda c: out.append(Environment.tostring_comment(c)),
            kv_consumer=lambda k, v: out.append(Environment.tostring_export(k, v)),
            file_consumer=lambda f: out.append(Environment.tostring_file(f)),
        )
        return "\n".join(out)

    def _tostring_verbose(self):
        return self._tostring_default()
