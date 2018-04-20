'''
@author: seb
'''

from leaf.constants import LeafFiles
import os
import unittest

from tests.utils import LeafCliWrapper


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestSetupCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testSetupWsCreation(self):
        wsConfigFile = self.getWorkspaceFolder() / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(wsConfigFile.is_file())
        self.leafExec("setup", "-p", "container-A")
        self.assertTrue(wsConfigFile.is_file())

    def testProfileAlreadyExist(self):
        self.leafExec("setup", "foo", "-p", "container-A")
        self.leafExec("setup", "foo", "-p", "container-A", expectedRc=2)

    def testProfileContent(self):
        self.leafExec("setup", "foo1",
                      "-p", "condition")
        self.checkCurrentProfile("foo1")
        self.checkProfileContent("foo1", ["condition-B",
                                          "condition-D",
                                          "condition-F",
                                          "condition-H",
                                          "condition"])

        self.leafExec("setup", "foo2",
                      "--set", "FOO=BAR",
                      "-p", "condition")
        self.checkCurrentProfile("foo2")
        self.checkProfileContent("foo2", ["condition-A",
                                          "condition-C",
                                          "condition-F",
                                          "condition"])

        self.leafExec("setup", "foo3",
                      "--set", "FOO=BAR",
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=WorLD",
                      "-p", "condition")
        self.checkCurrentProfile("foo3")
        self.checkProfileContent("foo3", ["condition-A",
                                          "condition-C",
                                          "condition-E",
                                          "condition-G",
                                          "condition"])

        self.leafExec("setup", "foo4",
                      "--set", "FOO=BAR",
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=WorLD",
                      "-p", "condition",
                      "-p", "install")
        self.checkCurrentProfile("foo4")
        self.checkProfileContent("foo4", ["condition-A",
                                          "condition-C",
                                          "condition-E",
                                          "condition-G",
                                          "condition",
                                          "install"])


@unittest.skipUnless("VERBOSE" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Verbose(TestSetupCli_Default):
    def __init__(self, methodName):
        TestSetupCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipUnless("QUIET" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Quiet(TestSetupCli_Default):
    def __init__(self, methodName):
        TestSetupCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


@unittest.skipUnless("JSON" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Json(TestSetupCli_Default):
    def __init__(self, methodName):
        TestSetupCli_Default.__init__(self, methodName)
        self.jsonEnvValue = "1"


if __name__ == "__main__":
    unittest.main()
