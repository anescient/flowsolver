#!/usr/bin/env python

from PyQt4.QtCore import QPoint, QSize, QRect
from PyQt4.QtGui import QLayout, QLayoutItem, QWidgetItem, QWidget, QPainter


class QCenteredSquareItemLayout(QLayout):
    def __init__(self, parent=None):
        super(QCenteredSquareItemLayout, self).__init__(parent)
        self._item = None
        self._lastSetGeom = None

    def addItem(self, item):
        if self._item is not None:
            raise Exception("cannot add more than one item")
        assert isinstance(item, QLayoutItem)
        self._item = item
        self.setGeometry(self.geometry())

    def addWidget(self, widget):
        self.addItem(QWidgetItem(widget))

    #def takeAt(self, index):

    def itemAt(self, index):
        return self._item if index == 0 else None

    def count(self):
        return 1 if self._item else 0

    def setGeometry(self, rect):
        if rect == self._lastSetGeom:
            return
        self._lastSetGeom = rect
        super(QCenteredSquareItemLayout, self).setGeometry(rect)
        if self._item is None:
            return
        squaresize = min(rect.width(), rect.height()) - 2 * self.margin()
        squaresize = max(0, squaresize)
        left = (rect.width() - squaresize) / 2
        top = (rect.height() - squaresize) / 2
        sqrect = QRect(QPoint(left, top), QSize(squaresize, squaresize))
        self._item.setGeometry(sqrect)

    def minimumSize(self):
        if self._item:
            minsize = self._item.minimumSize()
            assert minsize.width() == minsize.height()
            mindim = minsize.width() + 2 * self.margin()
            return QSize(mindim, mindim)
        else:
            return QSize(0, 0)

    def sizeHint(self):
        return self.minimumSize()


class QSquareWidgetContainer(QWidget):
    def __init__(self, parent=None):
        super(QSquareWidgetContainer, self).__init__(parent)
        self._layout = None
        self._margin = 0
        self._bgcolor = None

    def setMargin(self, margin):
        self._margin = margin
        if self._layout:
            self._layout.setMargin(self._margin)

    def setBackgroundColor(self, color):
        self._bgcolor = color

    def setWidget(self, widget):
        assert isinstance(widget, QWidget)
        self._layout = QCenteredSquareItemLayout()
        self._layout.setMargin(self._margin)
        self._layout.addWidget(widget)
        self.setLayout(self._layout)

    def minimumSize(self):
        return self._layout.minimumSize() if self._layout else QSize(0, 0)

    def paintEvent(self, event):
        super(QSquareWidgetContainer, self).paintEvent(event)
        if self._bgcolor:
            QPainter(self).fillRect(self.rect(), self._bgcolor)
