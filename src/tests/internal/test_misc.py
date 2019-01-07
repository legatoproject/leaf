'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from tempfile import mktemp

import unittest
from tests.testutils import EXTENSIONS_FOLDER, RESOURCE_FOLDER

from leaf.cli.cliutils import ExternalCommandUtils
from leaf.constants import JsonConstants, LeafFiles
from leaf.core.coreutils import VariableResolver, \
    groupPackageIdentifiersByName
from leaf.core.error import LeafException
from leaf.core.lock import LockFile
from leaf.model.base import JsonObject
from leaf.model.package import Feature, InstalledPackage, PackageIdentifier
from leaf.utils import checkSupportedLeaf, jsonLoadFile, jsonWriteFile


class TestMisc(unittest.TestCase):

    def testGrepDescription(self):
        file = RESOURCE_FOLDER / "leaf-foo.sh"
        self.assertTrue(file.exists())
        description = ExternalCommandUtils.grepDescription(file)
        self.assertEqual("The description of my command", description)

        file = RESOURCE_FOLDER / "install_1.0" / "manifest.json"
        self.assertTrue(file.exists())
        description = ExternalCommandUtils.grepDescription(file)
        self.assertIsNone(description)

        for extension in EXTENSIONS_FOLDER.iterdir():
            description = ExternalCommandUtils.grepDescription(extension)
            print(extension, description)
            self.assertIsNotNone(description)

    def testLeafMinVersion(self):
        self.assertTrue(checkSupportedLeaf(None))
        self.assertTrue(checkSupportedLeaf("2.0", "2.0"))
        self.assertFalse(checkSupportedLeaf("2.1", "2.0"))
        with self.assertRaises(ValueError):
            self.assertFalse(checkSupportedLeaf("2.1", "2.0",
                                                exceptionMessage="foo"))

    def testJo(self):
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

        tmpFile = mktemp(".json", "leaf-ut")
        jsonWriteFile(tmpFile, jo.json, pp=True)
        jo = JsonObject(jsonLoadFile(tmpFile))

        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "hello"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"], "world"))
        self.assertEqual("hello", jo.jsonpath(["a", "b", "c"]))

        with self.assertRaises(ValueError):
            jo.jsonget("z", mandatory=True)
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "b", "c", "d"])
        with self.assertRaises(ValueError):
            jo.jsonpath(["a", "d", "e"])

    def testFeaturesEquals(self):
        self.assertEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different name
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id2", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different key
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY2",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different enum
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum2": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different value
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value2"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different size
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1", "enum2": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }))

        # Different description
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message2"
        }))

        # Different description: None
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: None
        }))

        # Different description: missing
        self.assertNotEqual(Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
            JsonConstants.INFO_FEATURE_DESCRIPTION: "message"
        }), Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"}
        }))

    def testFeaturesAlias(self):
        feature = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
        })
        feature_newValue = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1",
                                                "enum2": "value2"},
        })
        feature_dupValue = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value3",
                                                "enum3": None},
        })
        feature_altKey = Feature("id1", {
            JsonConstants.INFO_FEATURE_KEY: "KEY2",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
        })
        otherFeature = Feature("id2", {
            JsonConstants.INFO_FEATURE_KEY: "KEY1",
            JsonConstants.INFO_FEATURE_VALUES: {"enum1": "value1"},
        })

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.check()
        with self.assertRaises(ValueError):
            testFeature.getValue("enum1")

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.check()
        with self.assertRaises(ValueError):
            testFeature.getValue("enum2")

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.addAlias(feature_newValue)
        testFeature.check()
        self.assertEqual("value1", testFeature.getValue("enum1"))
        self.assertEqual("value2", testFeature.getValue("enum2"))

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.addAlias(feature_newValue)
        testFeature.addAlias(feature_dupValue)
        testFeature.check()
        with self.assertRaises(ValueError):
            testFeature.getValue("enum1")
        self.assertEqual("value2", testFeature.getValue("enum2"))
        self.assertEqual(None, testFeature.getValue("enum3"))

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        testFeature.addAlias(feature)
        testFeature.addAlias(feature_newValue)
        testFeature.addAlias(feature_dupValue)
        testFeature.addAlias(feature_altKey)
        with self.assertRaises(ValueError):
            testFeature.check()

        testFeature = Feature("id1", {JsonConstants.INFO_FEATURE_KEY: "KEY1"})
        with self.assertRaises(ValueError):
            testFeature.addAlias(otherFeature)

    def testSortPi(self):
        a10 = PackageIdentifier.fromString("a_1.0")
        a20 = PackageIdentifier.fromString("a_2.0")
        a11 = PackageIdentifier.fromString("a_1.1")
        a21 = PackageIdentifier.fromString("a_2.1")
        b10 = PackageIdentifier.fromString("b_1.0")
        b20 = PackageIdentifier.fromString("b_2.0")
        b11 = PackageIdentifier.fromString("b_1.1")
        b21 = PackageIdentifier.fromString("b_2.1")

        pkgMap = groupPackageIdentifiersByName(
            [a20, a10, b11, b21, a21])
        self.assertEqual(pkgMap,
                         {'a': [a10, a20, a21],
                          'b': [b11, b21]})

        pkgMap = groupPackageIdentifiersByName(
            [b10, a11, b20, a20], pkgMap=pkgMap)
        self.assertEqual(pkgMap,
                         {'a': [a10, a11, a20, a21],
                          'b': [b10, b11, b20, b21]})

    def testVariableResolver(self):

        ip1 = InstalledPackage(
            RESOURCE_FOLDER / "version_1.0" / LeafFiles.MANIFEST)
        ip2 = InstalledPackage(
            RESOURCE_FOLDER / "version_1.1" / LeafFiles.MANIFEST)
        ip3 = InstalledPackage(
            RESOURCE_FOLDER / "version_2.0" / LeafFiles.MANIFEST)

        vr = VariableResolver(ip1, [ip1, ip2, ip3])

        self.assertEqual("version",
                         vr.resolve("@{NAME}"))
        self.assertEqual("1.0",
                         vr.resolve("@{VERSION}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_1.0"),
                         vr.resolve("@{DIR}"))

        self.assertEqual("version",
                         vr.resolve("@{NAME:version_1.0}"))
        self.assertEqual("1.0",
                         vr.resolve("@{VERSION:version_1.0}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_1.0"),
                         vr.resolve("@{DIR:version_1.0}"))

        self.assertEqual("version",
                         vr.resolve("@{NAME:version_2.0}"))
        self.assertEqual("2.0",
                         vr.resolve("@{VERSION:version_2.0}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_2.0"),
                         vr.resolve("@{DIR:version_2.0}"))

        self.assertEqual("version",
                         vr.resolve("@{NAME:version_latest}"))
        self.assertEqual("2.0",
                         vr.resolve("@{VERSION:version_latest}"))
        self.assertEqual(str(RESOURCE_FOLDER / "version_2.0"),
                         vr.resolve("@{DIR:version_latest}"))

        self.assertEqual("version 1.1 " + str(RESOURCE_FOLDER / "version_2.0"),
                         vr.resolve("@{NAME} @{VERSION:version_1.1} @{DIR:version_latest}"))

        with self.assertRaises(ValueError):
            vr.resolve("@{NAME} @{VERSION:version_1.2} @{DIR:version_latest}")

    def testLockAdvisory(self):
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

    def testLockMandatory(self):
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
