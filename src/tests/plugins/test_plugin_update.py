"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from tests.testutils import LeafTestCaseWithCli


class TestPluginUpdate(LeafTestCaseWithCli):
    def test_update(self):
        self.leaf_exec(("init"))
        self.leaf_exec(("profile", "create"), "myprofile")
        self.leaf_exec(("profile", "config"), "-p", "version_1.0", "-p", "container-A_1.0")
        self.leaf_exec(("profile", "sync"))

        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0", "version_1.0"])
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E", "version"])

        self.leaf_exec("update", "-p", "version_2.0")

        self.check_installed_packages(["container-A_1.0", "container-B_1.0", "container-C_1.0", "container-E_1.0", "version_1.0", "version_2.0"])
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E", "version"])

        self.leaf_exec("update", "-p", "container-A_1.1")

        self.check_installed_packages(
            ["container-A_1.0", "container-A_1.1", "container-B_1.0", "container-C_1.0", "container-E_1.0", "version_1.0", "version_2.0"]
        )
        self.check_profile_content("myprofile", ["container-A", "container-B", "container-C", "container-E", "version"])

        self.leaf_exec("update")

        self.check_installed_packages(
            [
                "container-A_1.0",
                "container-A_1.1",
                "container-A_2.1",
                "container-B_1.0",
                "container-C_1.0",
                "container-D_1.0",
                "container-E_1.0",
                "version_1.0",
                "version_2.0",
            ]
        )
        self.check_profile_content("myprofile", ["container-A", "container-C", "container-D", "version"])
