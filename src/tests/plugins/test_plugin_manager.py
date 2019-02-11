'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from pathlib import Path

from leaf.cli.plugins import LeafPluginCommand, LeafPluginManager
from tests.testutils import RESOURCE_FOLDER, LeafTestCaseWithCli


class TestPluginManagerCli(LeafTestCaseWithCli):

    def checkCommands(self, pm, commandNames, prefix=(), ignored=None):
        prefix = ('leaf', ) + prefix
        for c in pm.getCommands(prefix):
            self.assertIsInstance(c, LeafPluginCommand)
        self.assertEqual(commandNames,
                         list(map(lambda c: c.name,
                                  pm.getCommands(prefix,
                                                 ignoredNames=ignored))))

    def checkCommandRc(self, pm, cmdName, rc):
        for c in pm.getCommands(()):
            if c.name == cmdName:
                self.assertEqual(rc, c.execute(None, None))
                return
        self.fail("Cannot find command " + cmdName)

    def testBuiltin(self):

        builtinFolder = RESOURCE_FOLDER / "__plugins"
        self.assertTrue(builtinFolder.is_dir())

        pm = LeafPluginManager()

        self.assertEqual(0, len(pm.builtinPluginMap))
        self.assertEqual(0, len(pm.userPluginMap))

        pm.loadBuiltinPlugins(builtinFolder)
        self.assertEqual(5, len(pm.builtinPluginMap))
        self.assertEqual(0, len(pm.userPluginMap))
        self.checkCommands(pm, ["foo", "bar"])

        pm.loadUserPlugins(Path("/unknownFolder/"))
        self.assertEqual(5, len(pm.builtinPluginMap))
        self.assertEqual(0, len(pm.userPluginMap))
        self.checkCommands(pm, ["foo", "bar"])

        pm.loadUserPlugins(self.getInstallFolder())
        self.assertEqual(5, len(pm.builtinPluginMap))
        self.assertEqual(0, len(pm.userPluginMap))
        self.checkCommands(pm, ["foo", "bar"])
        self.assertEqual(0, pm.getCommands(())[1].execute(None, None))

        self.leafExec(('package', 'install'), 'pluginA_1.0')
        pm.loadUserPlugins(self.getInstallFolder())
        self.assertEqual(5, len(pm.builtinPluginMap))
        self.assertEqual(2, len(pm.userPluginMap))
        self.checkCommands(pm, ["foo", "bar", "bar1"])
        self.checkCommandRc(pm, "bar", 0)

        self.leafExec(('package', 'install'), 'pluginA_1.1')
        pm.loadUserPlugins(self.getInstallFolder())
        self.assertEqual(5, len(pm.builtinPluginMap))
        self.assertEqual(3, len(pm.userPluginMap))
        self.checkCommands(pm, ["foo", "bar", "bar2", "bar3"])
        self.checkCommandRc(pm, "bar", 0)

        pm.loadBuiltinPlugins(None)
        self.assertEqual(0, len(pm.builtinPluginMap))
        self.assertEqual(3, len(pm.userPluginMap))
        self.checkCommands(pm, ["bar", "bar2", "bar3"])
        self.checkCommandRc(pm, "bar", 2)

        self.leafExec(('package', 'uninstall'), 'pluginA_1.1')
        pm.loadUserPlugins(self.getInstallFolder())
        self.assertEqual(0, len(pm.builtinPluginMap))
        self.assertEqual(2, len(pm.userPluginMap))
        self.checkCommands(pm, ["bar", "bar1"])
        self.checkCommandRc(pm, "bar", 1)

    def testLocation(self):
        builtinFolder = RESOURCE_FOLDER / "__plugins"
        self.assertTrue(builtinFolder.is_dir())
        pm = LeafPluginManager()

        self.assertEqual(0, len(pm.builtinPluginMap))
        self.assertEqual(0, len(pm.userPluginMap))

        pm.loadBuiltinPlugins(builtinFolder)
        self.assertEqual(5, len(pm.builtinPluginMap))
        self.assertEqual(0, len(pm.userPluginMap))

        self.checkCommands(pm, ["foo", "bar"])
        self.checkCommands(pm, ["subcommand"],
                           prefix=("env",))
        self.checkCommands(pm, ["subcommand"],
                           prefix=("package",))
        self.checkCommands(pm, ["subcommand"],
                           prefix=("unknown",))
        self.checkCommands(pm, [],
                           prefix=("unknown",),
                           ignored=['subcommand'])

    def testPythonPath(self):
        self.leafExec(('package', 'install'), 'pluginB_1.0')
        with self.assertStdout(templateOut="pluginB.out"):
            self.leafExec("a")
            self.leafExec("b")
            self.leafExec("c")
            self.leafExec("d")
