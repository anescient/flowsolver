#!/usr/bin/env python

from datetime import datetime, timedelta
from PyQt4.QtCore import QCoreApplication, QPoint, QSize, pyqtSignal
from PyQt4.QtGui import QPainter, QWidget
from flowboard import FlowBoardPainter
from grid import SpacedGrid
from flowsolver import FlowBoardSolver


class FlowSolverWidget(QWidget):

    finished = pyqtSignal()

    def __init__(self):
        super(FlowSolverWidget, self).__init__()
        self._size = 500
        self.setFixedSize(self.sizeHint())
        self._board = None
        self._grid = None
        self._solver = None
        self._startTime = None
        self._endTime = None
        self._run = False

    @property
    def timeElapsed(self):
        if self._startTime is None:
            return timedelta(0)
        if self._endTime is None:
            return datetime.now() - self._startTime
        return self._endTime - self._startTime

    @property
    def solved(self):
        return False if self._solver is None else self._solver.solved

    def setBoard(self, board):
        self._startTime = None
        self._endTime = None
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
        if self._solver.done:
            self.finished.emit()
            return
        self._run = True
        self._startTime = datetime.now()
        while self._run and not self._solver.run(20):
            QCoreApplication.processEvents()
        self._endTime = datetime.now()
        self.finished.emit()
        print
        self._solver.printStats()
        self.repaint()

    def stop(self):
        self._run = False

    def paintEvent(self, event):
        super(FlowSolverWidget, self).paintEvent(event)
        if self._board:
            fbp = FlowBoardPainter(self._grid)
            fbp.drawGrid()
            fbp.drawBoardFeatures(self._board)
            if self._solver:
                for key, cells in self._solver.getFlows():
                    if len(cells) > 1:
                        fbp.drawFlow(key, cells)
            QPainter(self).drawImage(QPoint(0, 0), fbp.image)

    def sizeHint(self):
        return QSize(self._size, self._size)
