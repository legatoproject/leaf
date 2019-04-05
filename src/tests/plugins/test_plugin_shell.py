"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import os

from leaf.core.constants import LeafSettings
from tests.testutils import LeafTestCaseWithCli, LEAF_SYSTEM_ROOT


class TestPluginShell(LeafTestCaseWithCli):
    def setUp(self):
        super().setUp()
        LeafSettings.SYSTEM_PKG_FOLDERS.value = LEAF_SYSTEM_ROOT

    def test_shell(self):
        pwd = os.getcwd()
        try:
            os.chdir(str(self.workspace_folder))
            self.simple_exec("setup", "-p", "env-A")

            self.simple_exec("shell", "-c", "true")
            self.simple_exec("shell", "-n", "bash", "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
            self.simple_exec("shell", "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
            self.simple_exec("shell", "-n", "zsh", "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
        finally:
            os.chdir(str(pwd))
