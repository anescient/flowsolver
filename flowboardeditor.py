#!/usr/bin/env python

from PyQt4.QtCore import Qt, QPoint, QSize, pyqtSignal, pyqtSlot
from PyQt4.QtGui import QPainter, QWidget, QToolBar, QComboBox, QButtonGroup, \
    QCheckBox, QGridLayout, QSizePolicy, QColor, QPen
from grid import SpacedGrid
from flowboard import FlowBoard, FlowPalette, FlowBoardPainter


class FlowBoardEditor(QWidget):
    def __init__(self):
        super(FlowBoardEditor, self).__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self._toolbar = FlowBoardEditorToolBar()
        self._connectToolbar(self._toolbar)
        self._board = None
        self._grid = None
        self._markedCell = None
        self.newBoard(self._toolbar.selectedSize)

    @property
    def toolbar(self):
        return self._toolbar

    def newBoard(self, boardSize):
        self._board = FlowBoard(boardSize)
        self._updateGrid()
        self.repaint()

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

    def _connectToolbar(self, toolbar):
        toolbar.makeNewBoard.connect(self._makeNewBoard)

    @pyqtSlot(int)
    def _makeNewBoard(self, size):
        self.newBoard(size)


class SwatchToggle(QCheckBox):
    def __init__(self, color, key=None):
        super(SwatchToggle, self).__init__()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self._size = 30
        self._color = color
        self._key = key

    @property
    def key(self):
        return self._key

    def setSelected(self, on):
        self.setCheckState(Qt.Checked if on else Qt.Unchecked)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        ptr = QPainter(self)
        ptr.fillRect(self.rect(), QColor(0, 0, 0))
        if self.checkState() == Qt.Checked:
            ptr.setPen(QPen(QColor(255, 255, 255), 2, Qt.DotLine))
            ptr.drawRect(self.rect().adjusted(1, 1, -1, -1))
        ptr.setRenderHint(QPainter.Antialiasing, True)
        ptr.setBrush(self._color)
        ptr.setPen(QPen(Qt.NoPen))
        ptr.drawEllipse(self.rect().adjusted(2, 2, -2, -2))

    def sizeHint(self):
        return QSize(self._size, self._size)


class FlowColorChooser(QWidget):
    def __init__(self, palette):
        super(FlowColorChooser, self).__init__()
        self._palette = palette
        self._keys = sorted(self._palette.keys())
        self._keyButtons = {}
        self._group = QButtonGroup()
        self._group.setExclusive(True)
        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        row = 0
        col = 0
        for k in self._keys:
            b = SwatchToggle(self._palette[k], k)
            self._keyButtons[k] = b
            self._group.addButton(b)
            layout.addWidget(b, row, col)
            col += 1
            if col >= len(self._keys) / 2:
                row += 1
                col = 0
        self.setLayout(layout)
        self.setSelectedKey(self._keys[0])

    def selectedKey(self):
        return self._group.checkedButton().key

    def selected(self):
        k = self.selectedKey()
        return (k, self._palette[k])

    def setSelectedKey(self, key):
        self._keyButtons[key].setSelected(True)

    def selectNext(self):
        nextidx = (self._keys.index(self.selectedKey) + 1) % len(self._keys)
        self.setSelectedKey(self._keys[nextidx])


class FlowBoardEditorToolBar(QToolBar):

    makeNewBoard = pyqtSignal(int)  # argument: board size

    def __init__(self):
        super(FlowBoardEditorToolBar, self).__init__()

        self._sizelist = QComboBox()
        for s in xrange(5, 15):
            self._sizelist.addItem("{0}x{0}".format(s), s)
        self.addWidget(self._sizelist)
        self._sizelist.currentIndexChanged.connect(self._sizelistChanged)

        act_clear = self.addAction("clear")
        act_clear.triggered.connect(self._clearClicked)

        self.addSeparator()
        self._colorpicker = FlowColorChooser(FlowPalette)
        self.addWidget(self._colorpicker)

    @property
    def selectedSize(self):
        qv = self._sizelist.itemData(self._sizelist.currentIndex())
        return qv.toInt()[0]

    @pyqtSlot(int)
    def _sizelistChanged(self, _):
        self.makeNewBoard.emit(self.selectedSize)

    @pyqtSlot(bool)
    def _clearClicked(self, _):
        self.makeNewBoard.emit(self.selectedSize)
