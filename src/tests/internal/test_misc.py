"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from pathlib import Path
from tempfile import mktemp

from leaf.core.constants import JsonConstants, LeafFiles
from leaf.core.error import LeafException
from leaf.core.jsonutils import JsonObject, jloadfile, jwritefile
from leaf.core.lock import LockFile
from leaf.core.utils import check_leaf_min_version
from leaf.model.modelutils import group_package_identifiers_by_name
from leaf.model.package import Feature, InstalledPackage, PackageIdentifier
from leaf.model.steps import VariableResolver
from tests.testutils import RESOURCE_FOLDER, LeafTestCase


class TestMisc(LeafTestCase):

    def test_leaf_minver(self):
        self.assertTrue(check_leaf_min_version(None))
        self.assertTrue(check_leaf_min_version("2.0", "2.0"))
        self.assertFalse(check_leaf_min_version("2.1", "2.0"))
        with self.assertRaises(LeafException):
            self.assertFalse(check_leaf_min_version("2.1", "2.0", exception_message="foo"))

    def test_json(self):
        jo = JsonObject({})
        self.assertIsNone(jo.jsonpath(["a"]))
        self.assertIsNotNone(jo.jsonpath(["a"], {}))
        self.assertIsNotNone(jo.jsonpath(["a"]))

        self.assertIsNone(jo.jsonpath(["a", "b"]))
        self.assertIsNotNone(jo.jsonpath(["a", "b"], {}))
        self.assertIsNotNone(jo.jsonpath(["a", "b"]))

        self.assertIsNone(jo.jsonpath(["a", "b", "c"]))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        tmpfile = Path(mktemp(".json", "leaf-ut"))
        jwritefile(tmpfile, jo.json, pp=True)
        jo = JsonObject(jloadfile(tmpfile))

        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        with self.assertRaises(ValueError):
            jo.jsonget("z", mandatory=True)
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "b", "c", "d"])
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "d", "e"])

    def test_features_equal(self):
        self.assertEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
        )

        # Different name
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id2",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
        )

        # Different key
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY2",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
        )

        # Different enum
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum2": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
        )

        # Different value
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value2"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
        )

        # Different size
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1", "enum2": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
        )

        # Different description
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message2",
                },
            ),
        )

        # Different description: None
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature(
                "id1",
                {JsonConstants.INFO_FEATURE_KEY: "KEY1", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}, JsonConstants.INFO_FEATURE_DESCRIPTION: None},
            ),
        )

        # Different description: missing
        self.assertNotEqual(
            Feature(
                "id1",
                {
                    JsonConstants.INFO_FEATURE_KEY: "KEY1",
                    JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
                    JsonConstants.INFO_FEATURE_DESCRIPTION: "message",
                },
            ),
            Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}}),
        )

    def test_features_alias(self):
        feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}})
        feature_newvalue = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1", "enum2": "value2"}})
        feature_dupvalue = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value3", "enum3": None}})
        feature_altkey = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY2", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}})
        other_feature = Feature("id2", {JsonConstants.INFO_FEATURE_KEY: "KEY1", JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}})

        test_feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        test_feature.check()
        with self.assertRaises(LeafException):
            test_feature.get_value("enum1")

        test_feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        test_feature.add_alias(feature)
        test_feature.check()
        with self.assertRaises(LeafException):
            test_feature.get_value("enum2")

        test_feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        test_feature.add_alias(feature)
        test_feature.add_alias(feature_newvalue)
        test_feature.check()
        self.assertEqual("value1", test_feature.get_value("enum1"))
        self.assertEqual("value2", test_feature.get_value("enum2"))

        test_feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        test_feature.add_alias(feature)
        test_feature.add_alias(feature_newvalue)
        test_feature.add_alias(feature_dupvalue)
        test_feature.check()
        with self.assertRaises(LeafException):
            test_feature.get_value("enum1")
        self.assertEqual("value2", test_feature.get_value("enum2"))
        self.assertEqual(None, test_feature.get_value("enum3"))

        test_feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        test_feature.add_alias(feature)
        test_feature.add_alias(feature_newvalue)
        test_feature.add_alias(feature_dupvalue)
        test_feature.add_alias(feature_altkey)
        with self.assertRaises(LeafException):
            test_feature.check()

        test_feature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        with self.assertRaises(LeafException):
            test_feature.add_alias(other_feature)

    def test_sort_pi(self):
        a10 = PackageIdentifier.parse("a_1.0")
        a20 = PackageIdentifier.parse("a_2.0")
        a11 = PackageIdentifier.parse("a_1.1")
        a21 = PackageIdentifier.parse("a_2.1")
        b10 = PackageIdentifier.parse("b_1.0")
        b20 = PackageIdentifier.parse("b_2.0")
        b11 = PackageIdentifier.parse("b_1.1")
        b21 = PackageIdentifier.parse("b_2.1")

        pkgmap = group_package_identifiers_by_name([a20, a10, b11, b21, a21])
        self.assertEqual(pkgmap, {"a": [a10, a20, a21], "b": [b11, b21]})

        pkgmap = group_package_identifiers_by_name([b10, a11, b20, a20], pkgmap=pkgmap)
        self.assertEqual(pkgmap, {"a": [a10, a11, a20, a21], "b": [b10, b11, b20, b21]})

    def test_variable_resolver(self):

        ip1 = InstalledPackage(RESOURCE_FOLDER / "version_1.0" / LeafFiles.MANIFEST)
        ip2 = InstalledPackage(RESOURCE_FOLDER / "version_1.1" / LeafFiles.MANIFEST)
        ip3 = InstalledPackage(RESOURCE_FOLDER / "version_2.0" / LeafFiles.MANIFEST)

        vr = VariableResolver(ip1, [ip1, ip2, ip3])

        self.assertEqual("version", vr.resolve("@{NAME}"))
        self.assertEqual("1.0", vr.resolve("@{VERSION}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_1.0"), vr.resolve("@{DIR}"))

        self.assertEqual("version", vr.resolve("@{NAME:version_1.0}"))
        self.assertEqual("1.0", vr.resolve("@{VERSION:version_1.0}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_1.0"), vr.resolve("@{DIR:version_1.0}"))

        self.assertEqual("version", vr.resolve("@{NAME:version_2.0}"))
        self.assertEqual("2.0", vr.resolve("@{VERSION:version_2.0}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_2.0"), vr.resolve("@{DIR:version_2.0}"))

        self.assertEqual("version", vr.resolve("@{NAME:version_latest}"))
        self.assertEqual("2.0", vr.resolve("@{VERSION:version_latest}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_2.0"), vr.resolve("@{DIR:version_latest}"))

        self.assertEqual("version 1.1 " + str(RESOURCE_FOLDER / "version_2.0"), vr.resolve("@{NAME} @{VERSION:version_1.1} @{DIR:version_latest}"))

        with self.assertRaises(LeafException):
            vr.resolve("@{NAME} @{VERSION:version_1.2} @{DIR:version_latest}")

    def test_lock_advisory(self):
        advisory = True
        lf = LockFile("/tmp/advisory.lock")

        @lf.acquire(advisory=advisory)
        def foo():
            pass

        lf.acquire(advisory=advisory)
        with lf.acquire(advisory=advisory):
            with lf.acquire(advisory=advisory):
                with lf.acquire(advisory=advisory):
                    foo()
                foo()
            with lf.acquire(advisory=advisory):
                with lf.acquire(advisory=advisory):
                    foo()
                foo()
            foo()

    def test_lock_mandatory(self):
        advisory = False
        lf = LockFile("/tmp/mandatory.lock")

        @lf.acquire(advisory=advisory)
        def foo():
            pass

        lf.acquire(advisory=advisory)

        with lf.acquire(advisory=advisory):
            with self.assertRaises(LeafException):
                with lf.acquire(advisory=advisory):
                    pass
            try:
                with lf.acquire(advisory=advisory):
                    self.fail()
                self.fail()
            except LeafException:
                pass
            with self.assertRaises(LeafException):
                foo()

        with lf.acquire(advisory=advisory):
            pass
