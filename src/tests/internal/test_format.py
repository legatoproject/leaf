'''
@author: Legato Tooling Team <letools@sierrawireless.com>
'''

from leaf.rendering.alignment import HAlign, VAlign
from leaf.rendering.chars import _SEPARATORS_ASCII
from leaf.rendering.formatutils import sizeof_fmt
from leaf.rendering.table import Table
from leaf.rendering.theme import ThemeManager
from tests.testutils import LeafTestCase


class TestFormat(LeafTestCase):

    def testsizeof_fmt(self):
        self.assertEqual(sizeof_fmt(0), "0 bytes")
        self.assertEqual(sizeof_fmt(1), "1 byte")
        self.assertEqual(sizeof_fmt(123789), "121 kB")
        self.assertEqual(sizeof_fmt(456123789), "435.0 MB")

    def _createTable(self):
        table = Table(ThemeManager())
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
        table = self._createTable()
        with self.assertStdout(templateOut="table.out"):
            print(table)
            table.removeColumns({1, 2, 4, 5})
            print(table)

    def testAsciiSwitch(self):
        table = self._createTable()
        table.separators = _SEPARATORS_ASCII
        with self.assertStdout(templateOut="table.out"):
            print(table)
