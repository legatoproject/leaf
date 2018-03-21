'''
@author: seb
'''

from leaf.constants import LeafFiles
import os
import unittest

from tests.utils import TestWithRepository, LeafCliWrapper


LEAF_UT_LEVELS = os.environ.get("LEAF_UT_LEVELS", "QUIET,VERBOSE,JSON")


class TestProfileCli_Default(TestWithRepository, LeafCliWrapper):

    def __init__(self, methodName):
        TestWithRepository.__init__(self, methodName)
        LeafCliWrapper.__init__(self)

    def setUp(self):
        TestWithRepository.setUp(self)
        self.initLeafConfig(TestWithRepository.CONFIG_FILE)

    def checkProfileContent(self, profileName, *content):
        pfFolder = self.getWorkspaceFolder() / LeafFiles.PROFILES_FOLDERNAME / profileName
        self.assertTrue(pfFolder.exists())
        symlinkCount = 0
        for item in pfFolder.iterdir():
            if item.is_symlink():
                symlinkCount += 1
            self.assertTrue(item.name in content, "Unexpected link %s" % item)
        self.assertEqual(symlinkCount, len(content))

    def leafProfileExec(self, subCommand, *args, **kwargs):
        fullargs = ["--workspace", self.getWorkspaceFolder()]
        fullargs += args
        self.leafExec(["profile", subCommand], *fullargs, **kwargs)

    def testInit(self):
        self.leafProfileExec("list", expectedRc=2)
        self.leafProfileExec("init")
        self.leafProfileExec("list")
        self.leafProfileExec("env")

    def testInitWithEnv(self):
        self.leafProfileExec("init",
                             "-e", "FOO=BAR",
                             "-e", "FOO2=BAR2")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.checkProfileContent("default")

    def testInitWithPackages(self):
        self.leafExec("refresh")
        self.leafProfileExec("init",
                             "-e", "FOO=BAR",
                             "-e", "FOO2=BAR2",
                             "-p", "container-A_1.0",
                             "-p", "deb_1.0")
        self.leafProfileExec("list")
        self.leafProfileExec("env")
        self.checkProfileContent("default",
                                 "container-A",
                                 "container-B",
                                 "container-C",
                                 "container-E",
                                 "deb")

    def testCreate(self):
        self.leafExec("refresh")
        self.leafProfileExec("init")
        self.leafProfileExec("create", "foo",
                             "-p", "container-A_1.0",
                             "-p", "deb_1.0",
                             "-e", "FOO=BAR",
                             "-e", "FOO2=BAR2")
        self.leafProfileExec("switch", "foo")
        self.checkProfileContent("foo",
                                 "container-A",
                                 "container-B",
                                 "container-C",
                                 "container-E",
                                 "deb")
        self.leafProfileExec("list")
        self.leafProfileExec("update", "foo",
                             "-p", "container-A",
                             "-e", "FOO3=BAR3")
        self.leafProfileExec("switch")
        self.leafProfileExec("env", "foo")
        self.checkProfileContent("foo",
                                 "container-A",
                                 "container-C",
                                 "container-D",
                                 "deb")
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

    def testAutoFindWorkspace(self):
        profileConfigFile = self.getWorkspaceFolder() / LeafFiles.PROFILES_FILENAME
        self.assertFalse(profileConfigFile.exists())
        self.leafExec(("profile", "init"),
                      "--workspace",
                      self.getWorkspaceFolder())
        self.assertTrue(profileConfigFile.exists())

        self.leafExec(("profile", "list"),
                      "--workspace",
                      self.getWorkspaceFolder())

        self.leafExec(("profile", "list"),
                      "--workspace",
                      "/tmp", expectedRc=2)

        subFolder = self.getWorkspaceFolder() / "foo" / "bar"
        subFolder.mkdir(parents=True)

        self.leafExec(("profile", "list"),
                      "--workspace",
                      subFolder, expectedRc=2)

        oldPwd = os.getcwd()
        try:
            os.chdir(str(subFolder))
            self.leafExec(("profile", "list"))
        finally:
            os.chdir(oldPwd)

    def testWithoutVersion(self):
        self.leafExec("refresh")
        self.leafProfileExec("init", "-p", "container-A")
        self.leafProfileExec("list")
        self.checkProfileContent("default",
                                 "container-A",
                                 "container-C",
                                 "container-D")


@unittest.skipUnless("VERBOSE" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Verbose(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.postCommandArgs.append("--verbose")


@unittest.skipUnless("QUIET" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Quiet(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.postCommandArgs.append("--quiet")


@unittest.skipUnless("JSON" in LEAF_UT_LEVELS, "Test disabled")
class TestProfileCli_Json(TestProfileCli_Default):
    def __init__(self, methodName):
        TestProfileCli_Default.__init__(self, methodName)
        self.preCommandArgs.append("--json")


if __name__ == "__main__":
    unittest.main()
