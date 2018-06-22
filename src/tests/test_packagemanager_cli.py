'''
@author: seb
'''

import os
import unittest

from tests.testutils import LeafCliWrapper, RESOURCE_FOLDER


LEAF_UT_SKIP = os.environ.get("LEAF_UT_SKIP", "")


class TestPackageManagerCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testConfig(self):
        self.leafExec("config")

    def testRemote(self):
        self.leafExec(["remote", "add"], "alt", self.getRemoteUrl())
        self.leafExec(["remote", "add"], "alt", self.getRemoteUrl(),
                      expectedRc=2)

        self.leafExec(["remote", "disable"], "alt")
        self.leafExec(["remote", "enable"], "alt")

        self.leafExec(["remote", "remove"], "alt")
        self.leafExec(["remote", "remove"], "alt",
                      expectedRc=2)
        self.leafExec(["remote", "enable"], "alt",
                      expectedRc=2)

    def testSearch(self):
        self.leafExec("search")
        self.leafExec("search", "--all")

    def testDepends(self):
        self.leafExec(["package", "deps"], "--available", "container-A_1.0")
        self.leafExec(["package", "deps"], "--install", "container-A_1.0")
        self.leafExec(["package", "deps"], "--installed", "container-A_1.0")
        self.leafExec(["package", "deps"], "--uninstall", "container-A_1.0")
        self.leafExec(["package", "deps"], "--prereq", "container-A_1.0")

    def testInstall(self):
        self.leafExec(["package", "install"], "container-A")
        self.leafExec(["package", "list"])
        self.leafExec(["package", "list"], "--all")
        self.checkInstalledPackages(['container-A_2.1',
                                     'container-C_1.0',
                                     'container-D_1.0'])

    def testEnv(self):
        self.leafExec(["package", "install"], "env-A_1.0")
        self.leafExec(["env", "package"], "env-A_1.0")

    def testInstallWithSteps(self):
        self.leafExec(["package", "install"], "install_1.0")
        self.checkInstalledPackages(['install_1.0'])

    def testInstallUninstallKeep(self):
        self.leafExec(["package", "install"], "container-A_1.0")
        self.checkInstalledPackages(['container-A_1.0',
                                     'container-B_1.0',
                                     'container-C_1.0',
                                     'container-E_1.0'])
        self.leafExec(["package", "install"], "container-A_2.0")
        self.checkInstalledPackages(['container-A_1.0',
                                     'container-A_2.0',
                                     'container-B_1.0',
                                     'container-C_1.0',
                                     'container-D_1.0',
                                     'container-C_1.0'])
        self.leafExec(["package", "uninstall"], "container-A_1.0")
        self.checkInstalledPackages(['container-A_2.0',
                                     'container-C_1.0',
                                     'container-D_1.0'])

    def testConditionalInstall(self):
        self.leafExec(["package", "install"], "condition")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])

        self.leafExec(["package", "uninstall"], "condition")
        self.checkInstalledPackages([])

        self.leafExec(["env", "user"], "--set", "FOO=BAR")
        self.leafExec(["package", "install"], "condition")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-C_1.0",
                                     "condition-F_1.0"])

        self.leafExec(["package", "uninstall"], "condition")
        self.checkInstalledPackages([])

        self.leafExec(["env", "user"],
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=WorlD")
        self.leafExec(["package", "install"], "condition")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-C_1.0",
                                     "condition-E_1.0",
                                     "condition-G_1.0"])

        self.leafExec(["package", "uninstall"], "condition")
        self.checkInstalledPackages([])

    def testPrereq(self):
        self.leafExec(["package", "prereq"], "prereq-true_1.0")
        self.assertFalse(
            (self.getAltWorkspaceFolder() / "prereq-true_1.0").is_dir())
        self.leafExec(["package", "prereq"],
                      "--target", self.getAltWorkspaceFolder(),
                      "prereq-true_1.0")
        self.assertTrue(
            (self.getAltWorkspaceFolder() / "prereq-true_1.0").is_dir())

    def testExternalCommand(self):
        with self.assertRaises(SystemExit):
            self.leafExec("foo.sh")
        oldPath = os.environ['PATH']
        try:
            self.assertTrue(RESOURCE_FOLDER.is_dir())
            os.environ['PATH'] = oldPath + ":" + str(RESOURCE_FOLDER)
            self.leafExec("foo.sh")
        finally:
            os.environ['PATH'] = oldPath


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestPackageManagerCli_Verbose(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestPackageManagerCli_Quiet(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


@unittest.skipIf("JSON" in LEAF_UT_SKIP, "Test disabled")
class TestPackageManagerCli_Json(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.jsonEnvValue = "1"


if __name__ == "__main__":
    unittest.main()
