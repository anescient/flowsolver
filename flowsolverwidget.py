#!/usr/bin/env python

from PyQt4.QtCore import QPoint, QSize
from PyQt4.QtGui import QPainter, QWidget
from flowboard import FlowBoardPainter
from grid import SpacedGrid


class FlowSolverWidget(QWidget):
    def __init__(self, board):
        super(FlowSolverWidget, self).__init__()
        self._size = 500
        self.setFixedSize(self.sizeHint())
        self._board = board
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)

    def paintEvent(self, event):
        super(FlowSolverWidget, self).paintEvent(event)
        fbp = FlowBoardPainter(self._grid)
        fbp.drawGrid()
        fbp.drawEndpoints(self._board.endpoints)
        fbp.drawBridges(self._board.bridges)
        QPainter(self).drawImage(QPoint(0, 0), fbp.image)

    def sizeHint(self):
        return QSize(self._size, self._size)
