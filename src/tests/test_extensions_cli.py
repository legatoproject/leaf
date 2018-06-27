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

    def testUpdate(self):
        self.leafExec(("init"))
        self.leafExec(("profile", "create"), "myprofile")
        self.leafExec(("profile", "config"),
                      "-p", "version_1.0", "-p", "container-A_1.0")
        self.leafExec(("profile", "sync"))

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "version_1.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E",
                                  "version"])

        self.leafExec("update", "-p", "version_2.0")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "version_1.0",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E",
                                  "version"])

        self.leafExec("update", "-p", "container-A_1.1")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-A_1.1",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "version_1.0",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E",
                                  "version"])

        self.leafExec("update")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-A_1.1",
                                     "container-A_2.1",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-D_1.0",
                                     "container-E_1.0",
                                     "version_1.0",
                                     "version_2.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-C",
                                  "container-D",
                                  "version"])


if __name__ == "__main__":
    unittest.main()
