"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

import traceback
import unittest

from tests.testutils import LeafTestCaseWithCli


@unittest.skip
class TestPluginGetsrc(LeafTestCaseWithCli):
    def test_getsrc(self):
        try:
            # Setup profile without source features
            self.leaf_exec("setup", "FEATURE-TEST", "-p", "featured-with-source")
            self.check_current_profile("FEATURE-TEST")
            self.check_profile_content("FEATURE-TEST", ["featured-with-source", "condition-A"])

            # Verify source list + check unknown source module
            self.leaf_exec("getsrc")
            self.leaf_exec("getsrc", "unknown", expected_rc=2)

            # Trigger source mode for test
            fake_src_file = self.ws_folder / "fake-test-src"
            self.assertFalse(fake_src_file.is_file())
            self.leaf_exec("getsrc", "test")
            self.assertTrue(fake_src_file.is_file())
            self.check_profile_content("FEATURE-TEST", ["featured-with-source", "source"])

            # Disable source mode
            self.leaf_exec("getsrc", "test", "--disable")
            self.assertTrue(fake_src_file.is_file())
            self.check_profile_content("FEATURE-TEST", ["featured-with-source", "condition-A"])
        except SystemExit:
            traceback.print_exc()
            self.fail("System exit caught")
