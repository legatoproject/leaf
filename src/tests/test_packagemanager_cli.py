'''
@author: seb
'''

import os
import unittest

from tests.utils import LeafCliWrapper, RESOURCE_FOLDER


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestPackageManagerCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testConfig(self):
        self.leafExec("config:user")

    def testRemote(self):
        self.leafExec("config:user", "--add-remote", self.getRemoteUrl())
        self.leafExec("config:u", "--rm-remote", self.getRemoteUrl())

    def testSearch(self):
        self.leafExec("search")
        self.leafExec("search", "--all")

    def testDepends(self):
        self.leafExec(["pkg", "deps"], "--available", "container-A_1.0")
        self.leafExec(["pkg", "deps"], "--install", "container-A_1.0")
        self.leafExec(["pkg", "deps"], "--installed", "container-A_1.0")
        self.leafExec(["pkg", "deps"], "--uninstall", "container-A_1.0")
        self.leafExec(["pkg", "deps"], "--prereq", "container-A_1.0")

    def testInstall(self):
        self.leafExec(["pkg", "install"], "container-A")
        self.leafExec(["pkg", "list"])
        self.leafExec(["pkg", "list"], "--all")
        self.checkInstalledPackages(['container-A_2.1',
                                     'container-C_1.0',
                                     'container-D_1.0'])

    def testEnv(self):
        self.leafExec(["pkg", "install"], "env-A_1.0")
        self.leafExec(["pkg", "env"], "env-A_1.0")

    def testInstallWithSteps(self):
        self.leafExec(["pkg", "install"], "install_1.0")
        self.checkInstalledPackages(['install_1.0'])

    def testInstallUninstallKeep(self):
        self.leafExec(["pkg", "install"], "container-A_1.0")
        self.checkInstalledPackages(['container-A_1.0',
                                     'container-B_1.0',
                                     'container-C_1.0',
                                     'container-E_1.0'])
        self.leafExec(["pkg", "install"], "container-A_2.0")
        self.checkInstalledPackages(['container-A_1.0',
                                     'container-A_2.0',
                                     'container-B_1.0',
                                     'container-C_1.0',
                                     'container-D_1.0',
                                     'container-C_1.0'])
        self.leafExec(["pkg", "remove"], "container-A_1.0")
        self.checkInstalledPackages(['container-A_2.0',
                                     'container-C_1.0',
                                     'container-D_1.0'])

    def testConditionalInstall(self):
        self.leafExec(["pkg", "install"], "condition")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])

        self.leafExec(["pkg", "remove"], "condition")
        self.checkInstalledPackages([])

        self.leafExec("config:user", "--set", "FOO=BAR")
        self.leafExec(["pkg", "install"], "condition")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-C_1.0",
                                     "condition-F_1.0"])

        self.leafExec(["pkg", "remove"], "condition")
        self.checkInstalledPackages([])

        self.leafExec("config:user",
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=WorlD")
        self.leafExec(["pkg", "install"], "condition")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-C_1.0",
                                     "condition-E_1.0",
                                     "condition-G_1.0"])

        self.leafExec(["pkg", "remove"], "condition")
        self.checkInstalledPackages([])

    def testRemotes(self):
        self.leafExec("remotes")
        self.leafExec("config:user", "--add-remote",
                      "https://foo.tld/bar/index.json")
        self.leafExec("remotes")

    def testPrereq(self):
        self.leafExec(["pkg", "prereq"], "prereq-true_1.0")
        self.assertFalse(
            (self.getAltWorkspaceFolder() / "prereq-true_1.0").is_dir())
        self.leafExec(["pkg", "prereq"],
                      "--target", self.getAltWorkspaceFolder(),
                      "prereq-true_1.0")
        self.assertTrue(
            (self.getAltWorkspaceFolder() / "prereq-true_1.0").is_dir())

    def DISABLED_testExternalCommand(self):
        with self.assertRaises(SystemExit):
            self.leafExec("foo")
        oldPath = os.environ['PATH']
        try:
            self.assertTrue(RESOURCE_FOLDER.is_dir())
            os.environ['PATH'] = oldPath + ":" + str(RESOURCE_FOLDER)
            self.leafExec("foo")
        finally:
            os.environ['PATH'] = oldPath


@unittest.skipUnless("VERBOSE" in LEAF_UT_LEVELS, "Test disabled")
class TestPackageManagerCli_Verbose(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipUnless("QUIET" in LEAF_UT_LEVELS, "Test disabled")
class TestPackageManagerCli_Quiet(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


@unittest.skipUnless("JSON" in LEAF_UT_LEVELS, "Test disabled")
class TestPackageManagerCli_Json(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.jsonEnvValue = "1"


if __name__ == "__main__":
    unittest.main()
