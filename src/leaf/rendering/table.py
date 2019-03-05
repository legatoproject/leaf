"""
Generate an ASCII table
Support the followings features:
    - multiple lines cells
    - horizontal and vertical alignment
    - horizontal and vertical spanning
    - simple, double or invisible horizontal and vertical separators
    - can be turned to a multiline string using str()

Example:
    table = Table(ThemeManager())
    nbElt = 7
    table.new_row().new_separator(nbElt)
    table.new_row().new_separator() \
        .new_cell("Cell1:\n- multiline,\n- vertical alignment: centered,\n- Vertically spanned", valign=VAlign.MIDDLE).new_double_separator() \
        .new_cell("Cell2:\n- multiline,\n- horizontal alignment: centered,\n- Horizontally spanned", HAlign.CENTER).new_hspan(nbElt - 5).new_separator()
    table.new_row().new_separator().new_vspan().new_double_separator(4).new_separator()
    table.new_row().new_separator() \
        .new_vspan().new_double_separator() \
        .new_cell("Cell3: one line, vertical alignment: bottom", valign=VAlign.BOTTOM).new_separator() \
        .new_cell("Cell4:\n- multiline\n- horizontal alignment: right", HAlign.RIGHT).new_separator()
    table.new_row().new_separator(nbElt)
    print(table)
Result:
    ┌─────────────────────────────────╥─────────────────────────────────────────────────────────────────────────────┐
    │                                 ║                                    Cell2:                                   │
    │                                 ║                                 - multiline,                                │
    │ Cell1:                          ║                      - horizontal alignment: centered,                      │
    │ - multiline,                    ║                            - Horizontally spanned                           │
    │ - vertical alignment: centered, ╠═════════════════════════════════════════════╤═══════════════════════════════╡
    │ - Vertically spanned            ║                                             │                        Cell4: │
    │                                 ║                                             │                   - multiline │
    │                                 ║ Cell3: one line, vertical alignment: bottom │ - horizontal alignment: right │
    └─────────────────────────────────╨─────────────────────────────────────────────┴───────────────────────────────┘

You have a few constraints when you use this API (which are checked when trying to 'str' this class):
    - Each row must own the same number of elements which can be:
        - _Cell using _Row.newCell,
        - _HorizontalSpan using _Row.newHSpan,
        - _VerticalSpan using _Row.newVSpan,
        - _Separator using _Row.newSep
    - You can only span a _Cell, not a _Separator

@author:    Legato Tooling Team <letools@sierrawireless.com>
@copyright: Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
"""
from abc import ABC, abstractmethod
from enum import Enum, unique

from leaf.rendering.alignment import HAlign, VAlign
from leaf.rendering.ansi import remove_ansi_chars
from leaf.rendering.chars import PADDING_CHAR, get_separators
from leaf.rendering.theme import ThemeManager


class Table:

    """
    Represent the table
    """

    def __init__(self, tm: ThemeManager):
        self.tm = tm
        self.rows = []
        self.columns = []
        self.separators = get_separators()
        self.removed_columns_indexes = set()

    def new_row(self):
        """
        Add a new row in the table and return it
        """
        out = _Row(self)
        self.rows.append(out)
        return out

    def new_header(self, text, tablesize):
        """
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────┐
        │                               text                               │
        ├──────────────────────────────────────────────────────────────────┤
        """
        self.new_row().new_separator(tablesize)
        self.new_row().new_separator().new_cell(text, HAlign.CENTER).new_hspan(tablesize - 3).new_separator()
        self.new_row().new_separator(tablesize)

    @property
    def min_height(self):
        """
        Give the height of the table in char
        """
        return sum(row.min_height for row in self.rows)

    @property
    def min_width(self):
        """
        Give the width of the table in char
        """
        return sum(column.min_width for column in self.columns)

    def _check_table(self):
        """
        Check the table model coherence
        This can help developer to use this API
        """
        nb_elt_by_row = [len(row) for row in self.rows]
        assert min(nb_elt_by_row) == max(nb_elt_by_row), "Number of elements is not the same on each row: " + str(nb_elt_by_row)
        for row in self.rows:
            for elt in row:
                if isinstance(elt, _HorizontalSpan):
                    assert isinstance(_Cardinal.LEFT(elt), (_Cell, _HorizontalSpan)), "An horizontal span must follow another or a cell (not a separator)"
                if isinstance(elt, _VerticalSpan):
                    assert isinstance(_Cardinal.UP(elt), (_Cell, _VerticalSpan)), "An vertical span must be under another or a cell (not a separator)"

    def remove_columns(self, colid_set):
        self.removed_columns_indexes.update(colid_set)

    def __str__(self):
        # Create columns
        self.columns.clear()
        self.columns.extend(_Column(self, column_cells) for column_cells in zip(*self.rows))

        # Remove removed columns
        for index in sorted(self.removed_columns_indexes, reverse=True):
            # Simply delete hidden columns
            del self.columns[index]
            # For each row, delete the cell which is the hidden column
            for row in self.rows:
                del row[index]

        # check table coherence
        self._check_table()

        # Prepare char table with final size using dummy '*' char (useful to
        # debug a layout issue)
        table_strings = [""] * self.min_height
        for column in self.columns:
            for element in column:
                _, vmin = element.get_position()
                # draw return the string list corresponding to this element
                element_strings = element.draw()
                # Erase dummy chars with the chars returned by the elements
                for i, string_to_write in enumerate(element_strings):
                    table_strings[vmin + i] += string_to_write
        return "\n".join(table_strings)


class _TableLine(list):

    """
    Abstract parent of _Row and _Column
    """

    def __init__(self, parent_list):
        self._parent_list = parent_list
        self.__minsize_cache = None  # Cached value for performance issue

    def extend(self, elements):
        """
        Let add a list of element to this line
        """
        for element in elements:
            self.append(element)

    def append(self, element):
        """
        Let add an element to this line
        """
        self.check_and_set_parent(element)
        super().append(element)

    def check_and_set_parent(self, element):
        assert isinstance(element, _TableElement), "You can only add _TableElement to _Row and _Column"
        element.set_parent(self)

    @property
    def index(self):
        """
        Return the index of this column
        """
        return self._parent_list.index(self)

    def min_size(self, element_size_accessor):
        """
        Give the width of this column in char
        """
        if self.__minsize_cache is None:
            self.__minsize_cache = max(element_size_accessor(elt) for elt in self)
        return self.__minsize_cache

    def get_near(self, step):
        """
        Give the previous TableElement if step is -1 and the next if step is +1 and so on
        """
        index2 = self.index + step
        if 0 <= index2 < len(self._parent_list):
            return self._parent_list[index2]
        return None


class _Column(_TableLine):

    """
    Represent a column
    Used to navigate between elements and to compute final size
    """

    def __init__(self, table, content=None):
        _TableLine.__init__(self, table.columns)
        if content is not None:
            self.extend(content)

    @property
    def min_width(self):
        """
        Give the width of this column in char
        """
        return self.min_size(lambda elt: elt.min_width)


class _Row(_TableLine):

    """
    Represent a row
    Used to navigate between elements and to compute final size
    """

    def __init__(self, table):
        _TableLine.__init__(self, table.rows)
        self.table = table

    def _add_table_element(self, count, clazz, *args, **kwargs):
        self.extend(clazz(*args, **kwargs) for _ in range(count))
        return self

    def new_cell(self, *args, **kwargs):
        """
        Create a new cell and add it to this row
        Return itself (the row)
        """
        return self._add_table_element(1, _Cell, *args, **kwargs)

    def new_separator(self, count=1, *args, **kwargs):
        """
        Create a new separator and add it to this row
        Return itself (the row)
        """
        return self._add_table_element(count, _Separator, *args, **kwargs)

    def new_double_separator(self, count=1, *args, **kwargs):
        """
        Create a new separator and add it to this row
        Return itself (the row)
        """
        return self._add_table_element(count, _Separator, 2, *args, **kwargs)

    def new_hspan(self, count=1, *args, **kwargs):
        """
        Create a new horizontal span and add it to this row
        Return itself (the row)
        """
        return self._add_table_element(count, _HorizontalSpan, *args, **kwargs)

    def new_vspan(self, count=1, *args, **kwargs):
        """
        Create a new vertical span and add it to this row
        Return itself (the row)
        """
        return self._add_table_element(count, _VerticalSpan, *args, **kwargs)

    @property
    def min_height(self):
        """
        Give the height of this row in char
        """
        return self.min_size(lambda elt: elt.min_height)


class _TableElement(ABC):

    """
    Abstract parent of elements than can be added to a _Row or a _Column :
        - _Cell,
        - _HorizontalSpan,
        - _VerticalSpan
        - _Separator
    """

    """
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    """
    __slots__ = ("row", "column")

    def __init__(self):
        pass

    def set_parent(self, parent):
        if isinstance(parent, _Row):
            self.row = parent
        elif isinstance(parent, _Column):
            self.column = parent
        else:
            assert False, "table element's parent must be a row or a column"

    def _get_up_element(self):
        """
        Do not use, see _Cardinal
        """
        near_row = self.row.get_near(-1)
        if near_row is not None:
            return near_row[self.column.index]
        return None

    def _get_down_element(self):
        """
        Do not use, see _Cardinal
        """
        near_row = self.row.get_near(1)
        if near_row is not None:
            return near_row[self.column.index]
        return None

    def _get_left_element(self):
        """
        Do not use, see _Cardinal
        """
        near_column = self.column.get_near(-1)
        if near_column is not None:
            return near_column[self.row.index]
        return None

    def _get_right_element(self):
        """
        Do not use, see _Cardinal
        """
        near_column = self.column.get_near(1)
        if near_column is not None:
            return near_column[self.row.index]
        return None

    def get_position(self):
        """
        Return the position of this cell in chars
        """
        previous_columns = self.table.columns[0 : self.column.index]
        hpos = sum(column.min_width for column in previous_columns)
        previous_rows = self.table.rows[0 : self.row.index]
        vpos = sum(row.min_height for row in previous_rows)
        return hpos, vpos

    @property
    @abstractmethod
    def min_height(self):
        """
        Give the height of this TableElement in char
        """
        pass

    @property
    @abstractmethod
    def min_width(self):
        """
        Give the width of this TableElement in char
        """
        pass

    @property
    @abstractmethod
    def draw(self, table_strings):
        """
        Return the list of string for this TableElement
        """
        pass

    @property
    def table(self):
        """
        Return the table that own this element
        """
        return self.row.table


@unique
class _Cardinal(Enum):

    """
    Used to navigate from a TableElement to another
    Example:
    With this table:
        ┌───────┬───────┐
        │ Cell1 │ Cell2 │
        ├───────┼───────┤
        │ Cell3 │ Cell4 │
        └───────┴───────┘
    You can get cell2 from cell1 using : _Cardinal.RIGHT(cell1)
    You can get cell1 from cell2 using : _Cardinal.LEFT(cell1)
    You can get cell3 from cell1 using : _Cardinal.DOWN(cell1)
    You can get cell2 from cell4 using : _Cardinal.UP(cell4)
    """

    UP = _TableElement._get_up_element
    RIGHT = _TableElement._get_right_element
    DOWN = _TableElement._get_down_element
    LEFT = _TableElement._get_left_element


_CARDINAL_ORDER = [_Cardinal.UP, _Cardinal.RIGHT, _Cardinal.DOWN, _Cardinal.LEFT]


class _Cell(_TableElement):

    """
    A cell can:
    - contain multiple lines of text
    - be aligned vertically and horizontally
    - be spanned vertically and horizontally
    """

    """
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    """
    __slots__ = ("input_lines", "__output_lines_cache", "halign", "valign")

    def __init__(self, label, halign=HAlign.LEFT, valign=VAlign.TOP):
        _TableElement.__init__(self)
        self.input_lines = str(label).split("\n")
        self.__output_lines_cache = None
        self.halign = halign
        self.valign = valign

    @property
    def output_lines(self):
        if self.__output_lines_cache is None:
            deco_pattern = "{0}"

            # Should add a space before
            if _Cardinal.LEFT(self) is not None:
                deco_pattern = " " + deco_pattern

            # Should add a space after
            next_not_span = self
            for _ in range(self._hspan_count):
                next_not_span = _Cardinal.RIGHT(next_not_span)
            if isinstance(next_not_span, _Separator):
                deco_pattern += " "
            self.__output_lines_cache = [deco_pattern.format(l) for l in self.input_lines]
        return self.__output_lines_cache

    @property
    def min_height(self):
        """
        Give the minimum height of this cell in char
        Span TAKEN into account (so it can be less than the contentHeight)
        """
        return self.content_height

    @property
    def min_width(self):
        """
        Give the minimum width of this cell in char
        Span TAKEN into account (so it can be less than the contentWidth)
        """
        return self.content_width if self._hspan_count == 1 else 1

    @property
    def content_height(self):
        """
        Give the minimum height of this cell in char
        Span NOT taken into account
        """
        return len(self.output_lines)

    @property
    def content_width(self):
        """
        Give the minimum width of this cell in char
        Span NOT taken into account
        """
        return max(map(lambda text: len(remove_ansi_chars(text)), self.output_lines))

    @property
    def _span_height(self):
        row_index = self.row.index
        spanned_rows = self.table.rows[row_index : row_index + self._vspan_count]
        return sum(map(lambda row: row.min_height, spanned_rows))

    @property
    def _span_width(self):
        col_index = self.column.index
        end_span_index = col_index + self._hspan_count
        spanned_columns = self.table.columns[col_index:end_span_index]
        return sum(column.min_width for column in spanned_columns)

    @property
    def _hspan_count(self):
        return self._span_count(_HorizontalSpan, _Cardinal.RIGHT)

    @property
    def _vspan_count(self):
        return self._span_count(_VerticalSpan, _Cardinal.DOWN)

    def _span_count(self, span_class, cardinal):
        element = cardinal(self)
        out = 1
        while isinstance(element, span_class):
            element = cardinal(element)
            out += 1
        return out

    def draw(self):
        """
        Return the list of string for this Cell
        """
        out = self.output_lines

        # Align
        out = self.valign(out, self._span_height)
        out = [self.halign(line, self._span_width, PADDING_CHAR) for line in out]

        return out


class _Span(_TableElement):

    """
    A span is:
    - a like a cell but which do not write any chars in its draw method
    - is only used to compute the size of the cell
    - let merge multiple cells into one (horizontally or vertically)
    """

    """
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    """
    __slots__ = ("cardinal", "__spanned_cell_cache")

    def __init__(self, cardinal):
        _TableElement.__init__(self)
        self.cardinal = cardinal
        self.__spanned_cell_cache = None

    @property
    def min_height(self):
        """
        Give the minimum height of this span in char
        """
        return 1

    @property
    def min_width(self):
        """
        Give the minimum width of this span in char
        """
        return 1

    @property
    def _spanned_cell(self):
        if self.__spanned_cell_cache is None:
            spanned_cell = self
            while not isinstance(spanned_cell, _Cell):
                spanned_cell = self.cardinal(spanned_cell)
            self.__spanned_cell_cache = spanned_cell
        return self.__spanned_cell_cache

    def draw(self):
        """
        Return an empty list because span is only used to calculate columns and rows sizes
        """
        return []


class _HorizontalSpan(_Span):

    """
    A horizontal span is:
    - a like a cell but which do not write any chars in its draw method
    - is only used to compute the size of the cell
    - let merge multiple cells into one (horizontally)
    """

    """
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    """
    __slots__ = ()

    def __init__(self):
        _Span.__init__(self, _Cardinal.LEFT)

    @property
    def min_width(self):
        """
        Give the minimum width of this span in char
        """
        if isinstance(_Cardinal.RIGHT(self), _HorizontalSpan):
            # Put extra space for span only on last one
            return 0

        # Compute space needed for the spanned cell
        span_index = self._spanned_cell.column.index
        self_index = self.column.index
        columns_from_spanned_cell_to_here = self.table.columns[span_index:self_index]
        already_allocated = sum(column.min_width for column in columns_from_spanned_cell_to_here)
        out = self._spanned_cell.content_width - already_allocated
        return out if out > 0 else 0


class _VerticalSpan(_Span):

    """
    A vertical span is:
    - a like a cell but which do not write any chars in its draw method
    - is only used to compute the size of the cell
    - let merge multiple cells into one (vertically)
    """

    """
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    """
    __slots__ = ()

    def __init__(self):
        _Span.__init__(self, _Cardinal.UP)

    @property
    def min_height(self):
        """
        Give the minimum height of this span in char
        """
        if isinstance(_Cardinal.DOWN(self), _VerticalSpan):
            # Put extra space for span only on last one
            return 0

        # Compute space needed for the spanned cell
        rows_from_spanned_cell_to_here = self.table.rows[self._spanned_cell.row.index : self.row.index]
        already_allocated = sum(row.min_height for row in rows_from_spanned_cell_to_here)
        out = self._spanned_cell.content_height - already_allocated
        return out if out > 0 else 0


class _Separator(_TableElement):

    """
    A separator will draw all table separations:
    - it will dynamically compute which char to use and where
    - it can draw a unique char or a string, depending of its position (under another separator or under a large cell)
    """

    """
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    """
    __slots__ = "nb_lines"

    def __init__(self, nb_lines=1):
        _TableElement.__init__(self)
        self.nb_lines = nb_lines

    @property
    def min_height(self):
        """
        Give the minimum height of this separator in char
        """
        return 1

    @property
    def min_width(self):
        """
        Give the minimum width of this separator in char
        """
        return 1

    def _find_sep_char(self):
        """
        Find the char that fit near separators and respect its own style (simple or double)
        """

        # Get the 4 table's elements around this separator in the following order:
        # UP, RIGHT, DOWN, LEFT
        near_elements = [cardinal(self) for cardinal in _CARDINAL_ORDER]

        # In order to avoid collisions between simple and double separator,
        # We need, for each separator, to choose between :
        # - stick to the self separator type
        # - adapt the self separator type to its neighborhood
        # More than 2 and you get surrounded enough to adapt, like a 'glider pattern'
        # So, how many separator in theses table's elements ?
        nb_near_sep = sum(1 for elt in near_elements if isinstance(elt, _Separator))
        should_trust_others = nb_near_sep > 2

        # Now let's count the number of line we need on each cardinal
        def _nb_lines(elt):
            if isinstance(elt, _Separator):
                if should_trust_others:
                    return elt.nb_lines
                else:
                    return self.nb_lines
            else:
                return 0

        # The tuple of theses counts is the key for the char dictionary
        # Do not use a list here, it's not hashable
        key = tuple(map(_nb_lines, near_elements))

        # Get it from the char dictionary
        # If not found, let's put à * to make debug easiest
        return self.table.separators.get(key, "*")

    def draw(self):
        """
        Return the list of String corresponding to this separator
        """
        return [self.table.tm.TABLE_SEPARATOR(self._find_sep_char() * self.column.min_width)] * self.row.min_height
