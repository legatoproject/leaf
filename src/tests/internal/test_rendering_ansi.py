'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''
import unittest

from leaf.core.packagemanager import LoggerManager
from leaf.format.ansi import ANSI
from leaf.format.logger import Verbosity
from tests.internal.test_rendering import TestRendering
from tests.testutils import LEAF_UT_SKIP


class TestRenderingAnsi(TestRendering):

    @classmethod
    def setUpClass(cls):
        ANSI.force = True
        TestRendering.setUpClass()

    def __init__(self, methodName):
        TestRendering.__init__(self, methodName)

    @classmethod
    def tearDownClass(cls):
        TestRendering.tearDownClass()
        ANSI.force = False


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestRenderingAnsiVerbose(TestRenderingAnsi):
    def __init__(self, methodName):
        TestRenderingAnsi.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.VERBOSE)


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestRenderingAnsiQuiet(TestRenderingAnsi):
    def __init__(self, methodName):
        TestRenderingAnsi.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.QUIET)
