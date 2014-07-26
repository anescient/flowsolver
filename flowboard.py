#!/usr/bin/env python

from PyQt4.QtGui import QPainter, QImage, QColor, QPen


class FlowBoard(object):
    def __init__(self, size=None):
        self._size = size or 7

    @property
    def size(self):
        return self._size

    def _includesCell(self, cell):
        return cell[0] >= 0 and cell[0] < self._size and \
               cell[1] >= 0 and cell[1] < self._size


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
