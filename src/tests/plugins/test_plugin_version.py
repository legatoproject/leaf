"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf import __version__
from leaf.core.constants import LeafSettings
from tests.testutils import LEAF_SYSTEM_ROOT, LeafTestCaseWithCli


class TestPluginVersion(LeafTestCaseWithCli):
    def setUp(self):
        super().setUp()
        LeafSettings.SYSTEM_PKG_FOLDERS.value = LEAF_SYSTEM_ROOT

    def test_version(self):
        self.leaf_exec("version")
        self.assertEqual("leaf version " + __version__, self.simple_exec("version"))
        self.assertEqual(self.simple_exec("--version"), self.simple_exec("version"))
