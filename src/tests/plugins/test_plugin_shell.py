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
            with self.assertStdout("shell.out"):
                for v in ("LEAF_PROFILE", "LEAF_ENV_A", "LEAF_ENV_A2", "MY_EXTRA_VAR1"):
                    self.simple_exec("shell", "-c", "echo {0} = \\${0}".format(v), silent=False)

        finally:
            os.chdir(str(pwd))
