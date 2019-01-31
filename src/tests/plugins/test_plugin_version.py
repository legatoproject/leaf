'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from tests.testutils import LeafCliWrapper
from leaf import __version__


class TestPluginVersion(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testVersion(self):
        self.leafExec("version")
        self.assertEqual("leaf version " + __version__, self.exec("version"))
        self.assertEqual(self.exec("--version"), self.exec("version"))
