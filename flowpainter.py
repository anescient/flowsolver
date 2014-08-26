#!/usr/bin/env python

from PyQt4.QtCore import Qt, QPoint, QLine, QSize, QRect
from PyQt4.QtGui import QPainter, QColor, QPen


FlowPalette = {
    1: QColor(255, 0, 0),  # red
    2: QColor(0, 128, 0),  # green
    3: QColor(0, 0, 255),  # blue
    4: QColor(255, 255, 0),  # yellow
    5: QColor(255, 128, 0),  # orange
    6: QColor(0, 255, 255),  # turquoise
    7: QColor(255, 0, 255),  # violet
    8: QColor(165, 44, 41),  # dark red
    9: QColor(128, 0, 128),  # dark violet
    10: QColor(255, 255, 255),  # white
    11: QColor(165, 165, 165),  # grey
    12: QColor(0, 255, 0),  # bright green
    13: QColor(189, 182, 107),  # beige
    14: QColor(0, 0, 140),  # dark blue
    15: QColor(0, 130, 132),  # dark turquoise
    16: QColor(235, 77, 139)}  # pink


class FlowBoardPainter(QPainter):

    _bgcolor = QColor(0, 0, 0)
    _gridcolor = QColor(81, 80, 62)
    _highlightcolor = QColor(34, 51, 44)
    _flowwidth = 0.3

    def __init__(self, target):
        self._target = target
        super(FlowBoardPainter, self).__init__(target)

    def fillBackground(self):
        cm = self.compositionMode()
        self.setCompositionMode(QPainter.CompositionMode_Clear)
        self.fillRect(self._target.rect(), self._bgcolor)
        self.setCompositionMode(cm)
        self.fillRect(self._target.rect(), self._bgcolor)

    def traceBound(self, rect):
        self.setPen(QPen(self._gridcolor, 2, join=Qt.MiterJoin))
        self.drawRect(rect.adjusted(1, 1, -1, -1))

    def drawGrid(self, grid):
        self.setPen(QPen(self._gridcolor, grid.spacing))
        for x in grid.columnSpacingsCenters():
            self.drawLine(x, 0, x, grid.size.width())
        for y in grid.rowSpacingsCenters():
            self.drawLine(0, y, grid.size.height(), y)

    def drawBoardFeatures(self, grid, board):
        for cell, key in board.endpoints:
            rect = grid.cellRect(cell)
            margin = rect.width() // 8
            rect = rect.adjusted(margin, margin, -margin, -margin)
            self.drawEndpoint(rect, key)
        for cell in board.bridges:
            self.drawBridge(grid.cellRect(cell))
        for cell in board.blockages:
            self.drawBlock(grid.cellRect(cell))

    def drawCellHighlight(self, grid, cell):
        self.fillRect(grid.cellRect(cell), self._highlightcolor)

    def drawFlow(self, grid, key, cells):
        assert len(cells) > 1
        linew = int(grid.minDimension * self._flowwidth)
        self.setPen(QPen(FlowPalette[key], linew, \
            cap=Qt.RoundCap, join=Qt.RoundJoin))
        self.drawLines(list(FlowBoardPainter._flowLines(grid, cells)))

    def drawEndpoint(self, rect, key=None, color=None):
        if key is not None:
            color = FlowPalette[key]
        else:
            assert isinstance(color, QColor)
        self.save()
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setBrush(color)
        self.setPen(QPen(Qt.NoPen))
        self.drawEllipse(rect)
        self.restore()

    def drawBridge(self, rect):
        w = rect.width() * (1.0 - self._flowwidth) * 0.5
        self._fillCorners(rect, w, self._gridcolor)
        self._fillCorners(rect, w - 3, self._bgcolor)

    def drawBlock(self, rect):
        self.fillRect(rect, self._gridcolor)

    def _fillCorners(self, rect, width, color):
        corner = QRect(0, 0, width, width)
        corner.moveTopLeft(rect.topLeft())
        self.fillRect(corner, color)
        corner.moveTopRight(rect.topRight())
        self.fillRect(corner, color)
        corner.moveBottomLeft(rect.bottomLeft())
        self.fillRect(corner, color)
        corner.moveBottomRight(rect.bottomRight())
        self.fillRect(corner, color)

    @staticmethod
    def _flowLines(grid, cells):
        assert len(cells) > 1
        cells = FlowBoardPainter._simplifyFlow(cells)
        for start, end in zip(cells, cells[1:]):
            yield QLine(grid.cellCenter(start), \
                        grid.cellCenter(end))

    @staticmethod
    def _simplifyFlow(cells):
        if len(cells) < 3:
            return cells
        simple = cells[:2]
        for cell in cells[2:]:
            (a, b), c = simple[-2:], cell
            colinear = (a[0] == b[0] and b[0] == c[0]) or \
                       (a[1] == b[1] and b[1] == c[1])
            if colinear:
                simple.pop()
            simple.append(cell)
        return simple


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
        self._minheight = min(r[1] - r[0] for r in self._rows)
        self._minwidth = min(c[1] - c[0] for c in self._columns)

    @property
    def size(self):
        return self._size

    @property
    def spacing(self):
        return self._spacing

    @property
    def minDimension(self):
        return min(self._minheight, self._minwidth)

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
