"""
@author: Legato Tooling Team <letools@sierrawireless.com>
"""

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

    def __createtable(self):
        table = Table(ThemeManager())
        count = 7
        table.new_row().new_separator(count)
        table.new_row().new_separator().new_cell(
            "Cell1:\n- multiline,\n- vertical alignment: centered,\n- Vertically spanned", valign=VAlign.MIDDLE
        ).new_double_separator().new_cell("Cell2:\n- multiline,\n- horizontal alignment: centered,\n- Horizontally spanned", HAlign.CENTER).new_hspan(
            count - 5
        ).new_separator()
        table.new_row().new_separator().new_vspan().new_double_separator(4).new_separator()
        table.new_row().new_separator().new_vspan().new_double_separator().new_cell(
            "Cell3: one line, vertical alignment: bottom", valign=VAlign.BOTTOM
        ).new_separator().new_cell("Cell4:\n- multiline\n- horizontal alignment: right", HAlign.RIGHT).new_separator()
        table.new_row().new_separator(count)
        return table

    def test_table(self):
        table = self.__createtable()
        with self.assertStdout(template_out="table.out"):
            print(table)
            table.remove_columns({1, 2, 4, 5})
            print(table)

    def test_ascii_switch(self):
        table = self.__createtable()
        table.separators = _SEPARATORS_ASCII
        with self.assertStdout(template_out="table.out"):
            print(table)
