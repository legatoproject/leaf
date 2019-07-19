"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""
import os

from leaf.core.constants import LeafSettings
from tests.testutils import LeafTestCaseWithCli, get_lines


class TestCliPackageManager(LeafTestCaseWithCli):
    def test_config(self):
        with self.assertStdout(template_out="config.out"):
            self.leaf_exec(("config", "list"), "leaf.root")
        with self.assertStdout(template_out="config2.out"):
            self.leaf_exec(("config", "list"), "download")

    def test_remote(self):
        self.leaf_exec(("remote", "list"))

        self.leaf_exec(["remote", "add"], "--insecure", "alt", self.remote_url1)
        self.leaf_exec(["remote", "add"], "--insecure", "alt", self.remote_url1, expected_rc=2)

        self.leaf_exec(["remote", "disable"], "alt")
        self.leaf_exec(["remote", "enable"], "alt")

        self.leaf_exec(["remote", "remove"], "alt")
        self.leaf_exec(["remote", "remove"], "alt", expected_rc=2)
        self.leaf_exec(["remote", "enable"], "alt", expected_rc=2)

        self.leaf_exec(["remote", "add"], "--insecure", "remote1", self.remote_url1)

        self.leaf_exec(["remote", "add"], "--insecure", "remote2", self.remote_url1)

        self.leaf_exec(["remote", "add"], "--insecure", "remote3", self.remote_url1)

        self.leaf_exec(["remote", "disable"], "remote1", "remote2", "remote3")

        self.leaf_exec(["remote", "enable"], "remote1", "remote2", "remote3")

        self.leaf_exec(["remote", "remove"], "remote1", "remote2")

        self.leaf_exec(["remote", "enable"], "remote1", "remote2", expected_rc=2)

        self.leaf_exec(["remote", "enable"], "remote3")

    def test_search(self):
        self.leaf_exec("search")
        self.leaf_exec("search", "--all")
        self.leaf_exec("search", "--tag", "tag1")
        self.leaf_exec("search", "--tag", "tag1", "-t", "tag2")
        self.leaf_exec("search", "--tag", "tag1,tag2")
        self.leaf_exec("search", "--tag", "tag1,tag2" "keyword1")
        self.leaf_exec("search", "--tag", "tag1,tag2" "keyword1", "keyword2")
        self.leaf_exec("search", "--tag", "tag1,tag2" "keyword1,keyword2")

    def test_depends_available(self):
        self.leaf_exec(["remote", "fetch"])

        with self.assertStdout("a.out"):
            self.leaf_exec(["package", "deps"], "--available", "condition_1.0")

        with self.assertStdout("b.out"):
            self.leaf_exec(["package", "deps"], "--available", "condition_1.0", "--env", "HELLO=WORLD")

    def test_depends_install(self):
        self.leaf_exec(["remote", "fetch"])

        with self.assertStdout("a.out"):
            self.leaf_exec(["package", "deps"], "--install", "condition_1.0")

        with self.assertStdout("b.out"):
            self.leaf_exec(["package", "deps"], "--install", "condition_1.0", "--env", "HELLO=WORLD")

        self.leaf_exec(["package", "install"], "condition-A_1.0")

        with self.assertStdout("c.out"):
            self.leaf_exec(["package", "deps"], "--install", "condition_1.0")

    def test_depends_installed(self):
        self.leaf_exec(["remote", "fetch"])

        with self.assertStdout("a.out"):
            self.leaf_exec(["package", "deps"], "--installed", "condition_1.0")

        self.leaf_exec(["package", "install"], "condition_1.0")

        with self.assertStdout("b.out"):
            self.leaf_exec(["package", "deps"], "--installed", "condition_1.0")

    def test_depends_prereq(self):
        self.leaf_exec(["remote", "fetch"])

        with self.assertStdout("a.out"):
            self.leaf_exec(["package", "deps"], "--prereq", "prereq-A_1.0")

    def test_depends_uninstall(self):
        self.leaf_exec(["remote", "fetch"])

        with self.assertStdout("a.out"):
            self.leaf_exec(["package", "deps"], "--uninstall", "condition_1.0")

        self.leaf_exec(["package", "install"], "condition_1.0")

        with self.assertStdout("b.out"):
            self.leaf_exec(["package", "deps"], "--uninstall", "condition_1.0")

    def test_depends_rdepends(self):
        self.leaf_exec(["remote", "fetch"])

        with self.assertStdout("a.out"):
            self.leaf_exec(["package", "deps"], "--rdepends", "condition-A_1.0")

        with self.assertStdout("b.out"):
            self.leaf_exec(["package", "deps"], "--rdepends", "condition-A_1.0", "--env", "HELLO=WORLD")

    def test_install(self):
        self.leaf_exec(["package", "install"], "container-A_2.1")
        self.leaf_exec(["package", "list"])
        self.leaf_exec(["package", "list"], "--all")
        self.check_installed_packages(["container-A_2.1", "container-C_1.0", "container-D_1.0"])

    def test_env(self):
        self.leaf_exec(("env", "user"), "--unset", "UNKNWONVAR")
        self.leaf_exec(("env", "user"), "--set", "UNKNWONVAR=TOTO")
        self.leaf_exec(("env", "user"), "--unset", "UNKNWONVAR")

        self.leaf_exec(["package", "install"], "env-A_1.0")
        self.leaf_exec(["env", "package"], "env-A_1.0")

    def test_install_with_steps(self):
        self.leaf_exec(["package", "install"], "install_1.0")
        self.check_installed_packages(["install_1.0"])

    def test_install_uninstall_keep(self):
        self.leaf_exec(["package", "install"], "container-A_1.0")
        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0"])
        self.leaf_exec(["package", "install"], "container-A_2.0")
        self.check_installed_packages(["container-A_1.0", "container-A_2.0", "container-B_1.0", "container-C_1.0", "container-D_1.0", "container-C_1.0"])
        self.leaf_exec(["package", "uninstall"], "container-A_1.0")
        self.check_installed_packages(["container-A_2.0", "container-C_1.0", "container-D_1.0"])

    def test_conditional_install(self):
        self.leaf_exec(["package", "install"], "condition_1.0")
        self.check_installed_packages(["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0"])

        self.leaf_exec(["package", "uninstall"], "condition_1.0")
        self.check_installed_packages([])

        self.leaf_exec(["env", "user"], "--set", "FOO=BAR")
        self.leaf_exec(["package", "install"], "condition_1.0")
        self.check_installed_packages(["condition_1.0", "condition-A_1.0", "condition-C_1.0", "condition-F_1.0"])

        self.leaf_exec(["package", "uninstall"], "condition_1.0")
        self.check_installed_packages([])

        self.leaf_exec(["env", "user"], "--set", "FOO2=BAR2", "--set", "HELLO=WorlD")
        self.leaf_exec(["package", "install"], "condition_1.0")
        self.check_installed_packages(["condition_1.0", "condition-A_1.0", "condition-C_1.0", "condition-E_1.0", "condition-G_1.0"])

        self.leaf_exec(["package", "uninstall"], "condition_1.0")
        self.check_installed_packages([])

    def test_conditional_uninstall(self):
        self.leaf_exec(["env", "user"], "--set", "FOO=BAR")
        self.leaf_exec(["package", "install"], "condition_1.0")
        self.leaf_exec(["env", "user"], "--unset", "FOO")
        self.leaf_exec(["package", "install"], "install_1.0")
        # condition_1.0 is not 'consistent' since env has changed
        self.leaf_exec(["package", "uninstall"], "install_1.0")

    def test_prereq(self):
        self.leaf_exec(["package", "install"], "pkg-with-prereq_0.1", expected_rc=2)
        self.leaf_exec(["package", "install"], "pkg-with-prereq_1.0")
        self.leaf_exec(["package", "install"], "pkg-with-prereq_2.0")

        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_0.1-fail" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_0.1-fail" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-A_1.0" / "install.log")))
        self.assertEqual(2, len(get_lines(self.install_folder / "prereq-A_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_1.0" / "sync.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_2.0" / "install.log")))
        self.assertEqual(1, len(get_lines(self.install_folder / "prereq-B_2.0" / "sync.log")))

    def test_install_unknown_package(self):
        self.leaf_exec(["package", "install"], "unknwonPackage", expected_rc=2)
        self.leaf_exec(["package", "install"], "container-A", expected_rc=2)

    def test_upgrade(self):
        self.leaf_exec(["remote", "disable"], "other")

        self.leaf_exec(["package", "install"], "upgrade_1.0")
        self.check_installed_packages(["upgrade_1.0"])

        self.leaf_exec(["package", "upgrade"])
        self.check_installed_packages(["upgrade_1.0"])

        self.leaf_exec(["package", "upgrade"], "upgrade")
        self.check_installed_packages(["upgrade_1.0", "upgrade_1.1"])

        self.leaf_exec(["remote", "enable"], "other")

        self.leaf_exec(["package", "upgrade"], "--clean")
        self.check_installed_packages(["upgrade_1.0", "upgrade_2.0"])

    def test_free_space_issue(self):
        self.leaf_exec(["package", "install"], "failure-large-ap_1.0", expected_rc=2)
        self.leaf_exec(["package", "install"], "failure-large-extracted_1.0", expected_rc=2)

    def test_legacy_config_root(self):
        # Test to be removed when legacy *leaf config --root* CLI is removed
        with self.assertStdout("test.out"):
            self.leaf_exec(["config", "get"], "leaf.user.root")
            LeafSettings.USER_PKG_FOLDER.value = None
            self.leaf_exec(["config", "get"], "leaf.user.root")
            self.leaf_exec(["config"], "--root", self.workspace_folder)
            self.leaf_exec(["config", "get"], "leaf.user.root")

    def test_env_scripts(self):
        try:
            in_script = self.volatile_folder / "in.sh"
            out_script = self.volatile_folder / "out.sh"

            self.leaf_exec(["config", "set"], "leaf.download.retry", "42")
            self.leaf_exec(["env", "user"], "--set", "LANG=D")
            self.leaf_exec(["env", "print"], "--activate-script", in_script, "--deactivate-script", out_script)

            self.assertFileContentEquals(in_script, "env.in", variables={"{LANG}": os.environ["LANG"]})
            self.assertFileContentEquals(out_script, "env.out", variables={"{LANG}": os.environ["LANG"]})
        finally:
            # Prevent leaf config leaf.download.retry from appearing in other tests
            if "LEAF_RETRY" in os.environ:
                del os.environ["LEAF_RETRY"]

    def test_local_install(self):
        file1 = self.repository_folder / "condition_1.0.leaf"
        file2 = self.repository_folder / "condition-B_1.0.leaf"
        self.leaf_exec(["package", "install"], file1, "install_1.0", file2)
        self.check_installed_packages(["condition_1.0", "condition-B_1.0", "condition-D_1.0", "condition-F_1.0", "condition-H_1.0", "install_1.0"])
        cached_filenames = [f.name[8:] for f in (self.cache_folder / "files").iterdir()]
        self.assertEqual(sorted(cached_filenames), ["condition-D_1.0.leaf", "condition-F_1.0.leaf", "condition-H_1.0.leaf", "install_1.0.leaf"])


class TestCliPackageManagerVerbose(TestCliPackageManager):
    def __init__(self, *args, **kwargs):
        TestCliPackageManager.__init__(self, *args, verbosity="verbose", **kwargs)


class TestCliPackageManagerQuiet(TestCliPackageManager):
    def __init__(self, *args, **kwargs):
        TestCliPackageManager.__init__(self, *args, verbosity="quiet", **kwargs)
