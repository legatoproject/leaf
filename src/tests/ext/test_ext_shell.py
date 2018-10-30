'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os

from tests.testutils import LeafCliWrapper


class TestExtShell(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testShell(self):
        pwd = os.getcwd()
        try:
            os.chdir(str(self.getWorkspaceFolder()))
            self.leafExec("setup", "-p", "env-A")

            self.leafExec("shell", "-c", "true")
            self.leafExec("shell", "-n", "bash",
                          "-c", "test $LEAF_PROFILE = 'ENV-A'")
            self.leafExec("shell",
                          "-c", "test $LEAF_PROFILE = 'ENV-A'")
            self.leafExec("shell", "-n", "zsh",
                          "-c", "test $LEAF_PROFILE = 'ENV-A'")
        finally:
            os.chdir(str(pwd))
