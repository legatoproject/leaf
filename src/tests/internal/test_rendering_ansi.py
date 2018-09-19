'''
@author: nico
'''
import unittest

from leaf.core.packagemanager import LoggerManager
from leaf.format.ansi import ANSI
from leaf.format.logger import Verbosity
from tests.internal.test_rendering import TestRendering_Default
from tests.testutils import LEAF_UT_SKIP


class TestAnsi_Default(TestRendering_Default):

    @classmethod
    def setUpClass(cls):
        ANSI.force = True
        TestRendering_Default.setUpClass()

    def __init__(self, methodName):
        TestRendering_Default.__init__(self, methodName)

    @classmethod
    def tearDownClass(cls):
        TestRendering_Default.tearDownClass()
        ANSI.force = False


@unittest.skipIf("VERBOSE" in LEAF_UT_SKIP, "Test disabled")
class TestAnsi_Verbose(TestAnsi_Default):
    def __init__(self, methodName):
        TestAnsi_Default.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.VERBOSE, True)


@unittest.skipIf("QUIET" in LEAF_UT_SKIP, "Test disabled")
class TestAnsi_Quiet(TestAnsi_Default):
    def __init__(self, methodName):
        TestAnsi_Default.__init__(self, methodName)
        self.loggerManager = LoggerManager(Verbosity.QUIET, True)
