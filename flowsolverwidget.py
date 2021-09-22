#!/usr/bin/env python

from os import path
from datetime import datetime, timedelta
from PyQt5.QtCore import QCoreApplication, QSize, pyqtSignal
from PyQt5.QtGui import QImageWriter
from PyQt5.QtWidgets import QWidget
from flowpainter import SpacedGrid, FlowBoardPainter
from flowboard import FlowBoardSolver


class FlowSolverWidget(QWidget):

    finished = pyqtSignal(bool)

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
        return (self._endTime or datetime.now()) - self._startTime

    def setBoard(self, board):
        self._startTime = None
        self._endTime = None
        if board is None:
            self._board = None
            self._grid = None
            self._solver = None
        else:
            self._board = board
            self._grid = SpacedGrid(
                self._board.size, self._board.size, self.rect().size(), 2)
            self._solver = FlowBoardSolver(self._board)

    def run(self, skipSolution=False):
        if self._solver.done:
            if skipSolution and self._solver.solved:
                self._solver.skipSolution()
            else:
                self.finished.emit(self._solver.solved)
                return
        self._run = True
        self._startTime = datetime.now()
        self._endTime = None
        try:
            while self._run and not self._solver.run(20):
                while QCoreApplication.hasPendingEvents():
                    QCoreApplication.processEvents()
        finally:
            self._endTime = datetime.now()
            self.finished.emit(self._solver.solved)
            self.repaint()

    def stop(self):
        self._run = False

    def paintEvent(self, event):
        super(FlowSolverWidget, self).paintEvent(event)
        ptr = FlowBoardPainter(self)
        ptr.fillBackground()
        if self._board:
            if self._solver and self._solver.solved:
                ptr.drawFlowHighlights(self._grid, self._solver)
            ptr.drawGrid(self._grid)
            ptr.drawBoardFeatures(self._grid, self._board)
            if self._solver:
                ptr.drawFlows(self._grid, self._solver)
        ptr.end()

    def sizeHint(self):
        return QSize(self._size, self._size)

    def saveImage(self, dirpath):
        img = FlowBoardPainter.renderImage(self._board, self._solver)
        filename = hex(abs(self._solver.stateHash()))[2:] + '.png'
        writer = QImageWriter(path.join(dirpath, filename))
        writer.setFormat('png')
        if not writer.write(img):
            raise Exception(writer.errorString())
