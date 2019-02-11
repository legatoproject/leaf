'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import traceback
import unittest

from tests.testutils import LeafTestCaseWithCli


@unittest.skip
class TestPluginGetsrc(LeafTestCaseWithCli):

    def testGetsrc(self):
        try:
            # Setup profile without source features
            self.leafExec("setup", "FEATURE-TEST",
                          "-p", "featured-with-source")
            self.checkCurrentProfile("FEATURE-TEST")
            self.checkProfileContent(
                "FEATURE-TEST", ["featured-with-source", "condition-A"])

            # Verify source list + check unknown source module
            self.leafExec("getsrc")
            self.leafExec("getsrc", "unknown", expectedRc=2)

            # Trigger source mode for test
            fakeSrcFile = self.getWorkspaceFolder() / "fake-test-src"
            self.assertFalse(fakeSrcFile.is_file())
            self.leafExec("getsrc", "test")
            self.assertTrue(fakeSrcFile.is_file())
            self.checkProfileContent(
                "FEATURE-TEST", ["featured-with-source", "source"])

            # Disable source mode
            self.leafExec("getsrc", "test", "--disable")
            self.assertTrue(fakeSrcFile.is_file())
            self.checkProfileContent(
                "FEATURE-TEST", ["featured-with-source", "condition-A"])
        except SystemExit:
            traceback.print_exc()
            self.fail("System exit caught")
