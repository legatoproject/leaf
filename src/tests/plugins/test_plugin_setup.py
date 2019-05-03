"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.core.constants import LeafFiles, LeafSettings
from tests.testutils import LeafTestCaseWithCli, LEAF_SYSTEM_ROOT


class TestPluginSetup(LeafTestCaseWithCli):
    def setUp(self):
        super().setUp()
        LeafSettings.SYSTEM_PKG_FOLDERS.value = LEAF_SYSTEM_ROOT

    def test_setup_ws_creation(self):
        ws_config_file = self.workspace_folder / LeafFiles.WS_CONFIG_FILENAME
        self.assertFalse(ws_config_file.is_file())
        self.leaf_exec("setup", "-p", "container-A")
        self.assertTrue(ws_config_file.is_file())

    def test_setup_profile_already_exist(self):
        self.leaf_exec("setup", "foo", "-p", "container-A")
        self.leaf_exec("setup", "foo", "-p", "container-A", expected_rc=2)

    def test_setup_with_package_identifier(self):
        self.leaf_exec("setup", "A", "-p", "container-A_1.0")
        self.check_current_profile("A")
        self.check_profile_content("A", ["container-A", "container-B", "container-C", "container-E"])

        self.leaf_exec("setup", "B", "-p", "container-A_2.0")
        self.check_current_profile("B")
        self.check_profile_content("B", ["container-A", "container-C", "container-D"])

    def test_setup_with_package_name(self):
        self.leaf_exec("setup", "A", "-p", "container-A")
        self.check_current_profile("A")
        self.check_profile_content("A", ["container-A", "container-C", "container-D"])

    def test_setup_profile_content(self):
        self.leaf_exec("setup", "foo1", "-p", "condition")
        self.check_current_profile("foo1")
        self.check_profile_content("foo1", ["condition-B", "condition-D", "condition-F", "condition-H", "condition"])

        self.leaf_exec("setup", "foo2", "--set", "FOO=BAR", "-p", "condition")
        self.check_current_profile("foo2")
        self.check_profile_content("foo2", ["condition-A", "condition-C", "condition-F", "condition"])

        self.leaf_exec("setup", "foo3", "--set", "FOO=BAR", "--set", "FOO2=BAR2", "--set", "HELLO=WorLD", "-p", "condition")
        self.check_current_profile("foo3")
        self.check_profile_content("foo3", ["condition-A", "condition-C", "condition-E", "condition-G", "condition"])

        self.leaf_exec("setup", "foo4", "--set", "FOO=BAR", "--set", "FOO2=BAR2", "--set", "HELLO=WorLD", "-p", "condition", "-p", "install")
        self.check_current_profile("foo4")
        self.check_profile_content("foo4", ["condition-A", "condition-C", "condition-E", "condition-G", "condition", "install"])


class TestPluginSetupVerbose(TestPluginSetup):
    def __init__(self, *args, **kwargs):
        TestPluginSetup.__init__(self, *args, verbosity="verbose", **kwargs)


class TestPluginSetupQuiet(TestPluginSetup):
    def __init__(self, *args, **kwargs):
        TestPluginSetup.__init__(self, *args, verbosity="quiet", **kwargs)
