'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os

from tests.testutils import LeafTestCaseWithCli


class TestPluginShell(LeafTestCaseWithCli):

    def testShell(self):
        pwd = os.getcwd()
        try:
            os.chdir(str(self.getWorkspaceFolder()))
            self.exec("setup", "-p", "env-A")

            self.exec("shell", "-c", "true")
            self.exec("shell", "-n", "bash",
                      "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
            self.exec("shell",
                      "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
            self.exec("shell", "-n", "zsh",
                      "-c", "test \\$LEAF_PROFILE = 'ENV-A'")
        finally:
            os.chdir(str(pwd))
