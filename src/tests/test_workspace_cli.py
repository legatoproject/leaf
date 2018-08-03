'''
@author: seb
'''

from leaf.constants import LeafFiles
import os
import shutil
import unittest

from tests.testutils import LeafCliWrapper, envFileToMap, LEAF_UT_SKIP,\
    countLines


class TestProfileCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testInitWithoutProfile(self):
        self.leafExec("init")
        self.leafExec("status")
        self.leafExec(("env", "profile"), expectedRc=2)
        self.leafExec(("env", "print"), expectedRc=2)

    def testCreateProfile(self):
        self.leafExec("init")
        self.leafExec(('profile', 'create'), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A_1.0")
        self.checkProfileContent("foo", [])
        self.leafExec(("profile", "sync"))
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E"])
        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        self.leafExec("status")
        self.leafExec(("profile", "sync"))
        self.leafExec(("env", "print"))

    def testWorkspaceNotInit(self):
        self.leafExec(("profile", "sync"), expectedRc=2)
        self.leafExec("status")

    def testConfigurePackages(self):
        self.leafExec("init")
        self.leafExec(('profile', 'create'), "foo")
        self.leafExec(("profile", "config"),
                      "-p", "container-A_1.0",
                      "--add-package", "install_1.0")
        self.leafExec(("env", "profile"),
                      "--set", "FOO=BAR",
                      "--set", "FOO2=BAR2")
        self.checkProfileContent("foo", [])
        self.leafExec(("profile", "sync"))
        self.checkProfileContent("foo", ["container-A",
                                         "container-B",
                                         "container-C",
                                         "container-E",
                                         "install"])

        self.leafExec(('profile', 'create'), "foo", expectedRc=2)

    def testDelete(self):
        self.leafExec("init")
        self.leafExec(('profile', 'create'), "foo")
        self.checkProfileContent("foo", [])
        self.leafExec(('profile', 'create'), "foo2")
        self.checkProfileContent("foo2", [])
        self.leafExec("status")
        self.leafExec(("profile", "delete"), "foo2")
        self.checkProfileContent("foo", [])
        self.checkProfileContent("foo2", None)
        self.leafExec("status")

    def testReservedName(self):
        self.leafExec("init")
        self.leafExec(('profile', 'create'), "current", expectedRc=2)
        self.leafExec(('profile', 'create'), "", expectedRc=2)
        self.leafExec(('profile', 'create'), "foo")
        self.leafExec(('profile', 'create'), "foo", expectedRc=2)

    def testAutoFindWorkspace(self):
        profileConfigFile = self.getWorkspaceFolder() / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(profileConfigFile.exists())

        self.leafExec("init")
        self.assertTrue(profileConfigFile.exists())
        self.leafExec(('profile', 'create'), "foo")
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
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A")
        self.leafExec("status")
        self.leafExec(("profile", "sync"))
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])

    def testBootstrapWorkspace(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A")
        self.leafExec(("profile", "sync"))
        self.checkCurrentProfile("foo")
        self.leafExec(("profile", "create"), "bar")
        self.checkCurrentProfile("bar")
        self.leafExec("status")
        self.leafExec(("env", "print"))
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])
        dataFolder = self.getWorkspaceFolder() / LeafFiles.WS_DATA_FOLDERNAME
        self.assertTrue(dataFolder.exists())
        shutil.rmtree(str(dataFolder))
        self.assertFalse(dataFolder.exists())

        self.leafExec("status")
        self.leafExec(("env", "print"), expectedRc=2)
        self.leafExec(("profile", "switch"), "foo")
        self.checkCurrentProfile("foo")
        self.leafExec(("env", "print"), expectedRc=2)
        self.leafExec(("profile", "sync"))
        self.leafExec(("env", "print"))
        self.checkProfileContent("foo", ["container-A",
                                         "container-C",
                                         "container-D"])

    def testRenameProfile(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A")
        self.leafExec(("profile", "sync"))
        self.leafExec(("env", "print"))

        self.leafExec(("profile", "rename"), "bar")
        self.leafExec(("env", "profile"))
        self.leafExec(("env", "profile"), "bar")
        self.leafExec(("env", "profile"), "foo", expectedRc=2)

        self.leafExec(("profile", "rename"), "foo")
        self.leafExec(("env", "profile"))
        self.leafExec(("env", "profile"), "foo")

    def testEnv(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "ENV-A")
        self.leafExec(("profile", "config"), "-p", "env-A")
        self.leafExec(("profile", "sync"))
        self.leafExec(("env", "profile"), "ENV-A")
        self.leafExec(("env", "profile"))
        self.leafExec(("env", "profile"),
                      "--activate-script",
                      str(self.getWorkspaceFolder() / "in.env"),
                      "--deactivate-script",
                      str(self.getWorkspaceFolder() / "out.env"))
        self.assertTrue((self.getWorkspaceFolder() / "in.env").exists())
        self.assertTrue((self.getWorkspaceFolder() / "out.env").exists())

    def testConditionalInstall_user(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p" "condition")

        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "profile"), "--set", "HELLO=PLOP")
        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "profile"),
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=wOrlD")
        self.leafExec(("profile", "sync"))
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
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p" "condition")

        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "workspace"), "--set", "FOO=BAR")
        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "workspace"), "--set", "HELLO=PLOP")
        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "workspace"),
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=wOrlD")
        self.leafExec(("profile", "sync"))
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
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p" "condition")

        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "profile"), "--set", "HELLO=PLOP")
        self.leafExec(("profile", "sync"))
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

        self.leafExec(("env", "profile"),
                      "--set", "FOO2=BAR2",
                      "--set", "HELLO=wOrlD")
        self.leafExec(("profile", "sync"))
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

    def testEnvSetUnsetGenScripts(self):

        self.leafExec(("env", "user"))
        self.leafExec(("env", "workspace"), expectedRc=2)
        self.leafExec(("env", "profile"), expectedRc=2)
        self.leafExec("init")
        self.leafExec(("env", "user"))
        self.leafExec(("env", "workspace"))
        self.leafExec(("env", "profile"), expectedRc=2)
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("env", "user"))
        self.leafExec(("env", "workspace"))
        self.leafExec(("env", "profile"))

        for scope in ["user", "workspace", "profile"]:
            verb = ("env", scope)
            self.leafExec(verb, "--set", "FOO=BAR")
            self.leafExec(verb, "--set", "HELLO=World")
            self.leafExec(verb, "--unset", "HELLO")
            self.leafExec(verb, "--set", "FOO=bar")
            self.leafExec(verb)

        self.leafExec(("env", "profile"), "--set FOO=BAR", expectedRc=2)
        self.leafExec(("env", "profile"))
        inScript = self.getWorkspaceFolder() / "in.env"
        outScript = self.getWorkspaceFolder() / "out.env"
        self.leafExec(("env", "print"),
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
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "install_1.0")
        self.leafExec(("profile", "sync"))

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
        self.leafExec(("profile", "create"), "myprofile")
        self.leafExec(("profile", "config"), "-p", "container-A_1.0")
        self.leafExec(("profile", "sync"))

        self.checkInstalledPackages(["container-A_1.0",
                                     "container-B_1.0",
                                     "container-C_1.0",
                                     "container-E_1.0"])
        self.checkProfileContent("myprofile",
                                 ["container-A",
                                  "container-B",
                                  "container-C",
                                  "container-E"])

        self.leafExec(("profile", "config"), "-p", "container-E_1.1")
        self.leafExec(("profile", "sync"))

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

    def testOverideKeepDepends(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "condition_1.0")
        self.leafExec(("profile", "sync"))
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-B_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo",
                                 ["condition",
                                  "condition-B",
                                  "condition-D",
                                  "condition-F",
                                  "condition-H"])

        self.leafExec(("profile", "config"), "-p", "condition-A_2.0")
        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        self.leafExec(("profile", "sync"))
        self.checkInstalledPackages(["condition_1.0",
                                     "condition-A_1.0",
                                     "condition-A_2.0",
                                     "condition-B_1.0",
                                     "condition-C_1.0",
                                     "condition-D_1.0",
                                     "condition-F_1.0",
                                     "condition-H_1.0"])
        self.checkProfileContent("foo",
                                 ["condition",
                                  "condition-A",
                                  "condition-C",
                                  "condition-F"])

    def testFeatures(self):
        self.leafExec(("feature", "list"))
        self.leafExec(("feature", "query"), "featureWithDups")
        self.leafExec(("feature", "toggle"),
                      "--user", "featureWithDups", "enum1")
        self.leafExec(("feature", "toggle"),
                      "--workspace", "featureWithDups", "enum1", expectedRc=2)
        self.leafExec(("feature", "toggle"),
                      "--profile", "featureWithDups", "enum1", expectedRc=2)

        self.leafExec(("init"))
        self.leafExec(("feature", "toggle"),
                      "--user", "featureWithDups", "enum1")
        self.leafExec(("feature", "toggle"),
                      "--workspace", "featureWithDups", "enum1")
        self.leafExec(("feature", "toggle"),
                      "--profile", "featureWithDups", "enum1", expectedRc=2)

        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("feature", "toggle"),
                      "--user", "featureWithDups", "enum1")
        self.leafExec(("feature", "toggle"),
                      "--workspace", "featureWithDups", "enum1")
        self.leafExec(("feature", "toggle"),
                      "--profile", "featureWithDups", "enum1")

    def testSync(self):
        syncFile = self.getInstallFolder() / "sync_1.0" / "sync.log"
        self.assertFalse(syncFile.exists())

        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "sync_1.0")
        self.leafExec(("profile", "sync"))
        self.assertEqual(1, countLines(syncFile))

        self.leafExec(("profile", "sync"))
        self.assertEqual(2, countLines(syncFile))

        self.leafExec(("package", "sync"), "sync_1.0")
        self.assertEqual(3, countLines(syncFile))


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestProfileCli_Verbose(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestProfileCli_Quiet(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


if __name__ == "__main__":
    unittest.main()
