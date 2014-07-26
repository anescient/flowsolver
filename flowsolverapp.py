#!/usr/bin/env python

from PyQt4.QtCore import QPoint
from PyQt4.QtGui import QApplication, QMainWindow, QWidget, \
    QPainter, QImage, QColor, QPen
from QSquareWidget import QSquareWidgetContainer
from grid import SpacedGrid


class FlowBoard(object):
    def __init__(self, size=None):
        self._size = size or 7

    @property
    def size(self):
        return self._size

    def _includesCell(self, cell):
        return cell[0] >= 0 and cell[0] < self._size and \
               cell[1] >= 0 and cell[1] < self._size


class FlowBoardPainter(object):
    def __init__(self, grid):
        self._grid = grid
        self._img = QImage(self._grid.size, QImage.Format_ARGB32_Premultiplied)
        self._bgcolor = QColor(0, 0, 0)
        self._gridcolor = QColor(81, 80, 62)
        self._highlightcolor = QColor(34, 51, 44)
        QPainter(self._img).fillRect(self._img.rect(), self._bgcolor)

    @property
    def image(self):
        return self._img

    def drawGrid(self):
        ptr = QPainter(self._img)
        ptr.setPen(QPen(self._gridcolor, self._grid.spacing))
        w = self._img.width()
        for x in self._grid.columnSpacingsCenters():
            ptr.drawLine(x, 0, x, w)
        for y in self._grid.rowSpacingsCenters():
            ptr.drawLine(0, y, w, y)

    def drawCellHighlight(self, cell):
        r = self._grid.cellRect(cell)
        QPainter(self._img).fillRect(r, self._highlightcolor)


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


class FlowSolverWindow(QMainWindow):
    def __init__(self):
        super(FlowSolverWindow, self).__init__()
        self.setWindowTitle("flow solver")

        tb = self.addToolBar("toobar")
        tb.setFloatable(False)
        tb.setMovable(False)
        tb.addAction("solve")

        editor = FlowBoardEditor(7)
        squarer = QSquareWidgetContainer()
        squarer.setMargin(20)
        squarer.setWidget(editor)
        squarer.setBackgroundColor(QColor(0, 0, 0))
        self.setCentralWidget(squarer)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    main = FlowSolverWindow()
    main.show()
    sys.exit(app.exec_())
