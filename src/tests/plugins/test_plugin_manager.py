"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""


from leaf.api import ConfigurationManager
from leaf.cli.plugins import LeafPluginCommand, LeafPluginManager
from leaf.core.constants import LeafSettings
from tests.testutils import TEST_LEAF_SYSTEM_ROOT, LeafTestCaseWithCli


class TestPluginManagerCli(LeafTestCaseWithCli):
    def check_commands(self, pm, cmdnames, prefix=(), ignored=None):
        prefix = ("leaf",) + prefix
        for c in pm.get_commands(prefix):
            self.assertIsInstance(c, LeafPluginCommand)
        self.assertEqual(cmdnames, list(map(lambda c: c.name, pm.get_commands(prefix, ignored_names=ignored))))

    def check_command_rc(self, pm, cmdname, rc):
        for c in pm.get_commands(()):
            if c.name == cmdname:
                self.assertEqual(rc, c.execute(None, None))
                return
        self.fail("Cannot find command " + cmdname)

    def test_builtin(self):

        cm = ConfigurationManager()

        LeafSettings.SYSTEM_PKG_FOLDERS.value = ""
        pm = LeafPluginManager({})
        self.assertEqual(0, len(pm._LeafPluginManager__plugins))

        LeafSettings.SYSTEM_PKG_FOLDERS.value = TEST_LEAF_SYSTEM_ROOT
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__plugins))
        self.check_commands(pm, ["foo", "bar"])

        self.leaf_exec(("package", "install"), "pluginA_1.0")
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        self.assertEqual(6, len(pm._LeafPluginManager__plugins))
        self.check_commands(pm, ["bar1", "foo"])

        self.leaf_exec(("package", "install"), "pluginA_1.1")
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        self.assertEqual(7, len(pm._LeafPluginManager__plugins))
        self.check_commands(pm, ["bar2", "bar3", "foo"])

        self.leaf_exec(("package", "uninstall"), "pluginA_1.1")
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        self.assertEqual(6, len(pm._LeafPluginManager__plugins))
        self.check_commands(pm, ["bar1", "foo"])

    def test_builtin_upgrade(self):

        # Initialise a system root
        system_root = self.volatile_folder / "system_root"
        LeafSettings.USER_PKG_FOLDER.value = system_root
        self.leaf_exec(("package", "install"), "pluginA_1.0")
        LeafSettings.USER_PKG_FOLDER.value = self.install_folder
        LeafSettings.SYSTEM_PKG_FOLDERS.value = system_root
        self.check_installed_packages(["pluginA_1.0"], install_folder=system_root)
        self.check_installed_packages([])

        cm = ConfigurationManager()
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        self.check_commands(pm, ["bar", "bar1"])
        self.check_command_rc(pm, "bar", 1)

        self.leaf_exec(("package", "install"), "pluginA_1.1")
        self.check_installed_packages(["pluginA_1.0"], install_folder=system_root)
        self.check_installed_packages(["pluginA_1.1"])

        cm = ConfigurationManager()
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))
        self.check_commands(pm, ["bar", "bar2", "bar3"])
        self.check_command_rc(pm, "bar", 2)

    def test_location(self):
        LeafSettings.SYSTEM_PKG_FOLDERS.value = TEST_LEAF_SYSTEM_ROOT

        cm = ConfigurationManager()
        pm = LeafPluginManager(cm.list_installed_packages(only_latest=True))

        self.assertEqual(5, len(pm._LeafPluginManager__plugins))

        self.check_commands(pm, ["foo", "bar"])
        self.check_commands(pm, ["subcommand"], prefix=("env",))
        self.check_commands(pm, ["subcommand"], prefix=("package",))
        self.check_commands(pm, ["subcommand"], prefix=("unknown",))
        self.check_commands(pm, [], prefix=("unknown",), ignored=["subcommand"])

    def test_pythonpath(self):
        self.leaf_exec(("package", "install"), "pluginB_1.0")
        with self.assertStdout(template_out="pluginB.out"):
            self.leaf_exec("a")
            self.leaf_exec("b")
            self.leaf_exec("c")
            self.leaf_exec("d")
