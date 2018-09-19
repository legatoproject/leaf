'''
@author: nico
'''

from pathlib import Path
from tempfile import mkdtemp

from leaf.format.alignment import VAlign, HAlign
from leaf.format.chars import _SEPARATORS_ASCII
from leaf.format.formatutils import sizeof_fmt
from leaf.format.table import Table
from leaf.format.theme import ThemeManager

from tests.testutils import AbstractTestWithChecker, LEAF_UT_DEBUG


class TestFormat(AbstractTestWithChecker):

    def testsizeof_fmt(self):
        self.assertEqual(sizeof_fmt(0), "0 bytes")
        self.assertEqual(sizeof_fmt(1), "1 byte")
        self.assertEqual(sizeof_fmt(123789), "121 kB")
        self.assertEqual(sizeof_fmt(456123789), "435.0 MB")

    def _createTable(self):
        if LEAF_UT_DEBUG is not None:
            ROOT_FOLDER = Path("/tmp/leaf")
        else:
            ROOT_FOLDER = Path(mkdtemp(prefix="leaf_tests_"))
        table = Table(ThemeManager(ROOT_FOLDER / "themes.ini"))
        nbElt = 7
        table.newRow().newSep(nbElt)
        table.newRow().newSep() \
            .newCell("Cell1:\n- multiline,\n- vertical alignment: centered,\n- Vertically spanned", vAlign=VAlign.MIDDLE).newDblSep() \
            .newCell("Cell2:\n- multiline,\n- horizontal alignment: centered,\n- Horizontally spanned", HAlign.CENTER).newHSpan(nbElt - 5).newSep()
        table.newRow().newSep().newVSpan().newDblSep(4).newSep()
        table.newRow().newSep() \
            .newVSpan().newDblSep() \
            .newCell("Cell3: one line, vertical alignment: bottom", vAlign=VAlign.BOTTOM).newSep() \
            .newCell("Cell4:\n- multiline\n- horizontal alignment: right", HAlign.RIGHT).newSep()
        table.newRow().newSep(nbElt)
        return table

    def testTable(self):
        with self.assertStdout(
                templateOut="table.out"):
            print(self._createTable())

    def testAsciiSwitch(self):
        table = self._createTable()
        table.separators = _SEPARATORS_ASCII
        with self.assertStdout(
                templateOut="table.out"):
            print(table)
