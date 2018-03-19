'''
@author: seb
'''

import os
import unittest

from tests.utils import TestWithRepository, LeafCliWrapper


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestPackageManagerCli_Default(TestWithRepository, LeafCliWrapper):

    def __init__(self, methodName):
        TestWithRepository.__init__(self, methodName)
        LeafCliWrapper.__init__(self)

    def setUp(self):
        TestWithRepository.setUp(self)

    def initLeafConfig(self, setRoot=True, addRemote=True, refresh=True):
        LeafCliWrapper.initLeafConfig(self, TestWithRepository.CONFIG_FILE,
                                      setRoot=setRoot,
                                      addRemote=addRemote)
        if setRoot and addRemote and refresh:
            self.leafExec("refresh")

    def checkContent(self, *pisList):
        for pis in pisList:
            folder = self.getInstallFolder() / str(pis)
            self.assertTrue(folder.is_dir(), msg=str(folder))
        folderItemCount = 0
        for i in self.getInstallFolder().iterdir():
            if i.is_dir():
                folderItemCount += 1
        self.assertEqual(len(pisList),
                         folderItemCount)

    def testConfig(self):
        self.initLeafConfig(False)
        self.leafExec("config")
        self.initLeafConfig()
        self.leafExec("config")

    def testRemote(self):
        self.initLeafConfig(False)
        self.leafExec("remote", "--add", self.getRemoteUrl())
        self.leafExec("remote")
        self.leafExec("remote", "--rm", self.getRemoteUrl())
        self.leafExec("remote")

    def testSearch(self):
        self.initLeafConfig()
        self.leafExec("search")
        self.leafExec("search", "--all")

    def testDepends(self):
        self.initLeafConfig()
        self.leafExec("install", "container-A_1.0")
        self.leafExec("dependencies", "container-A_2.0")
        self.leafExec("dependencies", "-i", "container-A_2.0")

    def testDownload(self):
        self.initLeafConfig()
        self.leafExec("download", "container-A_2.1")

    def testInstall(self):
        self.initLeafConfig()
        self.leafExec("install", "container-A")
        self.leafExec("list")
        self.leafExec("list", "--all")
        self.checkContent('container-A_2.1',
                          'container-C_1.0',
                          'container-D_1.0')

    def testEnv(self):
        self.initLeafConfig()
        self.leafExec("install", "env-A_1.0")
        self.leafExec("env", "env-A_1.0")

    def testInstallWithSteps(self):
        self.initLeafConfig()
        self.leafExec("install", "install_1.0")
        self.checkContent('install_1.0')

    def testInstallUninstallKeep(self):
        self.initLeafConfig()
        self.leafExec("install", "container-A_1.0")
        self.checkContent('container-A_1.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-E_1.0')
        self.leafExec("install", "container-A_2.0")
        self.checkContent('container-A_1.0',
                          'container-A_2.0',
                          'container-B_1.0',
                          'container-C_1.0',
                          'container-D_1.0',
                          'container-C_1.0')
        self.leafExec("remove", "container-A_1.0")
        self.checkContent('container-A_2.0',
                          'container-C_1.0',
                          'container-D_1.0')

    def testClean(self):
        self.initLeafConfig()
        self.leafExec("clean")

    def testMissingApt(self):
        self.initLeafConfig()
        self.leafExec("dependencies", "--apt",
                      "deb_1.0", "failure-depends-deb_1.0")
        with self.assertRaises(ValueError):
            self.leafExec("install", "failure-depends-deb_1.0")
        self.leafExec("install", "--skip-apt", "failure-depends-deb_1.0")
        self.checkContent('failure-depends-deb_1.0')


@unittest.skipUnless("VERBOSE" in LEAF_UT_LEVELS, "Test disabled")
class TestPackageManagerCli_Verbose(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.postCommandArgs.append("--verbose")


@unittest.skipUnless("QUIET" in LEAF_UT_LEVELS, "Test disabled")
class TestPackageManagerCli_Quiet(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.postCommandArgs.append("--quiet")


@unittest.skipUnless("JSON" in LEAF_UT_LEVELS, "Test disabled")
class TestPackageManagerCli_Json(TestPackageManagerCli_Default):
    def __init__(self, methodName):
        TestPackageManagerCli_Default.__init__(self, methodName)
        self.preCommandArgs.append("--json")


if __name__ == "__main__":
    unittest.main()
