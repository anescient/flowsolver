#!/usr/bin/env python

from PyQt4.QtCore import Qt, QLine, QRect
from PyQt4.QtGui import QPainter, QImage, QColor, QPen
from graph import QueryableSimpleGraph
from gridgraph import GraphOntoRectangularGrid


class FlowBoard(object):
    def __init__(self, size=None):
        self._size = size or 7
        self._endpoints = {}  # key: list (length 1 or 2) of 2-tuples
        self._bridges = set()  # 2-tuples
        self._blockages = set()  # 2-tuples

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
            assert self.hasCompleteEndpoints(k)
            yield (k, tuple(l))

    @property
    def bridges(self):
        return iter(self._bridges)

    @property
    def blockages(self):
        return iter(self._blockages)

    def isValid(self):
        if not self._endpoints:
            return False
        if not all(self.hasCompleteEndpoints(k) for k in self._endpoints):
            return False
        if not all(self.bridgeValidAt(cell) for cell in self._bridges):
            return False
        if not all(self.blockageValidAt(cell) for cell in self._blockages):
            return False
        return True

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

    def endpointKeyAt(self, cell):
        assert self._includesCell(cell)
        for k, l in self._endpoints.iteritems():
            if cell in l:
                return k
        return None

    def bridgeValidAt(self, cell):
        return len(self._adjacentUnblockedCells(cell)) == 4

    def setBridge(self, cell):
        assert self.bridgeValidAt(cell)
        self.clear(cell)
        self._bridges.add(cell)

    def hasBridgeAt(self, cell):
        return cell in self._bridges

    def blockageValidAt(self, cell):
        return not self._bridges.intersection(self._adjacentCells(cell))

    def setBlockage(self, cell):
        assert self.blockageValidAt(cell)
        self.clear(cell)
        self._blockages.add(cell)

    def hasBlockageAt(self, cell):
        return cell in self._blockages

    def clear(self, cell):
        assert self._includesCell(cell)
        for k, l in self._endpoints.iteritems():
            if cell in l:
                l.remove(cell)
                if not l:
                    del self._endpoints[k]
                break
        self._bridges.discard(cell)
        self._blockages.discard(cell)

    def _includesCell(self, cell):
        return cell[0] >= 0 and cell[0] < self._size and \
               cell[1] >= 0 and cell[1] < self._size

    def _adjacentUnblockedCells(self, cell):
        return set(self._adjacentCells(cell)) - self._blockages

    def _adjacentCells(self, cell):
        if cell[0] > 0:
            yield (cell[0] - 1, cell[1])
        if cell[0] < self._size - 1:
            yield (cell[0] + 1, cell[1])
        if cell[1] > 0:
            yield (cell[0], cell[1] - 1)
        if cell[1] < self._size - 1:
            yield (cell[0], cell[1] + 1)

    @staticmethod
    def _adjacent(cell1, cell2):
        return (abs(cell1[0] - cell2[0]) == 1) != \
               (abs(cell1[1] - cell2[1]) == 1)


class FlowBoardGraph(QueryableSimpleGraph):
    def __init__(self, board):
        gridgraph = GraphOntoRectangularGrid(board.size)

        for xy in board.blockages:
            gridgraph.removeVertexAt(xy)

        for xy in board.bridges:
            x, y = xy
            v = gridgraph.singleVertexAt(xy)

            x_adj = gridgraph.adjacenciesAt(xy).intersection(\
                gridgraph.verticesAt((x - 1, y)).union(\
                gridgraph.verticesAt((x + 1, y))))
            y_adj = gridgraph.adjacenciesAt(xy).intersection(\
                gridgraph.verticesAt((x, y - 1)).union(\
                gridgraph.verticesAt((x, y + 1))))
            assert len(x_adj) == 2 and len(y_adj) == 2

            xpass = gridgraph.pushVertex(xy)
            gridgraph.addEdge(x_adj.pop(), xpass)
            gridgraph.addEdge(x_adj.pop(), xpass)

            ypass = gridgraph.pushVertex(xy)
            gridgraph.addEdge(y_adj.pop(), ypass)
            gridgraph.addEdge(y_adj.pop(), ypass)

            gridgraph.removeVertex(v)

        self._cellToVertex = gridgraph.singleVertexAt
        self._vertexToCell = gridgraph.locationForVertex
        super(FlowBoardGraph, self).__init__(gridgraph.graph.copyEdgeSets())

    def cellToVertex(self, cell):
        return self._cellToVertex(cell)

    def vertexToCell(self, v):
        return self._vertexToCell(v)

    def verticesToCells(self, vseq):
        return list(map(self._vertexToCell, vseq))


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
    flowwidth = 0.3

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

    def drawBoardFeatures(self, board):
        ptr = QPainter(self._img)
        for cell, key in board.endpoints:
            rect = self._grid.cellRect(cell)
            margin = rect.width() // 8
            rect = rect.adjusted(margin, margin, -margin, -margin)
            FlowBoardPainter.drawEndpoint(ptr, rect, key)
        for cell in board.bridges:
            FlowBoardPainter.drawBridge(ptr, self._grid.cellRect(cell))
        for cell in board.blockages:
            FlowBoardPainter.drawBlock(ptr, self._grid.cellRect(cell))

    def drawCellHighlight(self, cell):
        r = self._grid.cellRect(cell)
        QPainter(self._img).fillRect(r, self._highlightcolor)

    def drawFlow(self, key, cells):
        assert len(cells) > 1
        ptr = QPainter(self._img)
        linew = int(self._grid.minDimension * self.flowwidth)
        ptr.setPen(QPen(FlowPalette[key], linew, \
            cap=Qt.RoundCap, join=Qt.RoundJoin))
        ptr.drawLines(list(self._flowLines(cells)))

    def _flowLines(self, cells):
        assert len(cells) > 1
        cells = FlowBoardPainter._simplifyFlow(cells)
        for start, end in zip(cells[:-1], cells[1:]):
            yield QLine(self._grid.cellCenter(start), \
                        self._grid.cellCenter(end))

    @staticmethod
    def drawEndpoint(ptr, rect, key):
        ptr.save()
        ptr.setRenderHint(QPainter.Antialiasing, True)
        ptr.setBrush(FlowPalette[key])
        ptr.setPen(QPen(Qt.NoPen))
        ptr.drawEllipse(rect)
        ptr.restore()

    @classmethod
    def drawBridge(cls, ptr, rect):
        w = rect.width() * (1.0 - cls.flowwidth) * 0.5
        FlowBoardPainter._fillCorners(ptr, rect, w, cls.gridcolor)
        FlowBoardPainter._fillCorners(ptr, rect, w - 3, cls.bgcolor)

    @classmethod
    def drawBlock(cls, ptr, rect):
        ptr.fillRect(rect, cls.gridcolor)

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
