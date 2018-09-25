'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import platform
import unittest

from leaf import __version__
from tests.testutils import AbstractTestWithRepo, LEAF_UT_SKIP, \
    LeafCliWrapper


class TestRenderingCli_Default(LeafCliWrapper):

    def __init__(self, methodName):
        LeafCliWrapper.__init__(self, methodName)

    def testManifest(self):
        self.leafExec(["package", "install"], "container-A_2.1")
        with self.assertStdout(
                templateOut="search_all.out",
                variables={
                    "{REMOTE_URL}": self.getRemoteUrl(),
                    "{REMOTE_URL2}": self.getRemoteUrl2()}):
            self.leafExec("search", "-a", "container-A")
        with self.assertStdout(
                templateOut="package_list.out",
                variables={"{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER}):
            self.leafExec(["package", "list"])
            self.leafExec(["package", "list"], "--all")

    def testRemote(self):
        self.leafExec(["remote", "add"], "alt",
                      self.getRemoteUrl(), "--insecure")
        self.leafExec(["remote", "disable"], "alt")
        with self.assertStdout(
                templateOut="remote_list.out",
                variables={
                    "{REMOTE_URL}": self.getRemoteUrl(),
                    "{REMOTE_URL2}": self.getRemoteUrl2()}):
            self.leafExec(("remote", "list"))

    def testEnvironment(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A")
        self.leafExec(("profile", "config"),
                      "-p", "container-A_1.0",
                      "--add-package", "install_1.0")
        self.leafExec(("profile", "sync"))
        self.leafExec(("profile", "create"), "bar")
        self.leafExec(["package", "install"], "env-A_1.0")
        with self.assertStdout(
                templateOut="env.out",
                variables={"{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER,
                           "{LEAF_VERSION}": __version__,
                           "{PLATFORM_SYSTEM}": platform.system(),
                           "{PLATFORM_MACHINE}": platform.machine(),
                           "{PLATFORM_RELEASE}": platform.release()}):
            self.leafExec(("env", "print"))
            self.leafExec(("env", "user"), "--set", "UNKNWONVAR=TOTO")
            self.leafExec(("env", "workspace"), "--set", "FOO=BAR")
            self.leafExec(("env", "workspace"), "--set", "HELLO=PLOP")
            self.leafExec(("env", "workspace"),
                          "--set", "FOO2=BAR2",
                          "--set", "HELLO=wOrlD")
            self.leafExec(["env", "package"], "env-A_1.0")
            self.leafExec(["env", "builtin"])
            self.leafExec(("env", "profile"),
                          "--set", "FOO=BAR",
                          "--set", "FOO2=BAR2")

    def testWorkspace(self):
        self.leafExec("init")
        self.leafExec(('profile', 'create'), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A_1.0")
        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        self.leafExec(("profile", "sync"))
        with self.assertStdout(
                templateOut="status.out",
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER}):
            self.leafExec("status")

    def testProfile(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A_1.0")
        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        with self.assertStdout(
                templateOut="profile_list.out",
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER}):
            self.leafExec(("profile", "list"))

    def testFeature(self):
        with self.assertStdout(
                templateOut="feature_list.out",
                variables={
                    "{ROOT_FOLDER}": AbstractTestWithRepo.ROOT_FOLDER}):
            self.leafExec(("feature", "list"))


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestRenderingCli_Verbose(TestRenderingCli_Default):
    def __init__(self, methodName):
        TestRenderingCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestRenderingCli_Quiet(TestRenderingCli_Default):
    def __init__(self, methodName):
        TestRenderingCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")
