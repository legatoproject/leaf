'''
@author: seb
'''

from leaf.core import checkLeafVersion
import unittest


class TestMisc(unittest.TestCase):

    def testLeafMinVersion(self):
        self.assertTrue(checkLeafVersion(None))
        self.assertTrue(checkLeafVersion("2.0"))
        self.assertTrue(checkLeafVersion("2.0", "2.0"))
        self.assertFalse(checkLeafVersion("2.1", "2.0"))


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
