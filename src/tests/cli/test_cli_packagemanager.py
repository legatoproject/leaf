'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import os
import unittest

from tests.testutils import LEAF_UT_SKIP, RESOURCE_FOLDER, LeafCliWrapper


class TestPackageManagerCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testConfig(self):
        self.leafExec("config")

    def testRemote(self):
        self.leafExec(("remote", "list"))

        self.leafExec(["remote", "add"], "--insecure",
                      "alt", self.getRemoteUrl())
        self.leafExec(["remote", "add"], "--insecure",
                      "alt", self.getRemoteUrl(),
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
        self.leafExec("search", "--tag", "tag1")
        self.leafExec("search", "--tag", "tag1", "-t", "tag2")
        self.leafExec("search", "--tag", "tag1,tag2")
        self.leafExec("search", "--tag", "tag1,tag2" "keyword1")
        self.leafExec("search", "--tag", "tag1,tag2" "keyword1", "keyword2")
        self.leafExec("search", "--tag", "tag1,tag2" "keyword1,keyword2")

    def testDepends(self):
        self.leafExec(["package", "deps"], "--available", "container-A_1.0")
        self.leafExec(["package", "deps"], "--install", "container-A_1.0")
        self.leafExec(["package", "deps"], "--installed", "container-A_1.0")
        self.leafExec(["package", "deps"], "--uninstall", "container-A_1.0")
        self.leafExec(["package", "deps"], "--prereq", "container-A_1.0")

    def testInstall(self):
        self.leafExec(["package", "install"], "container-A_2.1")
        self.leafExec(["package", "list"])
        self.leafExec(["package", "list"], "--all")
        self.checkInstalledPackages(['container-A_2.1',
                                     'container-C_1.0',
                                     'container-D_1.0'])

    def testEnv(self):
        self.leafExec(("env", "user"), "--unset", "UNKNWONVAR")
        self.leafExec(("env", "user"), "--set", "UNKNWONVAR=TOTO")
        self.leafExec(("env", "user"), "--unset", "UNKNWONVAR")

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
        self.leafExec(["package", "install"], "condition_1.0")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])

        self.leafExec(["package", "uninstall"], "condition_1.0")
        self.checkInstalledPackages([])

        self.leafExec(["env", "user"], "--set", "FOO=BAR")
        self.leafExec(["package", "install"], "condition_1.0")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-C_1.0",
                                     "condition-F_1.0"])

        self.leafExec(["package", "uninstall"], "condition_1.0")
        self.checkInstalledPackages([])

        self.leafExec(["env", "user"],
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=WorlD")
        self.leafExec(["package", "install"], "condition_1.0")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-C_1.0",
                                     "condition-E_1.0",
                                     "condition-G_1.0"])

        self.leafExec(["package", "uninstall"], "condition_1.0")
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

    def testInstallUnknownPackage(self):
        self.leafExec(["package", "install"], "unknwonPackage",
                      expectedRc=2)
        self.leafExec(["package", "install"], "container-A",
                      expectedRc=2)


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