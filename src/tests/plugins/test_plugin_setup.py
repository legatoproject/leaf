'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''


from leaf.core.constants import LeafFiles
from tests.testutils import LeafTestCaseWithCli


class TestPluginSetup(LeafTestCaseWithCli):

    def testSetupWsCreation(self):
        wsConfigFile = self.getWorkspaceFolder() / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(wsConfigFile.is_file())
        self.leafExec("setup", "-p", "container-A")
        self.assertTrue(wsConfigFile.is_file())

    def testSetupProfileAlreadyExist(self):
        self.leafExec("setup", "foo", "-p", "container-A")
        self.leafExec("setup", "foo", "-p", "container-A", expectedRc=2)

    def testSetupWithPackageIdentifier(self):
        self.leafExec("setup", "A",
                      "-p", "container-A_1.0")
        self.checkCurrentProfile("A")
        self.checkProfileContent("A",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E"])

        self.leafExec("setup", "B",
                      "-p", "container-A_2.0")
        self.checkCurrentProfile("B")
        self.checkProfileContent("B",
                                 ["container-A",
                                  "container-C",
                                  "container-D"])

    def testSetupWithPackageName(self):
        self.leafExec("setup", "A",
                      "-p", "container-A")
        self.checkCurrentProfile("A")
        self.checkProfileContent("A",
                                 ["container-A",
                                  "container-C",
                                  "container-D"])

    def testSetupProfileContent(self):
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


class TestPluginSetupVerbose(TestPluginSetup):

    def __init__(self, *args, **kwargs):
        TestPluginSetup.__init__(self, *args, verbosity="verbose", **kwargs)


class TestPluginSetupQuiet(TestPluginSetup):

    def __init__(self, *args, **kwargs):
        TestPluginSetup.__init__(self, *args, verbosity="quiet", **kwargs)
