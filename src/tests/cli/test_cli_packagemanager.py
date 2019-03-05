"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.core.constants import LeafSettings
from tests.testutils import LeafTestCaseWithCli


class TestCliPackageManager(LeafTestCaseWithCli):
    def test_config(self):
        self.leaf_exec("config")

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

    def test_depends(self):
        self.leaf_exec(["package", "deps"], "--available", "container-A_1.0")
        self.leaf_exec(["package", "deps"], "--install", "container-A_1.0")
        self.leaf_exec(["package", "deps"], "--uninstall", "container-A_1.0")
        self.leaf_exec(["package", "deps"], "--prereq", "container-A_1.0")
        self.leaf_exec(["package", "deps"], "--installed", "container-A_1.0", expected_rc=2)
        self.leaf_exec(["package", "install"], "container-A_1.0")
        self.leaf_exec(["package", "deps"], "--installed", "container-A_1.0")

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
        self.leaf_exec(["package", "prereq"], "prereq-true_1.0")
        self.assertFalse((self.alt_ws_folder / "prereq-true_1.0").is_dir())
        self.leaf_exec(["package", "prereq"], "--target", self.alt_ws_folder, "prereq-true_1.0")
        self.assertTrue((self.alt_ws_folder / "prereq-true_1.0").is_dir())

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


class TestCliPackageManagerVerbose(TestCliPackageManager):
    @classmethod
    def setUpClass(cls):
        TestCliPackageManager.setUpClass()
        LeafSettings.VERBOSITY.value = "verbose"


class TestCliPackageManagerQuiet(TestCliPackageManager):
    @classmethod
    def setUpClass(cls):
        TestCliPackageManager.setUpClass()
        LeafSettings.VERBOSITY.value = "quiet"
