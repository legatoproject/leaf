"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

from leaf.tools import OPERATOR_LABELS
from tests.testutils import LeafTestCaseWithCli
from tests.internal.test_version import TestVersion


class TestCliVersionComparator(LeafTestCaseWithCli, TestVersion):
    def assert_compare(self, a, op, b, result=True):
        super().assert_compare(a, op, b, result=result)
        self.simple_exec(a, OPERATOR_LABELS[op][0], b, bin="leaf-version-compare", expected_rc=0 if result else 1)

    def test_simple(self):
        self.simple_exec("-h", bin="leaf-version-compare", silent=False)

        with self.assertStdout("out.txt"):
            self.simple_exec("1.0", "-eq", "0.9", bin="leaf-version-compare", silent=False, expected_rc=1)
            self.simple_exec("1.0", "-eq", "1.0", bin="leaf-version-compare", silent=False, expected_rc=0)
            self.simple_exec("1.0", "-eq", "1.1", bin="leaf-version-compare", silent=False, expected_rc=1)

            self.simple_exec("1.0", "-ne", "0.9", bin="leaf-version-compare", silent=False, expected_rc=0)
            self.simple_exec("1.0", "-ne", "1.0", bin="leaf-version-compare", silent=False, expected_rc=1)
            self.simple_exec("1.0", "-ne", "1.1", bin="leaf-version-compare", silent=False, expected_rc=0)

            self.simple_exec("1.0", "-lt", "0.9", bin="leaf-version-compare", silent=False, expected_rc=1)
            self.simple_exec("1.0", "-lt", "1.0", bin="leaf-version-compare", silent=False, expected_rc=1)
            self.simple_exec("1.0", "-lt", "1.1", bin="leaf-version-compare", silent=False, expected_rc=0)

            self.simple_exec("1.0", "-le", "0.9", bin="leaf-version-compare", silent=False, expected_rc=1)
            self.simple_exec("1.0", "-le", "1.0", bin="leaf-version-compare", silent=False, expected_rc=0)
            self.simple_exec("1.0", "-le", "1.1", bin="leaf-version-compare", silent=False, expected_rc=0)

            self.simple_exec("1.0", "-gt", "0.9", bin="leaf-version-compare", silent=False, expected_rc=0)
            self.simple_exec("1.0", "-gt", "1.0", bin="leaf-version-compare", silent=False, expected_rc=1)
            self.simple_exec("1.0", "-gt", "1.1", bin="leaf-version-compare", silent=False, expected_rc=1)

            self.simple_exec("1.0", "-ge", "0.9", bin="leaf-version-compare", silent=False, expected_rc=0)
            self.simple_exec("1.0", "-ge", "1.0", bin="leaf-version-compare", silent=False, expected_rc=0)
            self.simple_exec("1.0", "-ge", "1.1", bin="leaf-version-compare", silent=False, expected_rc=1)
