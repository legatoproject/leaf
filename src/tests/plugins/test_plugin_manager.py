"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from pathlib import Path

from leaf.api import ConfigurationManager
from leaf.cli.plugins import LeafPluginCommand, LeafPluginManager
from tests.testutils import TEST_RESOURCE_FOLDER, LeafTestCaseWithCli


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

        builtin_folder = TEST_RESOURCE_FOLDER / "__plugins"
        self.assertTrue(builtin_folder.is_dir())

        cm = ConfigurationManager()
        pm = LeafPluginManager()

        self.assertEqual(0, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(0, len(pm._LeafPluginManager__user_plugins))

        pm.load_builtin_plugins(cm._list_installed_packages(builtin_folder, only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(0, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["foo", "bar"])

        pm.load_user_plugins(cm._list_installed_packages(Path("/unknownFolder/"), only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(0, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["foo", "bar"])

        pm.load_user_plugins(cm._list_installed_packages(self.install_folder, only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(0, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["foo", "bar"])
        self.assertEqual(0, pm.get_commands(())[1].execute(None, None))

        self.leaf_exec(("package", "install"), "pluginA_1.0")
        pm.load_user_plugins(cm._list_installed_packages(self.install_folder, only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(2, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["foo", "bar", "bar1"])
        self.check_command_rc(pm, "bar", 0)

        self.leaf_exec(("package", "install"), "pluginA_1.1")
        pm.load_user_plugins(cm._list_installed_packages(self.install_folder, only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(3, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["foo", "bar", "bar2", "bar3"])
        self.check_command_rc(pm, "bar", 0)

        pm.load_builtin_plugins({})
        self.assertEqual(0, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(3, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["bar", "bar2", "bar3"])
        self.check_command_rc(pm, "bar", 2)

        self.leaf_exec(("package", "uninstall"), "pluginA_1.1")
        pm.load_user_plugins(cm._list_installed_packages(self.install_folder, only_latest=True))
        self.assertEqual(0, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(2, len(pm._LeafPluginManager__user_plugins))
        self.check_commands(pm, ["bar", "bar1"])
        self.check_command_rc(pm, "bar", 1)

    def test_location(self):
        builtin_folder = TEST_RESOURCE_FOLDER / "__plugins"
        self.assertTrue(builtin_folder.is_dir())
        pm = LeafPluginManager()
        cm = ConfigurationManager()

        self.assertEqual(0, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(0, len(pm._LeafPluginManager__user_plugins))

        pm.load_builtin_plugins(cm._list_installed_packages(builtin_folder, only_latest=True))
        self.assertEqual(5, len(pm._LeafPluginManager__builtin_plugins))
        self.assertEqual(0, len(pm._LeafPluginManager__user_plugins))

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
