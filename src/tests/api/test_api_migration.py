"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from collections import OrderedDict

from leaf import __version__
from leaf.core.constants import LeafSettings
from leaf.core.jsonutils import jloadfile, jwritefile
from leaf.core.utils import CURRENT_LEAF_VERSION, Version
from leaf.model.config import ConfigFileWithLayer, UserConfiguration, WorkspaceConfiguration
from tests.testutils import LeafTestCase


class TestApiMigration(LeafTestCase):
    LEAF_VERSION = None

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.force_version(__version__)
        super().tearDown()

    def force_version(self, version):
        self.assertEqual(CURRENT_LEAF_VERSION._Version__version, CURRENT_LEAF_VERSION.value)
        CURRENT_LEAF_VERSION._Version__version = version
        self.assertEqual(CURRENT_LEAF_VERSION.value, version)

    def test_updaters(self):
        def my_updater_foo(model):
            model.json["test"].append("foo")

        def my_updater_bar(model):
            model.json["test"].append("bar")

        class MyConfig(ConfigFileWithLayer):
            def __init__(self, *layers):
                ConfigFileWithLayer.__init__(self, *layers)

            def _get_updaters(self):
                return super()._get_updaters() + ((None, my_updater_foo), (Version("2.0"), my_updater_bar))

            @property
            def test_list(self):
                return self.json["test"]

        tmpfile = self.test_folder / "a.json"
        jwritefile(tmpfile, {"test": ["hello"]})

        self.force_version("1.0")
        model = MyConfig(tmpfile)
        self.assertEqual(["hello", "foo", "bar"], model.test_list)
        model.write_layer(tmpfile)
        jmodel = jloadfile(tmpfile)
        self.assertEqual(["hello", "foo", "bar"], jmodel["test"])
        self.assertEqual("1.0", jmodel["leafMinVersion"])

        model = MyConfig(tmpfile)
        self.assertEqual(["hello", "foo", "bar"], model.test_list)
        model.write_layer(tmpfile)

        self.force_version("1.1")
        model = MyConfig(tmpfile)
        self.assertEqual(["hello", "foo", "bar", "foo", "bar"], model.test_list)
        model.write_layer(tmpfile)

        self.force_version("2.0")
        model = MyConfig(tmpfile)
        self.assertEqual(["hello", "foo", "bar", "foo", "bar", "foo", "bar"], model.test_list)
        model = MyConfig(tmpfile)
        self.assertEqual(["hello", "foo", "bar", "foo", "bar", "foo", "bar"], model.test_list)
        model.write_layer(tmpfile)

        self.force_version("2.1")
        model = MyConfig(tmpfile)
        self.assertEqual(["hello", "foo", "bar", "foo", "bar", "foo", "bar", "foo"], model.test_list)

    def test_update_root_folder(self):

        tmpfile = self.test_folder / "user.json"
        jwritefile(tmpfile, {"leafMinVersion": "1.8", "rootfolder": str(self.workspace_folder)})

        self.force_version("1.8")
        user_config = UserConfiguration(tmpfile)
        self.assertTrue("rootfolder" in user_config.json)
        self.assertEqual(0, len(user_config._getenvmap()))

        self.force_version("2.0")
        user_config = UserConfiguration(tmpfile)
        self.assertFalse("rootfolder" in user_config.json)
        self.assertEqual(1, len(user_config._getenvmap()))
        self.assertEqual(str(self.workspace_folder), user_config._getenvmap()[LeafSettings.USER_PKG_FOLDER.key])

    def test_update_packages_map(self):

        tmpfile = self.test_folder / "ws.json"
        jwritefile(tmpfile, {"leafMinVersion": "1.8", "profiles": {"foo": {"packages": ["test_1.0"]}, "bar": {"packages": {"test": "2.0"}}}})

        self.force_version("1.8")
        ws_config = WorkspaceConfiguration(tmpfile)
        self.assertTrue(isinstance(ws_config.json["profiles"]["foo"]["packages"], list))

        self.force_version("2.0")
        ws_config = WorkspaceConfiguration(tmpfile)
        self.assertTrue(isinstance(ws_config.json["profiles"]["foo"]["packages"], OrderedDict))
        self.assertEqual("1.0", ws_config.json["profiles"]["foo"]["packages"]["test"])
        self.assertTrue(isinstance(ws_config.json["profiles"]["bar"]["packages"], OrderedDict))
        self.assertEqual("2.0", ws_config.json["profiles"]["bar"]["packages"]["test"])
