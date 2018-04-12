'''
@author: seb
'''

from leaf.constants import LeafFiles
import os
import shutil
import unittest

from tests.utils import LeafProfileCliWrapper


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestProfileCli_Default(LeafProfileCliWrapper):

    def __init__(self, methodName):
        LeafProfileCliWrapper.__init__(self, methodName)

    def testInitWithoutProfile(self):
        self.leafProfileExec("init")
        self.leafProfileExec("list")
        self.leafProfileExec("env", expectedRc=2)

    def testInitWithProfile(self):
        self.leafProfileExec("init", "-p", "container-A_1.0")
        self.leafProfileExec("list")
        self.leafProfileExec("env")

    def testWorkspaceNotInit(self):
        self.leafProfileExec("list", expectedRc=2)
        self.leafProfileExec("init")
        self.leafProfileExec("list")

    def testInitWithEnv(self):
        self.leafProfileExec("init",
                             "-e", "FOO=BAR",
                             "-e", "FOO2=BAR2")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.checkProfileContent("default", [])

    def testInitWithPackages(self):
        self.leafProfileExec("init",
                             "-e", "FOO=BAR",
                             "-e", "FOO2=BAR2",
                             "-p", "container-A_1.0",
                             "-p", "deb_1.0")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.checkProfileContent("CONTAINER-A_DEB", ["container-A",
                                                     "container-B",
                                                     "container-C",
                                                     "container-E",
                                                     "deb"])

    def testCreate(self):
        self.leafProfileExec("init")
        self.leafProfileExec("create", "foo",
                             "-p", "container-A_1.0",
                             "-p", "deb_1.0",
                             "-e", "FOO=BAR",
                             "-e", "FOO2=BAR2")
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E",
                                         "deb"])
        self.leafProfileExec("list")
        self.leafProfileExec("update", "foo",
                             "-p", "container-A",
                             "-e", "FOO3=BAR3")
        self.leafProfileExec("env", "foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D",
                                         "deb"])
        self.leafProfileExec("create", "foo", expectedRc=2)

    def testDelete(self):
        self.leafProfileExec("init")
        self.leafProfileExec("create", "foo")
        self.leafProfileExec("create", "foo2")
        self.leafProfileExec("list")
        self.leafProfileExec("delete", "foo", "foo2")
        self.leafProfileExec("list")

    def testReservedName(self):
        self.leafProfileExec("init")
        self.leafProfileExec("create", "current", expectedRc=2)
        self.leafProfileExec("create", "", expectedRc=2)
        self.leafProfileExec("create", "foo")
        self.leafProfileExec("create", "foo", expectedRc=2)

    def testAutoFindWorkspace(self):
        profileConfigFile = self.getWorkspaceFolder() / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(profileConfigFile.exists())

        self.leafProfileExec("init")
        self.assertTrue(profileConfigFile.exists())

        self.leafProfileExec("list")
        self.leafProfileExec("list",
                             altWorkspace=self.getAltWorkspaceFolder(),
                             expectedRc=2)

        subFolder = self.getWorkspaceFolder() / "foo" / "bar"
        subFolder.mkdir(parents=True)
        self.leafProfileExec("list",
                             altWorkspace=subFolder,
                             expectedRc=2)

        oldPwd = os.getcwd()
        try:
            os.chdir(str(subFolder))
            self.leafProfileExec("list")
        finally:
            os.chdir(oldPwd)

    def testWithoutVersion(self):
        self.leafProfileExec("init", "-p", "container-A")
        self.leafProfileExec("list")
        self.checkProfileContent("CONTAINER-A", ["container-A",
                                                 "container-C",
                                                 "container-D"])

    def testBootstrapWorkspace(self):
        self.leafProfileExec("init", "-p", "container-A")
        self.checkCurrentProfile("CONTAINER-A")
        self.leafProfileExec("create", "-p", "deb")
        self.checkCurrentProfile("DEB")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.checkProfileContent("CONTAINER-A", ["container-A",
                                                 "container-C",
                                                 "container-D"])
        dataFolder = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME
        self.assertTrue(dataFolder.exists())
        shutil.rmtree(str(dataFolder))
        self.assertFalse(dataFolder.exists())

        self.leafProfileExec("list")
        self.leafProfileExec("env", expectedRc=2)
        self.leafProfileExec("sync")
        self.checkCurrentProfile("CONTAINER-A")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.checkProfileContent("CONTAINER-A", ["container-A",
                                                 "container-C",
                                                 "container-D"])

    def testNoAutoSync(self):
        self.leafProfileExec("init")
        self.checkCurrentProfile(None)
        self.leafProfileExec("create", "foo")
        self.checkCurrentProfile("foo")
        self.leafProfileExec("create", "--nosync", "bar")
        self.checkCurrentProfile("foo")
        self.leafProfileExec("update", "--nosync", "bar", "-p", "container-A")
        self.checkCurrentProfile("foo")
        self.leafProfileExec("update", "bar", "-e", "FOO=BAR")
        self.checkCurrentProfile("bar")

    def testRenameProfile(self):
        self.leafProfileExec("init", "-p", "container-A")
        self.leafProfileExec("list")
        self.leafProfileExec("env")

        self.leafProfileExec("rename", "CONTAINER-A", "foo")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.leafProfileExec("env", "foo")
        self.leafProfileExec("env", "default", expectedRc=2)

        self.leafProfileExec("rename", "foo", "foo")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.leafProfileExec("env", "foo")

    def testSearch(self):
        self.leafProfileExec("init", "-p", "container-A")
        self.leafProfileExec("search")
        self.leafProfileExec("search", "container")
        self.leafProfileExec("search", "-P")
        self.leafProfileExec("search", "-P", "container")

    def testUpgrade(self):
        self.leafProfileExec("init")
        self.leafProfileExec("create", "foo",
                             "-p", "version_1.0",
                             "-p", "container-A_1.0")
        self.checkCurrentProfile("foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E",
                                         "version"])

        self.leafProfileExec("upgrade", "foo")
        self.checkCurrentProfile("foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D",
                                         "version"])

    def testEnv(self):
        self.leafProfileExec("init", "-p", "env-A")
        self.leafProfileExec("env", "ENV-A")
        self.leafProfileExec("env")
        self.leafProfileExec("env",
                             "--activate-script",
                             str(self.getWorkspaceFolder() / "in.env"),
                             "--deactivate-script",
                             str(self.getWorkspaceFolder() / "out.env"))
        self.assertTrue((self.getWorkspaceFolder() / "in.env").exists())
        self.assertTrue((self.getWorkspaceFolder() / "out.env").exists())

    def testConditionalInstall_user(self):
        self.leafProfileExec("init")

        self.leafProfileExec("create", "foo",
                             "-p" "condition")

        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-B",
                                         "condition-D",
                                         "condition-F",
                                         "condition-H",
                                         "condition"])

        self.leafPackageManagerExec("config", "--env", "FOO=BAR")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-F",
                                         "condition"])

        self.leafPackageManagerExec("config", "--env", "HELLO=PLOP")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-F",
                                         "condition"])

        self.leafPackageManagerExec("config",
                                    "--env", "FOO2=BAR2",
                                    "--env", "HELLO=wOrlD")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-E_1.0",
                                     "condition-F_1.0",
                                     "condition-G_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-E",
                                         "condition-G",
                                         "condition"])

    def testConditionalInstall_ws(self):
        self.leafProfileExec("init")

        self.leafProfileExec("create", "foo",
                             "-p" "condition")

        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-B",
                                         "condition-D",
                                         "condition-F",
                                         "condition-H",
                                         "condition"])

        self.leafProfileExec("workspace", "--env", "FOO=BAR")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-F",
                                         "condition"])

        self.leafProfileExec("workspace", "--env", "HELLO=PLOP")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-F",
                                         "condition"])

        self.leafProfileExec("workspace",
                             "--env", "FOO2=BAR2",
                             "--env", "HELLO=wOrlD")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-E_1.0",
                                     "condition-F_1.0",
                                     "condition-G_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-E",
                                         "condition-G",
                                         "condition"])

    def testConditionalInstall_pf(self):
        self.leafProfileExec("init")

        self.leafProfileExec("create", "foo",
                             "-p" "condition")

        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-B",
                                         "condition-D",
                                         "condition-F",
                                         "condition-H",
                                         "condition"])

        self.leafProfileExec("update", "--env", "FOO=BAR")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-F",
                                         "condition"])

        self.leafProfileExec("update", "--env", "HELLO=PLOP")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-F",
                                         "condition"])

        self.leafProfileExec("update",
                             "--env", "FOO2=BAR2",
                             "--env", "HELLO=wOrlD")
        self.leafProfileExec("sync", "foo")
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-E_1.0",
                                     "condition-F_1.0",
                                     "condition-G_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo", ["condition-A",
                                         "condition-C",
                                         "condition-E",
                                         "condition-G",
                                         "condition"])


@unittest.skipUnless("VERBOSE" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Verbose(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipUnless("QUIET" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Quiet(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


@unittest.skipUnless("JSON" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Json(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.jsonEnvValue = "1"


if __name__ == "__main__":
    unittest.main()
