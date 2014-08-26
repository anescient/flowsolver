#!/usr/bin/env python

print "loading testbench"

from PyQt4.QtCore import QPoint, QLine, QLineF, QSize, pyqtSlot
from PyQt4.QtGui import QPushButton, QDialog, QStatusBar, QLayout, \
    QBoxLayout, QWidget, QPen, QColor
from graph import SimpleGraph
from flowboard import FlowBoardSolver
from flowpainter import SpacedGrid, FlowBoardPainter, FlowPalette


class TestWidget(QWidget):
    def __init__(self):
        super(TestWidget, self).__init__()
        self._size = 500
        self.setFixedSize(self.sizeHint())
        self._board = None
        self._grid = None
        self._cellmap = None
        self._graph = None
        self._solver = None
        self._marks = None
        self._parts = None
        self._paths = None
        self._edges = None
        self._trees = None

    def setBoard(self, board):
        self._board = board
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)
        puzzle, self._cellmap = board.getPuzzle()
        self._graph = SimpleGraph(puzzle.graph)
        self._solver = FlowBoardSolver(board) if board.isValid() else None
        self._marks = []
        self._parts = []
        self._paths = []
        self._edges = []
        self._trees = []
        self.repaint()

    def run(self):
        for p in self._paths:
            if self._graph.adjacent(p[0], p[-1]):
                self._graph.removeEdge(p[0], p[-1])
        self._paths = self._graph.paths()
        self.repaint()

    def paintEvent(self, event):
        super(TestWidget, self).paintEvent(event)
        ptr = FlowBoardPainter(self)
        ptr.fillBackground()
        ptr.drawGrid(self._grid)
        ptr.drawBoardFeatures(self._grid, self._board)
        if self._solver:
            ptr.drawFlows(self._grid, self._solver)
        if self._marks:
            for v in self._marks:
                r = self._grid.cellRect(self._cellmap[v])
                margin = self._grid.minDimension // 4
                r.adjust(margin, margin, -margin, -margin)
                ptr.drawEndpoint(r, color=QColor.fromHslF(0, 0, 0.4))
        if self._parts:
            k = 1
            for p in self._parts:
                self._markVerts(ptr, k, p)
                k += 1
        if self._paths:
            for i, p in enumerate(self._paths):
                edges = [(a, b) for a, b in zip(p, p[1:])]
                ci = i / float(len(self._paths))
                self._drawEdges(ptr, edges, True, ci)
        if self._edges:
            self._drawEdges(ptr, self._edges)
        if self._trees:
            for t in self._trees:
                edges = []
                for v in t:
                    pv = t[v]
                    if pv is not None:
                        edges.append((pv, v))
                self._drawEdges(ptr, edges, True)
        ptr.end()

    def sizeHint(self):
        return QSize(self._size, self._size)

    def _vertsCenter(self, vertices):
        if not hasattr(vertices, '__iter__'):
            vertices = [vertices]
        cells = map(self._cellmap.get, vertices)
        xs = [p.x() for p in map(self._grid.cellCenter, cells)]
        ys = [p.y() for p in map(self._grid.cellCenter, cells)]
        return QPoint(sum(xs) / len(xs), sum(ys) / len(ys))

    def _drawEdges(self, ptr, edges, directed=False, colorindex=None):
        c = QColor(255, 255, 255)
        if colorindex is not None:
            c.setHslF(colorindex, 0.8, 0.7)
        c.setAlphaF(0.5)
        ptr.setPen(QPen(c, 2))
        ptr.setBrush(c)
        for _, edge in enumerate(edges):
            p1, p2 = map(self._vertsCenter, edge)
            line = QLineF(QLine(p2, p1))
            ptr.drawLine(line)
            if directed:
                arrow = [line.p1()]
                a = line.angle()
                line.setLength(self._grid.minDimension * 0.3)
                line.setAngle(a + 15)
                arrow.append(line.p2())
                line.setAngle(a - 15)
                arrow.append(line.p2())
                ptr.drawConvexPolygon(*arrow)

    def _markVerts(self, ptr, key, verts):
        key = (key - min(FlowPalette)) % len(FlowPalette) + min(FlowPalette)
        div = 4
        r_mark = self._grid.cellRect((0, 0))
        marksize = self._grid.minDimension // div
        r_mark.setWidth(marksize)
        r_mark.setHeight(marksize)
        row = (key - 1) // div
        col = (key - 1) % div
        offset = QPoint(col * marksize, row * marksize)
        for cell in map(self._cellmap.get, verts):
            r_mark.moveTopLeft(self._grid.cellRect(cell).topLeft() + offset)
            ptr.drawEndpoint(r_mark, key)


class TestPopup(QDialog):
    def __init__(self, parent=None):
        super(TestPopup, self).__init__(parent)

        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setSpacing(0)
        layout.setMargin(0)

        self._widget = TestWidget()
        layout.addWidget(self._widget)

        status = QStatusBar()
        status.setSizeGripEnabled(False)

        runButton = QPushButton("run")
        runButton.clicked.connect(self._runClicked)
        status.addPermanentWidget(runButton)

        self._abortButton = QPushButton("close")
        self._abortButton.clicked.connect(self._abortClicked)
        status.addPermanentWidget(self._abortButton)

        layout.addWidget(status)

        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)

        self._board = None

    def setBoard(self, board):
        self._board = board
        self._widget.setBoard(board)

    def closeEvent(self, event):
        super(TestPopup, self).closeEvent(event)

    @pyqtSlot(bool)
    def _runClicked(self, _):
        self._widget.run()

    @pyqtSlot(bool)
    def _abortClicked(self, _):
        self.close()


def TestSolve(boardfile):
    import pickle
    from timeit import timeit
    board = pickle.load(open(boardfile, 'rb'))
    solver = FlowBoardSolver(board)
    print "running"
    print
    seconds = timeit(solver.run, number=1)
    solver.printStats()
    print "{0:.2f} seconds".format(seconds)
