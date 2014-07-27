#!/usr/bin/env python

from PyQt4.QtCore import QPoint, QSize, QRect


# when dividing an integer-sized rectangle into a regular grid with
# integer-sized cells, all cells might not have identical size
class SpacedGrid(object):
    def __init__(self, rows, columns, size, spacing):
        assert rows > 0 and columns > 0
        assert isinstance(size, QSize)
        assert size.width() > 0 and size.height() > 0
        self._size = size
        assert spacing == int(spacing)
        self._spacing = int(spacing)
        self._rows = list(SpacedGrid._divideRange(\
            0, size.height(), rows, spacing))
        self._columns = list(SpacedGrid._divideRange(\
            0, size.width(), columns, spacing))

    @property
    def size(self):
        return self._size

    @property
    def spacing(self):
        return self._spacing

    def rowSpacings(self):
        return self._spacings(self._rows)

    def rowSpacingsCenters(self):
        return SpacedGrid._centers(self.rowSpacings())

    def columnSpacings(self):
        return self._spacings(self._columns)

    def columnSpacingsCenters(self):
        return SpacedGrid._centers(self.columnSpacings())

    def cellRect(self, cell):
        c = self._columns[cell[0]]
        r = self._rows[cell[1]]
        return QRect(QPoint(c[0], r[0]), QPoint(c[1], r[1]))

    def cellCenter(self, cell):
        return self.cellRect(cell).center()

    def findCell(self, point):
        ci = SpacedGrid._searchRanges(self._columns, point.x())
        if ci is None:
            return None
        ri = SpacedGrid._searchRanges(self._rows, point.y())
        if ri is None:
            return None
        return (ci, ri)

    def _spacings(self, ranges):
        """
            yield 'divisions + 1' 2-tuples
            each tuple is (inclusive min, exclusive max)
        """
        yield (0, self._spacing)
        for r in ranges:
            yield (r[1] + 1, r[1] + 1 + self._spacing)

    @staticmethod
    def _centers(ranges):
        return (r[0] + (r[1] - r[0]) * 0.5 for r in ranges)

    @staticmethod
    def _searchRanges(ranges, value):
        for i, r in enumerate(ranges):
            if value >= r[0] and value <= r[1]:
                return i
        return None

    @staticmethod
    def _divideRange(start, end, divisions, spacing):
        """
            yield a sequence of 'divisions' 2-tuples
            each tuple is (inclusive min, inclusive max)
        """
        lastmax = (end - start) - spacing
        for i in xrange(divisions):
            yield (spacing + i * lastmax / divisions, \
                   (i + 1) * lastmax / divisions - 1)
