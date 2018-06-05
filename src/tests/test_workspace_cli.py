'''
@author: seb
'''

from leaf.constants import LeafFiles
import os
import shutil
import unittest

from tests.utils import LeafCliWrapper, envFileToMap


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestProfileCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testInitWithoutProfile(self):
        self.leafExec("init")
        self.leafExec("status")
        self.leafExec("env", expectedRc=2)

    def testCreateProfile(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile", "-p", "container-A_1.0")
        self.leafExec("config:profile", "--set", "FOO=BAR")
        self.leafExec("status")
        self.checkProfileContent("foo", [])
        self.leafExec("sync")
        self.leafExec("env")

    def testWorkspaceNotInit(self):
        self.leafExec("sync", expectedRc=2)
        self.leafExec("status")

    def testConfigurePackages(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile",
                      "-p", "container-A_1.0",
                      "--package", "install_1.0")
        self.leafExec("config:profile",
                      "--set", "FOO=BAR",
                      "--set", "FOO2=BAR2")
        self.checkProfileContent("foo", [])
        self.leafExec("sync")
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E",
                                         "install"])

        self.leafExec("create", "foo", expectedRc=2)

    def testDelete(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.checkProfileContent("foo", [])
        self.leafExec("create", "foo2")
        self.checkProfileContent("foo2", [])
        self.leafExec("status")
        self.leafExec("delete", "foo2")
        self.checkProfileContent("foo", [])
        self.checkProfileContent("foo2", None)
        self.leafExec("status")

    def testReservedName(self):
        self.leafExec("init")
        self.leafExec("create", "current", expectedRc=2)
        self.leafExec("create", "", expectedRc=2)
        self.leafExec("create", "foo")
        self.leafExec("create", "foo", expectedRc=2)

    def testAutoFindWorkspace(self):
        profileConfigFile = self.getWorkspaceFolder() / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(profileConfigFile.exists())

        self.leafExec("init")
        self.assertTrue(profileConfigFile.exists())
        self.leafExec("create", "foo")
        self.leafExec("select", "foo")

        self.leafExec("status")
        self.leafExec("select", "foo",
                      altWorkspace=self.getAltWorkspaceFolder(),
                      expectedRc=2)

        subFolder = self.getWorkspaceFolder() / "foo" / "bar"
        subFolder.mkdir(parents=True)
        self.leafExec("select", "foo",
                      altWorkspace=subFolder,
                      expectedRc=2)

        oldPwd = os.getcwd()
        try:
            os.chdir(str(subFolder))
            self.leafExec("select", "foo")
        finally:
            os.chdir(oldPwd)

    def testWithoutVersion(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile", "-p", "container-A")
        self.leafExec("status")
        self.leafExec("sync")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])

    def testBootstrapWorkspace(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:p", "-p", "container-A")
        self.leafExec("sync")
        self.checkCurrentProfile("foo")
        self.leafExec("create", "bar")
        self.checkCurrentProfile("bar")
        self.leafExec("status")
        self.leafExec("env")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])
        dataFolder = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME
        self.assertTrue(dataFolder.exists())
        shutil.rmtree(str(dataFolder))
        self.assertFalse(dataFolder.exists())

        self.leafExec("status")
        self.leafExec("env", expectedRc=2)
        self.leafExec("select", "foo")
        self.checkCurrentProfile("foo")
        self.leafExec("env", expectedRc=2)
        self.leafExec("sync")
        self.leafExec("env")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])

    def testRenameProfile(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:p", "-p", "container-A")
        self.leafExec("sync")
        self.leafExec("env")

        self.leafExec("rename", "bar")
        self.leafExec("env")
        self.leafExec("env", "bar")
        self.leafExec("env", "foo", expectedRc=2)

        self.leafExec("rename", "foo")
        self.leafExec("env")
        self.leafExec("env", "foo")

    def testUpdate(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile",
                      "-p", "version_1.0",
                      "-p", "container-A_1.0")
        self.leafExec("sync")
        self.checkCurrentProfile("foo")
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E",
                                         "version"])

        self.leafExec("update", "--list")
        self.leafExec("sync")
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E",
                                         "version"])

        self.leafExec("update")
        self.leafExec("sync")
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D",
                                         "version"])

    def testEnv(self):
        self.leafExec("init")
        self.leafExec("create", "ENV-A")
        self.leafExec("config:profile", "-p", "env-A")
        self.leafExec("sync")
        self.leafExec("env", "ENV-A")
        self.leafExec("env")
        self.leafExec("env",
                      "--activate-script",
                      str(self.getWorkspaceFolder() / "in.env"),
                      "--deactivate-script",
                      str(self.getWorkspaceFolder() / "out.env"))
        self.assertTrue((self.getWorkspaceFolder() / "in.env").exists())
        self.assertTrue((self.getWorkspaceFolder() / "out.env").exists())

    def testConditionalInstall_user(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile", "-p" "condition")

        self.leafExec("sync")
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

        self.leafExec("config:profile", "--set", "FOO=BAR")
        self.leafExec("sync")
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

        self.leafExec("config:profile", "--set", "HELLO=PLOP")
        self.leafExec("sync")
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

        self.leafExec("config:profile",
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=wOrlD")
        self.leafExec("sync")
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
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile", "-p" "condition")

        self.leafExec("sync")
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

        self.leafExec("config:workspace", "--set", "FOO=BAR")
        self.leafExec("sync")
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

        self.leafExec("config:workspace", "--set", "HELLO=PLOP")
        self.leafExec("sync")
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

        self.leafExec("config:workspace",
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=wOrlD")
        self.leafExec("sync")
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
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:profile", "-p" "condition")

        self.leafExec("sync")
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

        self.leafExec("config:profile", "--set", "FOO=BAR")
        self.leafExec("sync")
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

        self.leafExec("config:profile", "--set", "HELLO=PLOP")
        self.leafExec("sync")
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

        self.leafExec("config:profile",
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=wOrlD")
        self.leafExec("sync")
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

    def testEnvSetUnsetGenScrips(self):

        self.leafExec("env:user")
        self.leafExec("env:workspace", expectedRc=2)
        self.leafExec("env:profile", expectedRc=2)
        self.leafExec("init")
        self.leafExec("env:user")
        self.leafExec("env:workspace")
        self.leafExec("env:profile", expectedRc=2)
        self.leafExec("create", "foo")
        self.leafExec("env:user")
        self.leafExec("env:workspace")
        self.leafExec("env:profile")

        for scope in ["user", "workspace", "profile", "u", "w", "p"]:
            verb = "env:%s" % scope
            self.leafExec(verb, "--set", "FOO=BAR")
            self.leafExec(verb, "--set", "HELLO=World")
            self.leafExec(verb, "--unset", "HELLO")
            self.leafExec(verb, "--set", "FOO=bar")
            self.leafExec(verb)

        self.leafExec("env", "--set FOO=BAR", expectedRc=2)
        self.leafExec("env")
        inScript = self.getWorkspaceFolder() / "in.env"
        outScript = self.getWorkspaceFolder() / "out.env"
        self.leafExec("env",
                      "--activate-script", inScript,
                      "--deactivate-script", outScript)
        self.assertTrue(inScript.exists())
        self.assertTrue(outScript.exists())

        with open(str(inScript)) as fp:
            fooCount = 0
            for line in fp.read().splitlines():
                if line == 'export FOO="bar";':
                    fooCount += 1
            self.assertEqual(3, fooCount)

        with open(str(outScript)) as fp:
            fooCount = 0
            for line in fp.read().splitlines():
                if line == 'unset FOO;':
                    fooCount += 1
            self.assertEqual(1, fooCount)

    def testInstallFromWorkspace(self):
        self.leafExec("init")
        self.leafExec("create", "foo")
        self.leafExec("config:p", "-p", "install_1.0")
        self.leafExec("sync")

        envDumpFile = self.getInstallFolder() / "install_1.0" / "dump.env"
        keys = [k for k in envFileToMap(envDumpFile).keys()
                if k.startswith("LEAF_")]
        for key in ['LEAF_NON_INTERACTIVE',
                    'LEAF_PLATFORM_MACHINE',
                    'LEAF_PLATFORM_RELEASE',
                    'LEAF_PLATFORM_SYSTEM',
                    'LEAF_WORKSPACE',
                    'LEAF_PROFILE',
                    'LEAF_VERSION']:
            self.assertTrue(key in keys, msg=key)
        print(keys)

    def testPackageOverride(self):
        self.leafExec("init")
        self.leafExec("create", "myprofile")
        self.leafExec("config:p", "-p", "container-A_1.0")
        self.leafExec("sync")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E"])

        self.leafExec("config:p", "-p", "container-E_1.1")
        self.leafExec("sync")

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0",
                                     "container-E_1.1"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E"])


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
