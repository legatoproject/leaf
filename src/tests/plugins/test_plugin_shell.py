"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os

from tests.testutils import LeafTestCaseWithCli


class TestPluginShell(LeafTestCaseWithCli):
    def test_shell(self):
        pwd = os.getcwd()
        try:
            os.chdir(str(self.ws_folder))
            self.simple_exec("setup", "-p", "env-A")

            self.simple_exec("shell", "-c", "true")
            self.simple_exec("shell", "-n", "bash", "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
            self.simple_exec("shell", "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
            self.simple_exec("shell", "-n", "zsh", "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
        finally:
            os.chdir(str(pwd))
