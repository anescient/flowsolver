#!/usr/bin/env python

print "loading testbench"

import random
from PyQt4.QtCore import QPoint, QLine, QLineF, QSize, pyqtSlot
from PyQt4.QtGui import QPushButton, QDialog, QStatusBar, QLayout, \
    QBoxLayout, QWidget, QPen, QColor
from flowboard import FlowBoardGraph
from flowpainter import SpacedGrid, FlowBoardPainter, FlowPalette
from flowsolver import FlowBoardSolver


class TestWidget(QWidget):
    def __init__(self):
        super(TestWidget, self).__init__()
        self._size = 500
        self.setFixedSize(self.sizeHint())
        self._board = None
        self._grid = None
        self._graph = None
        self._marks = None
        self._parts = None
        self._paths = None
        self._edges = None
        self._trees = None

    def setBoard(self, board):
        self._board = board
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)
        self._graph = FlowBoardGraph(board)
        self._marks = []
        self._parts = []
        self._paths = []
        self._edges = []
        self._trees = []
        self.repaint()

    def run(self):
        v1, v2 = random.sample(list(self._graph.vertices), 2)
        self._marks = [v1, v2]
        p = self._graph.shortestPath(v1, v2)
        self._paths = [p] if p else []
        self.repaint()

    def paintEvent(self, event):
        super(TestWidget, self).paintEvent(event)
        ptr = FlowBoardPainter(self)
        ptr.fillBackground()
        ptr.drawGrid(self._grid)
        ptr.drawBoardFeatures(self._grid, self._board)
        if self._marks:
            for v in self._marks:
                r = self._grid.cellRect(self._graph.vertexToCell(v))
                margin = self._grid.minDimension // 4
                r.adjust(margin, margin, -margin, -margin)
                ptr.drawEndpoint(r, color=QColor.fromHslF(0, 0, 0.4))
        if self._parts:
            k = 1
            for p in self._parts:
                self._markVerts(ptr, k, p)
                k += 1
        if self._paths:
            for p in self._paths:
                edges = [(a, b) for a, b in zip(p, p[1:])]
                self._drawEdges(ptr, edges, True)
        if self._edges:
            self._drawEdges(ptr, self._edges)
        if self._trees:
            self._edges = self._edges or []
            for t in self._trees:
                self._drawEdges(ptr, t.edges, True)
        ptr.end()

    def sizeHint(self):
        return QSize(self._size, self._size)

    def _drawEdges(self, ptr, edges, directed=False):
        c = QColor(255, 255, 255)
        ptr.setPen(QPen(c, 2))
        for _, edge in enumerate(edges):
            #c.setHslF(0.1 * float(i % 10), 0.8, 0.5)
            #ptr.setPen(QPen(c, 2))
            c1, c2 = self._graph.verticesToCells(edge)
            p1, p2 = self._grid.cellCenter(c1), self._grid.cellCenter(c2)
            line = QLineF(QLine(p2, p1))
            ptr.drawLine(line)
            if directed:
                line.setAngle(line.angle() + 10)
                line.setLength(line.length() * 0.25)
                ptr.drawLine(line)
                line.setAngle(line.angle() - 20)
                ptr.drawLine(line)

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
        for cell in self._graph.verticesToCells(verts):
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
