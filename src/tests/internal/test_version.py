"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""


from leaf import __version__
from leaf.core.utils import CURRENT_LEAF_VERSION, Version, version_comparator
from leaf.tools import OPERATOR_LABELS
from tests.testutils import LeafTestCase


class TestVersion(LeafTestCase):

    ALT_OP = {
        Version.__gt__: (Version.__ge__, Version.__ne__),
        Version.__ge__: (),
        Version.__lt__: (Version.__le__, Version.__ne__),
        Version.__le__: (),
        Version.__eq__: (Version.__ge__, Version.__le__),
        Version.__ne__: (),
    }

    def assert_compare(self, a: Version, op: callable, b: Version, result=True):
        msg = "{a} {op} {b}".format(a=a, b=b, op=OPERATOR_LABELS[op][0])
        print("Test", msg)
        self.assertEqual(result, op(a, b), msg=msg)

    def test_version_compare(self):
        for a, b, op in (
            ("1", "1", Version.__eq__),
            ("1", "1.0", Version.__lt__),
            ("1", "1.0.0-0", Version.__lt__),
            ("1.00", "1.0.0", Version.__lt__),
            ("1.00", "1.0", Version.__eq__),
            ("1.a", "1.a", Version.__eq__),
            ("1.1", "1.2", Version.__lt__),
            ("1.a-rc1", "1.a.rc1", Version.__eq__),
            ("3", "2", Version.__gt__),
            ("3.2", "3.1", Version.__gt__),
            ("LXSWI2.5-3.0", "LXSWI2.5-3.0.rc1", Version.__lt__),
            ("LXSWI2.5-4.0", "LXSWI2.5-3.0", Version.__gt__),
            ("LXSWI2.5-3.1", "LXSWI2.5-3.0", Version.__gt__),
            ("LXSWI2.7-1.0", "LXSWI2.5-11.0", Version.__gt__),
            ("SWI9X28A_00.02.00.00", "SWI9X28A_00.01.02.03", Version.__gt__),
            ("SWI9X28A_00.01.02.03", "SWI9X28A_00.01.02.02 ", Version.__gt__),
            ("16.10.0.m3.rc1", "16.10.0", Version.__gt__),
        ):
            va, vb = Version(a), Version(b)
            self.assert_compare(va, op, vb)
            for op2 in TestVersion.ALT_OP[op]:
                self.assert_compare(va, op2, vb)

    def test_comparator(self):
        self.assert_compare(CURRENT_LEAF_VERSION, Version.__eq__, __version__)

    def test_implicit_zero(self):
        self.assertEqual(0, version_comparator("1.0", "1.0", implicit_zero=True))
        self.assertEqual(0, version_comparator("1.0", "1.0", implicit_zero=False))

        self.assertEqual(0, version_comparator("1.0", "1.0.0", implicit_zero=True))
        self.assertEqual(-1, version_comparator("1.0", "1.0.0", implicit_zero=False))

        self.assertEqual(0, version_comparator("1.0.0.0", "1.0.0", implicit_zero=True))
        self.assertEqual(1, version_comparator("1.0.0.0", "1.0.0", implicit_zero=False))

        # Default behaviour
        self.assertEqual(-1, version_comparator("1.0", "1.0.0"))
        self.assertEqual(1, version_comparator("1.0.0.0", "1.0.0"))
