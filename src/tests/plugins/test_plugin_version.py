"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf import __version__
from tests.testutils import LeafTestCaseWithCli


class TestPluginVersion(LeafTestCaseWithCli):
    def test_version(self):
        self.leaf_exec("version")
        self.assertEqual("leaf version " + __version__, self.simple_exec("version"))
        self.assertEqual(self.simple_exec("--version"), self.simple_exec("version"))
