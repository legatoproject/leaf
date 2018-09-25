'''
Generate an ASCII table
Support the followings features:
    - multiple lines cells
    - horizontal and vertical alignment
    - horizontal and vertical spanning
    - simple, double or invisible horizontal and vertical separators
    - can be turned to a multiline string using str()

Example:
    table = Table()
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
@copyright: 2018 Sierra Wireless. All rights reserved.
@contact:   Legato Tooling Team <letools@sierrawireless.com>
@license:   https://www.mozilla.org/en-US/MPL/2.0/
'''
from abc import ABC, abstractmethod

from enum import unique, Enum

from leaf.format.alignment import HAlign, VAlign
from leaf.format.ansi import removeAnsiChars
from leaf.format.chars import PADDING_CHAR, getSeparators
from leaf.format.theme import ThemeManager


class Table():
    '''
    Represent the table
    '''

    def __init__(self, themeManager=ThemeManager()):
        self.tm = themeManager
        self.rows = []
        self.columns = []
        self.separators = getSeparators()
        self.removedColumnsIndexes = set()

    def newRow(self):
        '''
        Add a new row in the table and return it
        '''
        out = _Row(self)
        self.rows.append(out)
        return out

    def newHeader(self, text, tableSize):
        '''
        Add header to the given Table like that:
        ┌──────────────────────────────────────────────────────────────────┐
        │                               text                               │
        ├──────────────────────────────────────────────────────────────────┤
        '''
        self.newRow().newSep(tableSize)
        self.newRow().newSep() \
            .newCell(text, HAlign.CENTER).newHSpan(tableSize - 3).newSep()
        self.newRow().newSep(tableSize)

    @property
    def minHeight(self):
        '''
        Give the height of the table in char
        '''
        return sum(row.minHeight for row in self.rows)

    @property
    def minWidth(self):
        '''
        Give the width of the table in char
        '''
        return sum(column.minWidth for column in self.columns)

    def _checkTable(self):
        '''
        Check the table model coherence
        This can help developer to use this API
        '''
        nbEltByRow = [len(row) for row in self.rows]
        assert min(nbEltByRow) == max(nbEltByRow), \
            "Number of elements is not the same on each row: " + \
            str(nbEltByRow)
        for row in self.rows:
            for elt in row:
                if isinstance(elt, _HorizontalSpan):
                    assert isinstance(_Cardinal.LEFT(elt), (_Cell, _HorizontalSpan)), \
                        "An horizontal span must follow another or a cell (not a separator)"
                if isinstance(elt, _VerticalSpan):
                    assert isinstance(_Cardinal.UP(elt), (_Cell, _VerticalSpan)), \
                        "An vertical span must be under another or a cell (not a separator)"

    def removeColumns(self, colIdSet):
        self.removedColumnsIndexes.update(colIdSet)

    def __str__(self):
        # Create columns
        self.columns.clear()
        self.columns.extend(_Column(self, columnCells)
                            for columnCells in zip(*self.rows))

        # Remove removed columns
        for index in sorted(self.removedColumnsIndexes, reverse=True):
            # Simply delete hidden columns
            del self.columns[index]
            # For each row, delete the cell which is the hidden column
            for row in self.rows:
                del row[index]

        # check table coherence
        self._checkTable()

        # Prepare char table with final size using dummy '*' char (useful to
        # debug a layout issue)
        tableStrings = [""] * self.minHeight
        for col in self.columns:
            for elt in col:
                _, vMin = elt.getPosition()
                # draw return the string list corresponding to this element
                eltStrings = elt.draw()
                # Erase dummy chars with the chars returned by the elements
                for i, stringToWrite in enumerate(eltStrings):
                    tableStrings[vMin + i] += stringToWrite
        return "\n".join(tableStrings)


class _TableLine(list):
    '''
    Abstract parent of _Row and _Column
    '''

    def __init__(self, parentList):
        self._parentList = parentList
        self.__minSize_cache = None  # Cached value for performance issue

    def extend(self, newElts):
        '''
        Let add a list of element to this line
        '''
        for newElt in newElts:
            self.append(newElt)

    def append(self, newElt):
        '''
        Let add an element to this line
        '''
        self.checkAndSetParent(newElt)
        super().append(newElt)

    def checkAndSetParent(self, newElt):
        assert isinstance(newElt, _TableElement), \
            "You can only add _TableElement to _Row and _Column"
        newElt.setParent(self)

    @property
    def index(self):
        '''
        Return the index of this column
        '''
        return self._parentList.index(self)

    def minSize(self, eltSizeAccessor):
        '''
        Give the width of this column in char
        '''
        if self.__minSize_cache is None:
            self.__minSize_cache = max(eltSizeAccessor(elt) for elt in self)
        return self.__minSize_cache

    def getNear(self, step):
        '''
        Give the previous TableElement if step is -1 and the next if step is +1 and so on
        '''
        newIndex = self.index + step
        if 0 <= newIndex < len(self._parentList):
            return self._parentList[newIndex]
        return None


class _Column(_TableLine):
    '''
    Represent a column
    Used to navigate between elements and to compute final size
    '''

    def __init__(self, table, content=None):
        _TableLine.__init__(self, table.columns)
        if content is not None:
            self.extend(content)

    @property
    def minWidth(self):
        '''
        Give the width of this column in char
        '''
        return self.minSize(lambda elt: elt.minWidth)


class _Row(_TableLine):
    '''
    Represent a row
    Used to navigate between elements and to compute final size
    '''

    def __init__(self, table):
        _TableLine.__init__(self, table.rows)
        self.table = table

    def _addTableElement(self, count, clazz, *args, **kwargs):
        self.extend(clazz(*args, **kwargs) for _ in range(count))
        return self

    def newCell(self, *args, **kwargs):
        '''
        Create a new cell and add it to this row
        Return itself (the row)
        '''
        return self._addTableElement(1, _Cell, *args, **kwargs)

    def newSep(self, count=1, *args, **kwargs):
        '''
        Create a new separator and add it to this row
        Return itself (the row)
        '''
        return self._addTableElement(count, _Separator, *args, **kwargs)

    def newDblSep(self, count=1, *args, **kwargs):
        '''
        Create a new separator and add it to this row
        Return itself (the row)
        '''
        return self._addTableElement(count, _Separator, 2, *args, **kwargs)

    def newHSpan(self, count=1, *args, **kwargs):
        '''
        Create a new horizontal span and add it to this row
        Return itself (the row)
        '''
        return self._addTableElement(count, _HorizontalSpan, *args, **kwargs)

    def newVSpan(self, count=1, *args, **kwargs):
        '''
        Create a new vertical span and add it to this row
        Return itself (the row)
        '''
        return self._addTableElement(count, _VerticalSpan, *args, **kwargs)

    @property
    def minHeight(self):
        '''
        Give the height of this row in char
        '''
        return self.minSize(lambda elt: elt.minHeight)


class _TableElement(ABC):
    '''
    Abstract parent of elements than can be added to a _Row or a _Column :
        - _Cell,
        - _HorizontalSpan,
        - _VerticalSpan
        - _Separator
    '''

    '''
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    '''
    __slots__ = ('row', 'column')

    def __init__(self):
        pass

    def setParent(self, parent):
        if isinstance(parent, _Row):
            self.row = parent
        elif isinstance(parent, _Column):
            self.column = parent
        else:
            assert False, "table element's parent must be a row or a column"

    def _getUpElement(self):
        '''
        Do not use, see _Cardinal
        '''
        nearRow = self.row.getNear(-1)
        if nearRow is not None:
            return nearRow[self.column.index]
        return None

    def _getDownElement(self):
        '''
        Do not use, see _Cardinal
        '''
        nearRow = self.row.getNear(1)
        if nearRow is not None:
            return nearRow[self.column.index]
        return None

    def _getLeftElement(self):
        '''
        Do not use, see _Cardinal
        '''
        nearColumn = self.column.getNear(-1)
        if nearColumn is not None:
            return nearColumn[self.row.index]
        return None

    def _getRightElement(self):
        '''
        Do not use, see _Cardinal
        '''
        nearColumn = self.column.getNear(1)
        if nearColumn is not None:
            return nearColumn[self.row.index]
        return None

    def getPosition(self):
        '''
        Return the position of this cell in chars
        '''
        previousColumns = self.table.columns[0:self.column.index]
        hPosition = sum(column.minWidth for column in previousColumns)
        previousRows = self.table.rows[0:self.row.index]
        vPosition = sum(row.minHeight for row in previousRows)
        return hPosition, vPosition

    @property
    @abstractmethod
    def minHeight(self):
        '''
        Give the height of this TableElement in char
        '''
        pass

    @property
    @abstractmethod
    def minWidth(self):
        '''
        Give the width of this TableElement in char
        '''
        pass

    @property
    @abstractmethod
    def draw(self, tableStrings):
        '''
        Return the list of string for this TableElement
        '''
        pass

    @property
    def table(self):
        '''
        Return the table that own this element
        '''
        return self.row.table


@unique
class _Cardinal(Enum):
    '''
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
    '''
    UP = _TableElement._getUpElement
    RIGHT = _TableElement._getRightElement
    DOWN = _TableElement._getDownElement
    LEFT = _TableElement._getLeftElement


_CARDINAL_ORDER = [_Cardinal.UP,
                   _Cardinal.RIGHT,
                   _Cardinal.DOWN,
                   _Cardinal.LEFT]


class _Cell(_TableElement):
    '''
    A cell can:
    - contain multiple lines of text
    - be aligned vertically and horizontally
    - be spanned vertically and horizontally
    '''

    '''
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    '''
    __slots__ = ('inputLines', '__outputLines_cache', 'hAlign', 'vAlign')

    def __init__(self, label, hAlign=HAlign.LEFT, vAlign=VAlign.TOP):
        _TableElement.__init__(self)
        self.inputLines = str(label).split('\n')
        self.__outputLines_cache = None
        self.hAlign = hAlign
        self.vAlign = vAlign

    @property
    def outputLines(self):
        if self.__outputLines_cache is None:
            decoPattern = "%s"

            # Should add a space before
            if _Cardinal.LEFT(self) is not None:
                decoPattern = " " + decoPattern

            # Should add a space after
            nextEltWhichIsNotSpan = self
            for _ in range(self._hSpanCount):
                nextEltWhichIsNotSpan = _Cardinal.RIGHT(nextEltWhichIsNotSpan)
            if isinstance(nextEltWhichIsNotSpan, _Separator):
                decoPattern += " "
            self.__outputLines_cache = \
                [decoPattern % l for l in self.inputLines]
        return self.__outputLines_cache

    @property
    def minHeight(self):
        '''
        Give the minimum height of this cell in char
        Span TAKEN into account (so it can be less than the contentHeight)
        '''
        return self.contentHeight

    @property
    def minWidth(self):
        '''
        Give the minimum width of this cell in char
        Span TAKEN into account (so it can be less than the contentWidth)
        '''
        return self.contentWidth if self._hSpanCount == 1 else 1

    @property
    def contentHeight(self):
        '''
        Give the minimum height of this cell in char
        Span NOT taken into account
        '''
        return len(self.outputLines)

    @property
    def contentWidth(self):
        '''
        Give the minimum width of this cell in char
        Span NOT taken into account
        '''
        return max(map(lambda text: len(removeAnsiChars(text)), self.outputLines))

    @property
    def _spanHeight(self):
        rowIndex = self.row.index
        spannedRows = self.table.rows[rowIndex:rowIndex + self._vSpanCount]
        return sum([row.minHeight for row in spannedRows])

    @property
    def _spanWidth(self):
        colIndex = self.column.index
        endSpanIndex = colIndex + self._hSpanCount
        spannedColumns = self.table.columns[colIndex:endSpanIndex]
        return sum(column.minWidth for column in spannedColumns)

    @property
    def _hSpanCount(self):
        return self._spanCount(_HorizontalSpan, _Cardinal.RIGHT)

    @property
    def _vSpanCount(self):
        return self._spanCount(_VerticalSpan, _Cardinal.DOWN)

    def _spanCount(self, spanClass, cardinal):
        elt = cardinal(self)
        nbSpan = 1
        while isinstance(elt, spanClass):
            elt = cardinal(elt)
            nbSpan += 1
        return nbSpan

    def draw(self):
        '''
        Return the list of string for this Cell
        '''
        out = self.outputLines

        # Align
        out = self.vAlign(out, self._spanHeight)
        out = [self.hAlign(line, self._spanWidth, PADDING_CHAR)
               for line in out]

        return out


class _Span(_TableElement):
    '''
    A span is:
    - a like a cell but which do not write any chars in its draw method
    - is only used to compute the size of the cell
    - let merge multiple cells into one (horizontally or vertically)
    '''

    '''
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    '''
    __slots__ = ('cardinal', '__spannedCell_cache')

    def __init__(self, cardinal):
        _TableElement.__init__(self)
        self.cardinal = cardinal
        self.__spannedCell_cache = None

    @property
    def minHeight(self):
        '''
        Give the minimum height of this span in char
        '''
        return 1

    @property
    def minWidth(self):
        '''
        Give the minimum width of this span in char
        '''
        return 1

    @property
    def _spannedCell(self):
        if self.__spannedCell_cache is None:
            newSpannedCell = self
            while not isinstance(newSpannedCell, _Cell):
                newSpannedCell = self.cardinal(newSpannedCell)
            self.__spannedCell_cache = newSpannedCell
        return self.__spannedCell_cache

    def draw(self):
        '''
        Return an empty list because span is only used to calculate columns and rows sizes
        '''
        return []


class _HorizontalSpan(_Span):
    '''
    A horizontal span is:
    - a like a cell but which do not write any chars in its draw method
    - is only used to compute the size of the cell
    - let merge multiple cells into one (horizontally)
    '''

    '''
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    '''
    __slots__ = ()

    def __init__(self):
        _Span.__init__(self, _Cardinal.LEFT)

    @property
    def minWidth(self):
        '''
        Give the minimum width of this span in char
        '''
        if isinstance(_Cardinal.RIGHT(self), _HorizontalSpan):
            # Put extra space for span only on last one
            return 0

        # Compute space needed for the spanned cell
        spanIndex = self._spannedCell.column.index
        selfIndex = self.column.index
        columnsFromSpannedCellToHere = self.table.columns[spanIndex:selfIndex]
        alreadyAllocated = \
            sum(column.minWidth for column in columnsFromSpannedCellToHere)
        needed = self._spannedCell.contentWidth - alreadyAllocated
        if needed < 0:
            return 0
        return needed


class _VerticalSpan(_Span):
    '''
    A vertical span is:
    - a like a cell but which do not write any chars in its draw method
    - is only used to compute the size of the cell
    - let merge multiple cells into one (vertically)
    '''

    '''
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    '''
    __slots__ = ()

    def __init__(self):
        _Span.__init__(self, _Cardinal.UP)

    @property
    def minHeight(self):
        '''
        Give the minimum height of this span in char
        '''
        if isinstance(_Cardinal.DOWN(self), _VerticalSpan):
            # Put extra space for span only on last one
            return 0

        # Compute space needed for the spanned cell
        rowsFromSpannedCellToHere = self.table.rows[self._spannedCell.row.index:self.row.index]
        alreadyAllocated = \
            sum(row.minHeight for row in rowsFromSpannedCellToHere)
        needed = self._spannedCell.contentHeight - alreadyAllocated
        if needed < 0:
            return 0
        return needed


class _Separator(_TableElement):
    '''
    A separator will draw all table separations:
    - it will dynamically compute which char to use and where
    - it can draw a unique char or a string, depending of its position (under another separator or under a large cell)
    '''

    '''
    Some big tables can have many elements, and performance and memory consumption can quickly become critical.
    Thats why, for theses elements, we store only needed attributes instead of __dict__ in order to get:
    - faster attribute access.
    - space savings in memory.
    '''
    __slots__ = ('nbLines')

    def __init__(self, nbLines=1):
        _TableElement.__init__(self)
        self.nbLines = nbLines

    @property
    def minHeight(self):
        '''
        Give the minimum height of this separator in char
        '''
        return 1

    @property
    def minWidth(self):
        '''
        Give the minimum width of this separator in char
        '''
        return 1

    def _findSepChar(self):
        '''
        Find the char that fit near separators and respect its own style (simple or double)
        '''

        # Get the 4 table's elements around this separator in the following order:
        # UP, RIGHT, DOWN, LEFT
        nearElts = [cardinal(self) for cardinal in _CARDINAL_ORDER]

        # In order to avoid collisions between simple and double separator,
        # We need, for each separator, to choose between :
        # - stick to the self separator type
        # - adapt the self separator type to its neighborhood
        # More than 2 and you get surrounded enough to adapt, like a 'glider pattern'
        # So, how many separator in theses table's elements ?
        nbNearSep = sum(1 for elt in nearElts if isinstance(elt, _Separator))
        shouldTrustOthers = nbNearSep > 2

        # Now let's count the number of line we need on each cardinal
        def _nbLines(elt):
            if isinstance(elt, _Separator):
                if shouldTrustOthers:
                    return elt.nbLines
                else:
                    return self.nbLines
            else:
                return 0

        # The tuple of theses counts is the key for the char dictionary
        # Do not use a list here, it's not hashable
        key = tuple(map(_nbLines, nearElts))

        # Get it from the char dictionary
        # If not found, let's put à * to make debug easiest
        return self.table.separators.get(key, "*")

    def draw(self):
        '''
        Return the list of String corresponding to this separator
        '''
        return [self.table.tm.TABLE_SEPARATOR(self._findSepChar() * self.column.minWidth)] * self.row.minHeight
