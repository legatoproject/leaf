'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from tests.testutils import LeafTestCaseWithCli
from leaf import __version__


class TestPluginVersion(LeafTestCaseWithCli):

    def testVersion(self):
        self.leafExec("version")
        self.assertEqual("leaf version " + __version__, self.exec("version"))
        self.assertEqual(self.exec("--version"), self.exec("version"))
