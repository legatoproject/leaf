'''
@author: seb
'''

import os
import unittest

from tests.utils import LeafPackageManagerCliWrapper


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestPackageManagerCli_Default(LeafPackageManagerCliWrapper):

    def __init__(self, methodName):
        LeafPackageManagerCliWrapper.__init__(self, methodName)

    def testConfig(self):
        self.leafPackageManagerExec("config")

    def testRemote(self):
        self.leafPackageManagerExec("remote", "--add", self.getRemoteUrl())
        self.leafPackageManagerExec("remote")
        self.leafPackageManagerExec("remote", "--rm", self.getRemoteUrl())
        self.leafPackageManagerExec("remote")

    def testSearch(self):
        self.leafPackageManagerExec("search")
        self.leafPackageManagerExec("search", "--all")

    def testDepends(self):
        self.leafPackageManagerExec("install", "container-A_1.0")
        self.leafPackageManagerExec("dependencies", "container-A_2.0")
        self.leafPackageManagerExec("dependencies", "-i", "container-A_2.0")

    def testInstall(self):
        self.leafPackageManagerExec("install", "container-A")
        self.leafPackageManagerExec("list")
        self.leafPackageManagerExec("list", "--all")
        self.checkInstalledPackages('container-A_2.1',
                                    'container-C_1.0',
                                    'container-D_1.0')

    def testEnv(self):
        self.leafPackageManagerExec("install", "env-A_1.0")
        self.leafPackageManagerExec("env", "env-A_1.0")

    def testInstallWithSteps(self):
        self.leafPackageManagerExec("install", "install_1.0")
        self.checkInstalledPackages('install_1.0')

    def testInstallUninstallKeep(self):
        self.leafPackageManagerExec("install", "container-A_1.0")
        self.checkInstalledPackages('container-A_1.0',
                                    'container-B_1.0',
                                    'container-C_1.0',
                                    'container-E_1.0')
        self.leafPackageManagerExec("install", "container-A_2.0")
        self.checkInstalledPackages('container-A_1.0',
                                    'container-A_2.0',
                                    'container-B_1.0',
                                    'container-C_1.0',
                                    'container-D_1.0',
                                    'container-C_1.0')
        self.leafPackageManagerExec("remove", "container-A_1.0")
        self.checkInstalledPackages('container-A_2.0',
                                    'container-C_1.0',
                                    'container-D_1.0')

    def testClean(self):
        self.leafPackageManagerExec("clean")

    def testMissingApt(self):
        self.leafPackageManagerExec("dependencies", "--apt",
                                    "deb_1.0", "failure-depends-deb_1.0")
        self.leafPackageManagerExec(
            "install", "failure-depends-deb_1.0", expectedRc=2)
        self.leafPackageManagerExec(
            "install", "--skip-apt", "failure-depends-deb_1.0")
        self.checkInstalledPackages('failure-depends-deb_1.0')


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
