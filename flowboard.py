#!/usr/bin/env python

from PyQt4.QtCore import Qt, QLine, QRect
from PyQt4.QtGui import QPainter, QImage, QColor, QPen


class FlowBoard(object):
    def __init__(self, size=None):
        self._size = size or 7
        self._endpoints = {}  # key: list (length 1 or 2) of 2-tuples
        self._bridges = set()  # 2-tuples

    @property
    def size(self):
        return self._size

    @property
    def endpoints(self):
        for k, l in self._endpoints.iteritems():
            for cell in l:
                yield (cell, k)

    @property
    def endpointPairs(self):
        for k, l in self._endpoints.iteritems():
            if len(l) == 2:
                yield (k, l[0], l[1])

    @property
    def bridges(self):
        for cell in self._bridges:
            yield cell

    def isValid(self):
        keys = self._endpoints.keys()
        if not keys:
            return False
        if not all(self.hasCompleteEndpoints(k) for k in keys):
            return False
        if not all(self.isInnerCell(cell) for cell in self._bridges):
            return False
        return True

    def isInnerCell(self, cell):
        return cell[0] > 0 and cell[0] < self._size - 1 and \
               cell[1] > 0 and cell[1] < self._size - 1

    def hasCompleteEndpoints(self, key):
        return key in self._endpoints and len(self._endpoints[key]) == 2

    def setEndpoint(self, cell, key):
        self.clear(cell)
        l = self._endpoints[key] if key in self._endpoints else []
        l.append(cell)
        if len(l) > 2:
            l.pop(0)
            assert len(l) == 2
        self._endpoints[key] = l

    def setBridge(self, cell):
        assert self.isInnerCell(cell)
        self.clear(cell)
        self._bridges.add(cell)

    def clear(self, cell):
        assert self._includesCell(cell)
        for k, l in self._endpoints.iteritems():
            if cell in l:
                if len(l) == 1:
                    del self._endpoints[k]
                else:
                    l.remove(cell)
                break
        self._bridges.discard(cell)

    def _includesCell(self, cell):
        return cell[0] >= 0 and cell[0] < self._size and \
               cell[1] >= 0 and cell[1] < self._size


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


class FlowBoardPainter(object):

    bgcolor = QColor(0, 0, 0)
    gridcolor = QColor(81, 80, 62)
    flowwidth = 0.4

    def __init__(self, grid):
        self._grid = grid
        self._img = QImage(self._grid.size, QImage.Format_ARGB32_Premultiplied)
        self._highlightcolor = QColor(34, 51, 44)
        QPainter(self._img).fillRect(self._img.rect(), self.bgcolor)

    @property
    def image(self):
        return self._img

    def drawGrid(self):
        ptr = QPainter(self._img)
        ptr.setPen(QPen(self.gridcolor, self._grid.spacing))
        w = self._img.width()
        for x in self._grid.columnSpacingsCenters():
            ptr.drawLine(x, 0, x, w)
        for y in self._grid.rowSpacingsCenters():
            ptr.drawLine(0, y, w, y)

    def drawEndpoints(self, endpoints):
        ptr = QPainter(self._img)
        for cell, key in endpoints:
            rect = self._grid.cellRect(cell)
            margin = rect.width() // 8
            rect = rect.adjusted(margin, margin, -margin, -margin)
            FlowBoardPainter.drawEndpoint(ptr, rect, key)

    def drawBridges(self, bridges):
        ptr = QPainter(self._img)
        for cell in bridges:
            FlowBoardPainter.drawBridge(ptr, self._grid.cellRect(cell))

    def drawCellHighlight(self, cell):
        r = self._grid.cellRect(cell)
        QPainter(self._img).fillRect(r, self._highlightcolor)

    def drawFlow(self, key, cells):
        assert len(cells) > 1
        ptr = QPainter(self._img)
        linew = int(\
            self._grid.cellRect(cells[0]).width() * FlowBoardPainter.flowwidth)
        ptr.setPen(QPen(FlowPalette[key], linew, \
            cap=Qt.RoundCap, join=Qt.RoundJoin))
        ptr.drawLines(self._flowLines(cells))

    def _flowLines(self, cells):
        assert len(cells) > 1
        cells = FlowBoardPainter._simplifyFlow(cells)
        lines = []
        for start, end in zip(cells[:-1], cells[1:]):
            lines.append(QLine(self._grid.cellCenter(start), \
                               self._grid.cellCenter(end)))
        return lines

    @staticmethod
    def drawEndpoint(ptr, rect, key):
        ptr.save()
        ptr.setRenderHint(QPainter.Antialiasing, True)
        ptr.setBrush(FlowPalette[key])
        ptr.setPen(QPen(Qt.NoPen))
        ptr.drawEllipse(rect)
        ptr.restore()

    @staticmethod
    def drawBridge(ptr, rect):
        w = rect.width() * FlowBoardPainter.flowwidth
        FlowBoardPainter._fillCorners(ptr, rect, w, \
            FlowBoardPainter.gridcolor)
        FlowBoardPainter._fillCorners(ptr, rect, w - 3, \
            FlowBoardPainter.bgcolor)

    @staticmethod
    def _simplifyFlow(cells):
        if len(cells) < 3:
            return cells
        simple = cells[:2]
        for cell in cells[2:]:
            a, b, c = simple[-2], simple[-1], cell
            colinear = (a[0] == b[0] and b[0] == c[0]) or \
                       (a[1] == b[1] and b[1] == c[1])
            if colinear:
                simple.pop()
            simple.append(cell)
        return simple

    @staticmethod
    def _fillCorners(ptr, rect, width, color):
        corner = QRect(0, 0, width, width)
        corner.moveTopLeft(rect.topLeft())
        ptr.fillRect(corner, color)
        corner.moveTopRight(rect.topRight())
        ptr.fillRect(corner, color)
        corner.moveBottomLeft(rect.bottomLeft())
        ptr.fillRect(corner, color)
        corner.moveBottomRight(rect.bottomRight())
        ptr.fillRect(corner, color)
