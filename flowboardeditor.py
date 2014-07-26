#!/usr/bin/env python

from PyQt4.QtCore import QPoint
from PyQt4.QtGui import QWidget, QToolBar, QComboBox, QPainter
from grid import SpacedGrid
from flowboard import FlowBoard, FlowBoardPainter


class FlowBoardEditor(QWidget):
    def __init__(self, boardSize):
        super(FlowBoardEditor, self).__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self._board = None
        self._grid = None
        self._markedCell = None
        self.newBoard(boardSize)

    def newBoard(self, boardSize):
        self._board = FlowBoard(boardSize)
        self._updateGrid()

    def resizeEvent(self, event):
        super(FlowBoardEditor, self).resizeEvent(event)
        self._updateGrid()

    def paintEvent(self, event):
        super(FlowBoardEditor, self).paintEvent(event)
        QPainter(self).drawImage(QPoint(0, 0), self._renderBoard())

    def mouseMoveEvent(self, event):
        super(FlowBoardEditor, self).mouseMoveEvent(event)
        self._markCell(self._grid.findCell(event.pos()))

    def _markCell(self, cell):
        if self._markedCell == cell:
            return
        self._markedCell = cell
        self.repaint()

    def _updateGrid(self):
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)

    def _renderBoard(self):
        ptr = FlowBoardPainter(self._grid)
        ptr.drawGrid()
        if self._markedCell:
            ptr.drawCellHighlight(self._markedCell)
        return ptr.image


class FlowBoardEditorToolBar(QToolBar):
    def __init__(self):
        super(FlowBoardEditorToolBar, self).__init__()
        cb = QComboBox()
        cb.addItem("7x7", 7)
        cb.addItem("8x8", 8)
        cb.addItem("9x9", 9)
        self.addWidget(cb)
        self.addAction("clear")
