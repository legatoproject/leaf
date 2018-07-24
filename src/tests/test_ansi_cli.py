'''
@author: nico
'''

import unittest

from leaf.format.ansi import ANSI
from tests.test_rendering_cli import TestRenderingCli_Default
from tests.testutils import LEAF_UT_SKIP


class TestAnsiCli_Default(TestRenderingCli_Default):

    @classmethod
    def setUpClass(cls):
        ANSI.force = True
        TestRenderingCli_Default.setUpClass()

    def __init__(self, methodName):
        TestRenderingCli_Default.__init__(self, methodName)

    @classmethod
    def tearDownClass(cls):
        TestRenderingCli_Default.tearDownClass()
        ANSI.force = False


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestAnsiCli_Verbose(TestAnsiCli_Default):
    def __init__(self, methodName):
        TestAnsiCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestAnsiCli_Quiet(TestAnsiCli_Default):
    def __init__(self, methodName):
        TestAnsiCli_Default.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")


if __name__ == "__main__":
    unittest.main()
