"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.rendering.ansi import ANSI
from tests.testutils import LeafTestCaseWithCli


class TestCliRendering(LeafTestCaseWithCli):
    def test_manifest(self):
        self.leaf_exec(["package", "install"], "container-A_2.1")
        with self.assertStdout(template_out="search_all.out"):
            self.leaf_exec("search", "-a", "container-A")
        with self.assertStdout(template_out="package_list.out"):
            self.leaf_exec(["package", "list"])
            self.leaf_exec(["package", "list"], "--all")

    def test_remote(self):
        self.leaf_exec(["remote", "add"], "alt", self.remote_url1, "--insecure")
        self.leaf_exec(["remote", "disable"], "alt")
        with self.assertStdout(template_out="remote_list.out"):
            self.leaf_exec(("remote", "list"))

    def test_environment(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A")
        self.leaf_exec(("profile", "config"), "-p", "container-A_1.0", "--add-package", "install_1.0")
        self.leaf_exec(("profile", "sync"))
        self.leaf_exec(("profile", "create"), "bar")
        self.leaf_exec(["package", "install"], "env-A_1.0")
        with self.assertStdout(template_out="env.out"):
            self.leaf_exec(("env", "print"))
            self.leaf_exec(("env", "user"), "--set", "UNKNWONVAR=TOTO")
            self.leaf_exec(("env", "workspace"), "--set", "FOO=BAR")
            self.leaf_exec(("env", "workspace"), "--set", "HELLO=PLOP")
            self.leaf_exec(("env", "workspace"), "--set", "FOO2=BAR2", "--set", "HELLO=wOrlD")
            self.leaf_exec(["env", "package"], "env-A_1.0")
            self.leaf_exec(["env", "package"], "--nodeps", "env-A_1.0")
            self.leaf_exec(["env", "builtin"])
            self.leaf_exec(("env", "profile"), "--set", "FOO=BAR", "--set", "FOO2=BAR2")

    def test_workspace(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A_1.0")
        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR")
        self.leaf_exec(("profile", "sync"))
        with self.assertStdout(template_out="status.out"):
            self.leaf_exec("status")

    def test_profile(self):
        self.leaf_exec("init")
        self.leaf_exec(("profile", "create"), "foo")
        self.leaf_exec(("profile", "config"), "-p", "container-A_1.0")
        self.leaf_exec(("env", "profile"), "--set", "FOO=BAR")
        with self.assertStdout(template_out="profile_list.out"):
            self.leaf_exec(("profile", "list"))

    def test_settings(self):
        with self.assertStdout(template_out="config_list.out"):
            self.leaf_exec(("config", "list", "leaf.download"))
        with self.assertStdout(template_out="config_get.out"):
            self.leaf_exec(("config", "get", "leaf.root", "leaf.cache"))


class TestCliRenderingVerbose(TestCliRendering):
    def __init__(self, *args, **kwargs):
        TestCliRendering.__init__(self, *args, verbosity="verbose", **kwargs)


class TestCliRenderingQuiet(TestCliRendering):
    def __init__(self, *args, **kwargs):
        TestCliRendering.__init__(self, *args, verbosity="quiet", **kwargs)


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
        TestCliRenderingAnsi.__init__(self, *args, verbosity="verbose", **kwargs)


class TestCliRenderingAnsiQuiet(TestCliRenderingAnsi):
    def __init__(self, *args, **kwargs):
        TestCliRenderingAnsi.__init__(self, *args, verbosity="quiet", **kwargs)
