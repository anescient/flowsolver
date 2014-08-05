#!/usr/bin/env python

print "loading testbench"

from PyQt4.QtCore import QPoint, QSize, pyqtSlot
from PyQt4.QtGui import QPushButton, QDialog, QStatusBar, QLayout, \
    QBoxLayout, QWidget, QPainter
from grid import SpacedGrid
from flowboard import FlowBoardPainter, FlowBoardGraph


class TestWidget(QWidget):
    def __init__(self):
        super(TestWidget, self).__init__()
        self._size = 500
        self.setFixedSize(self.sizeHint())
        self._board = None
        self._grid = None
        self._graph = None
        self._parts = None

    def setBoard(self, board):
        self._board = board
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)
        self._graph = FlowBoardGraph(board)
        self._parts = self._graph.disjointPartitions()
        self.repaint()

    def paintEvent(self, event):
        super(TestWidget, self).paintEvent(event)
        fbp = FlowBoardPainter(self._grid)
        fbp.drawGrid()
        fbp.drawBoardFeatures(self._board)
        if self._parts:
            k = 1
            for p in self._parts:
                self._markVerts(fbp.image, k, p)
                k += 1
        QPainter(self).drawImage(QPoint(0, 0), fbp.image)

    def sizeHint(self):
        return QSize(self._size, self._size)

    def _markVerts(self, img, key, verts):
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
            FlowBoardPainter.drawEndpoint(QPainter(img), r_mark, key)


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
    def _abortClicked(self, _):
        self.close()
