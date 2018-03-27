'''
@author: seb
'''

from tempfile import mktemp
import unittest

from leaf.model import JsonObject
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
        self.assertTrue(jo.jsonpath("foo") is None)
        self.assertTrue(jo.jsonpath("foo", "bar") is None)
        self.assertEqual("hello", jo.jsonpath("foo", "bar2", default="hello"))
        newMap = jo.jsoninit(key="foo", value={})
        jo.jsoninit("foo", key="bar", value="hello")
        newMap["bar2"] = "hello2"
        self.assertFalse(jo.jsonpath("foo") is None)
        self.assertFalse(jo.jsonpath("foo", "bar") is None)
        self.assertEqual("hello", jo.jsonpath("foo", "bar"))
        self.assertEqual("hello2", jo.jsonpath("foo", "bar2"))

        tmpFile = mktemp(".json", "leaf-ut")
        jsonWriteFile(tmpFile, jo.json, pp=True)
        jo = JsonObject(jsonLoadFile(tmpFile))
        self.assertFalse(jo.jsonpath("foo") is None)
        self.assertFalse(jo.jsonpath("foo", "bar") is None)
        self.assertEqual("hello", jo.jsonpath("foo", "bar"))
        self.assertEqual("hello2", jo.jsonpath("foo", "bar2"))

        self.assertEqual("hello2", jo.jsoninit("foo",
                                               key="bar2",
                                               value="barbar"))
        self.assertEqual("barbar", jo.jsoninit("foo",
                                               key="bar2",
                                               value="barbar",
                                               force=True))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
