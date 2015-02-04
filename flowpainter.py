#!/usr/bin/env python

from itertools import product
from PyQt4.QtCore import Qt, QPoint, QLine, QSize, QRect, QRectF
from PyQt4.QtGui import QPainter, QColor, QBrush, QPen, QImage, \
    QRadialGradient, QPainterPath


# values ((r, g, b), (r, g, b))
# The first color is used to render endpoints and paths.
# The second color is the corresponding background/highlight.
# The game allocates these colors to endpoint pairs in this order.
FlowPalette = [
    ((100, 100, 55), (0, 0, 0)),  # grid and normal background
    ((255, 0, 0), (114, 57, 57)),  # red
    ((0, 128, 0), (57, 85, 57)),  # green
    ((0, 0, 255), (57, 57, 114)),  # blue
    ((238, 238, 0), (110, 110, 57)),  # yellow
    ((255, 128, 0), (114, 85, 57)),  # orange
    ((0, 255, 255), (57, 114, 114)),  # turquoise
    ((255, 0, 255), (114, 57, 114)),  # violet
    ((165, 42, 42), (95, 66, 66)),  # dark red
    ((128, 0, 128), (85, 57, 85)),  # dark violet
    ((255, 255, 255), (114, 114, 114)),  # white
    ((165, 165, 165), (95, 95, 95)),  # grey
    ((0, 255, 0), (57, 114, 57)),  # bright green
    ((189, 182, 107), (100, 98, 81)),  # beige
    ((0, 0, 140), (63, 57, 88)),  # dark blue
    ((0, 128, 128), (57, 85, 85)),  # dark turquoise
    ((255, 20, 147), (114, 61, 90))]  # pink

QFlowPalette = [tuple(QColor(*rgb) for rgb in entry) for entry in FlowPalette]


def _styleAlphaBrush(color, style=None, alpha=None):
    if alpha is not None:
        color = QColor(color)
        color.setAlphaF(alpha)
    return QBrush(color, style) if style else color


class FlowBoardPainter(QPainter):

    _flowwidth = 0.33

    def __init__(self, target):
        self._target = target
        super(FlowBoardPainter, self).__init__(target)

    def fillBackground(self):
        fillcolor = QFlowPalette[0][1]
        cm = self.compositionMode()
        self.setCompositionMode(QPainter.CompositionMode_Clear)
        self.fillRect(self._target.rect(), fillcolor)
        self.setCompositionMode(cm)
        self.fillRect(self._target.rect(), fillcolor)

    def traceBound(self, rect):
        self.setPen(QPen(QFlowPalette[0][0], 2, join=Qt.MiterJoin))
        self.drawRect(rect.adjusted(1, 1, -1, -1))

    def drawGrid(self, grid):
        self.setPen(QPen(QFlowPalette[0][0], grid.spacing))
        for x in grid.columnSpacingsCenters():
            self.drawLine(x, 0, x, grid.size.width())
        for y in grid.rowSpacingsCenters():
            self.drawLine(0, y, grid.size.height(), y)

    def drawBoardFeatures(self, grid, board):
        for cell, key in board.endpoints:
            rect = grid.cellRect(cell)
            self.drawEndpoint(rect, key)
        for cell in board.bridges:
            rect = grid.cellRect(cell)
            self.drawBridge(rect)
        for cell in board.blockages:
            rect = grid.cellRect(cell)
            self.drawBlock(rect)

    def drawFlowHighlights(self, grid, solver):
        for key, cells in solver.getFlows():
            c = QColor(QFlowPalette[key][1])
            c.setAlphaF(0.8)
            for cell in cells:
                self.fillRect(grid.cellRect(cell), c)

    def drawFlows(self, grid, solver):
        for key, cells in solver.getFlows():
            if len(cells) > 1:
                self._drawFlow(grid, key, cells)

    def _drawFlow(self, grid, key, cells):
        assert len(cells) > 1
        linew = int(grid.minDimension * self._flowwidth)
        self.setPen(QPen(QFlowPalette[key][0], linew,
                    cap=Qt.RoundCap, join=Qt.RoundJoin))
        self.drawLines(list(FlowBoardPainter._flowLines(grid, cells)))

    def drawEndpoint(self, rect, key=None, color=None, style=None, scale=None):
        if key is not None:
            color = QFlowPalette[key][0]
        else:
            assert isinstance(color, QColor)
        rect = FlowBoardPainter._endpointRect(rect, scale)
        self.save()
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setBrush(_styleAlphaBrush(color, style, None))
        self.setPen(QPen(Qt.NoPen))
        self.drawEllipse(rect)
        self.restore()

    def drawEndpointGlow(self, rect, key, scale=None):
        color = QFlowPalette[key][0]
        rect = FlowBoardPainter._endpointRect(rect, scale)
        gradient = QRadialGradient(QRectF(rect).center(), rect.width() / 2)
        bg = QColor(color)
        bg.setAlphaF(0.3)
        gradient.setColorAt(0.5, bg)
        gradient.setColorAt(1.0, color)
        self.save()
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setBrush(QBrush(gradient))
        self.setPen(QPen(color, 1))
        self.drawEllipse(rect)
        self.restore()

    def drawBridge(self, rect, style=None, alpha=None):
        brush = _styleAlphaBrush(QFlowPalette[0][0], style, alpha)
        self.setPen(QPen(brush, 2, cap=Qt.SquareCap, join=Qt.MiterJoin))
        mindim = int(min(rect.width(), rect.height()))
        gapw = int(mindim * (1 - self._flowwidth) / 2)
        x1 = rect.left() + gapw - 1
        y1 = rect.top() + gapw - 1
        x2 = rect.right() - rect.width() + mindim - gapw + 1
        y2 = rect.bottom() - rect.height() + mindim - gapw + 1
        path = QPainterPath()
        for xx, yy in product([(rect.left(), x1), (rect.right(), x2)],
                              [(rect.top(), y1), (rect.bottom(), y2)]):
            path.moveTo(xx[0], yy[1])
            path.lineTo(xx[1], yy[1])
            path.lineTo(xx[1], yy[0])
        self.drawPath(path)

    def clearBlock(self, rect, style=None, alpha=None):
        brush = _styleAlphaBrush(QFlowPalette[0][1], style, alpha)
        self.fillRect(rect, brush)

    def drawBlock(self, rect, style=None, alpha=None):
        brush = _styleAlphaBrush(QFlowPalette[0][0], style, alpha)
        self.fillRect(rect, brush)

    @staticmethod
    def endpointKeys():
        return range(1, len(FlowPalette))

    @staticmethod
    def renderImage(board, solver=None):
        cellsize = 33
        spacing = 1
        imgsize = board.size * (cellsize + spacing) + spacing
        imgsize = QSize(imgsize, imgsize)
        img = QImage(imgsize, QImage.Format_ARGB32_Premultiplied)
        grid = SpacedGrid(board.size, board.size, imgsize, spacing)
        ptr = FlowBoardPainter(img)
        ptr.fillBackground()
        if solver and solver.solved:
            ptr.drawFlowHighlights(grid, solver)
        ptr.drawGrid(grid)
        ptr.drawBoardFeatures(grid, board)
        if solver:
            ptr.drawFlows(grid, solver)
        ptr.end()
        return img.convertToFormat(QImage.Format_RGB32)

    @staticmethod
    def _endpointRect(rect, scale=None):
        scale = scale or 0.75
        dw = 0  # total width adjust
        dh = 0  # total height adjust
        if rect.width() > rect.height():
            dw -= (rect.width() - rect.height())
        elif rect.height() > rect.width():
            dh -= (rect.height() - rect.width())
        dw -= (1.0 - scale) * (rect.width() + dw)
        dh -= (1.0 - scale) * (rect.height() + dh)
        return rect.adjusted(-dw / 2, -dh / 2, dw / 2, dh / 2)

    @staticmethod
    def _flowLines(grid, cells):
        assert len(cells) > 1
        cells = FlowBoardPainter._simplifyFlow(cells)
        for start, end in zip(cells, cells[1:]):
            yield QLine(grid.cellCenter(start), grid.cellCenter(end))

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
        self._rows = \
            list(SpacedGrid._divideRange(0, size.height(), rows, spacing))
        self._columns = \
            list(SpacedGrid._divideRange(0, size.width(), columns, spacing))
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
            yield (spacing + i * lastmax / divisions,
                   (i + 1) * lastmax / divisions - 1)
