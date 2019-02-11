'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from leaf.rendering.ansi import ANSI
from tests.testutils import LeafTestCaseWithCli


class TestCliRendering(LeafTestCaseWithCli):

    def testManifest(self):
        self.leafExec(["package", "install"], "container-A_2.1")
        with self.assertStdout(templateOut="search_all.out"):
            self.leafExec("search", "-a", "container-A")
        with self.assertStdout(templateOut="package_list.out"):
            self.leafExec(["package", "list"])
            self.leafExec(["package", "list"], "--all")

    def testRemote(self):
        self.leafExec(["remote", "add"], "alt",
                      self.getRemoteUrl(), "--insecure")
        self.leafExec(["remote", "disable"], "alt")
        with self.assertStdout(templateOut="remote_list.out"):
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
        with self.assertStdout(templateOut="env.out"):
            self.leafExec(("env", "print"))
            self.leafExec(("env", "user"), "--set", "UNKNWONVAR=TOTO")
            self.leafExec(("env", "workspace"), "--set", "FOO=BAR")
            self.leafExec(("env", "workspace"), "--set", "HELLO=PLOP")
            self.leafExec(("env", "workspace"),
                          "--set", "FOO2=BAR2",
                          "--set", "HELLO=wOrlD")
            self.leafExec(["env", "package"], "env-A_1.0")
            self.leafExec(["env", "package"], "--nodeps", "env-A_1.0")
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
        with self.assertStdout(templateOut="status.out"):
            self.leafExec("status")

    def testProfile(self):
        self.leafExec("init")
        self.leafExec(("profile", "create"), "foo")
        self.leafExec(("profile", "config"), "-p", "container-A_1.0")
        self.leafExec(("env", "profile"), "--set", "FOO=BAR")
        with self.assertStdout(templateOut="profile_list.out"):
            self.leafExec(("profile", "list"))

    def testFeature(self):
        with self.assertStdout(templateOut="feature_list.out"):
            self.leafExec(("feature", "list"))


class TestCliRenderingVerbose(TestCliRendering):

    def __init__(self, *args, **kwargs):
        TestCliRendering.__init__(
            self, *args, verbosity="verbose", **kwargs)


class TestCliRenderingQuiet(TestCliRendering):

    def __init__(self, *args, **kwargs):
        TestCliRendering.__init__(
            self, *args, verbosity="quiet", **kwargs)


class TestCliRenderingAnsi(TestCliRendering):

    @classmethod
    def setUpClass(cls):
        ANSI.force = True
        TestCliRendering.setUpClass()

    @classmethod
    def tearDownClass(cls):
        TestCliRendering.tearDownClass()
        ANSI.force = False


class TestCliRenderingAnsiVerbose(TestCliRenderingAnsi):

    def __init__(self, *args, **kwargs):
        TestCliRenderingAnsi.__init__(
            self, *args, verbosity="verbose", **kwargs)


class TestCliRenderingAnsiQuiet(TestCliRenderingAnsi):

    def __init__(self, *args, **kwargs):
        TestCliRenderingAnsi.__init__(
            self, *args, verbosity="quiet", **kwargs)
