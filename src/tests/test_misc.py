'''
@author: seb
'''

from tempfile import mktemp
import unittest

from leaf.model.base import JsonObject
from leaf.utils import checkSupportedLeaf, jsonWriteFile, jsonLoadFile


class TestMisc(unittest.TestCase):

    def testLeafMinVersion(self):
        self.assertTrue(checkSupportedLeaf(None))
        self.assertTrue(checkSupportedLeaf("2.0"))
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


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
