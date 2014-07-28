#!/usr/bin/env python

from PyQt4.QtCore import QPoint, QSize
from PyQt4.QtGui import QPainter, QWidget
from flowboard import FlowBoardPainter
from grid import SpacedGrid
from flowsolver import FlowBoardSolver


class FlowSolverWidget(QWidget):
    def __init__(self):
        super(FlowSolverWidget, self).__init__()
        self._size = 500
        self.setFixedSize(self.sizeHint())
        self._board = None
        self._grid = None
        self._solver = None

    def setBoard(self, board):
        if board is None:
            self._board = None
            self._grid = None
            self._solver = None
        else:
            self._board = board
            self._grid = SpacedGrid(\
                self._board.size, self._board.size, self.rect().size(), 2)
            self._solver = FlowBoardSolver(self._board)

    def run(self):
        self._solver.run()
        self.repaint()

    def paintEvent(self, event):
        super(FlowSolverWidget, self).paintEvent(event)
        if self._board:
            assert self._grid and self._solver
            fbp = FlowBoardPainter(self._grid)
            fbp.drawGrid()
            fbp.drawEndpoints(self._board.endpoints)
            fbp.drawBridges(self._board.bridges)
            for key, cells in self._solver.getFlows():
                fbp.drawFlow(key, cells)
            QPainter(self).drawImage(QPoint(0, 0), fbp.image)

    def sizeHint(self):
        return QSize(self._size, self._size)