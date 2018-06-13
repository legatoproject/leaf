'''
@author: david
'''

import os
from pathlib import Path
import traceback
import unittest

from tests.testutils import LeafCliWrapper


class TestExtensionsCli(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def setUp(self):
        LeafCliWrapper.setUp(self)
        TestExtensionsCli.OLD_MANPATH = os.environ.get("MANPATH")
        manDir = Path("man/")
        self.assertTrue(manDir.is_dir())
        if TestExtensionsCli.OLD_MANPATH is None:
            os.environ['MANPATH'] = "%s" % (manDir.resolve())
        else:
            os.environ['MANPATH'] = "%s:%s" % (manDir.resolve(),
                                               TestExtensionsCli.OLD_MANPATH)
        print("Update MANPATH:", os.environ['MANPATH'])

    def tearDown(self):
        if TestExtensionsCli.OLD_MANPATH is None:
            del os.environ['MANPATH']
        else:
            os.environ['MANPATH'] = TestExtensionsCli.OLD_MANPATH
        LeafCliWrapper.tearDown(self)

    def testHelp(self):
        try:
            self.leafExec("help", "unknown_page", expectedRc=3)
            self.leafExec("help", "--help")
            self.leafExec("help", "--list")
            self.leafExec("help")
            self.leafExec("help", "setup")
            self.leafExec("help", "setup", "--unknown-arg", expectedRc=2)
        except SystemExit:
            traceback.print_exc()
            self.fail("System exit caught")


if __name__ == "__main__":
    unittest.main()
