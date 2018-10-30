'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

import unittest

from leaf.format.ansi import ANSI
from tests.cli.test_cli_rendering import TestCliRendering
from tests.testutils import LEAF_UT_SKIP


class TestCliRenderingAnsi(TestCliRendering):

    @classmethod
    def setUpClass(cls):
        ANSI.force = True
        TestCliRendering.setUpClass()

    def __init__(self, methodName):
        TestCliRendering.__init__(self, methodName)

    @classmethod
    def tearDownClass(cls):
        TestCliRendering.tearDownClass()
        ANSI.force = False


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestCliRenderingAnsiVerbose(TestCliRenderingAnsi):
    def __init__(self, methodName):
        TestCliRenderingAnsi.__init__(self, methodName)
        self.postVerbArgs.append("--verbose")


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestCliRenderingAnsiQuiet(TestCliRenderingAnsi):
    def __init__(self, methodName):
        TestCliRenderingAnsi.__init__(self, methodName)
        self.postVerbArgs.append("--quiet")
