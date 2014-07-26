#!/usr/bin/env python

from PyQt4.QtCore import Qt, QPoint, QSize, pyqtSignal, pyqtSlot
from PyQt4.QtGui import QPainter, QWidget, QToolBar, QComboBox, QButtonGroup, \
    QCheckBox, QGridLayout, QSizePolicy, QColor, QPen, QImage
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

    def mousePressEvent(self, event):
        super(FlowBoardEditor, self).mousePressEvent(event)
        self._toolbar.selectNextEndpointTool()

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


############################ cell tools


class FlowTool(object):
    def __init__(self):
        self._icon = None

    def getIcon(self, size):
        if not self._icon or self._icon.size() != size:
            self._icon = self._makeIcon(size)
        return self._icon

    def _makeIcon(self, size):
        raise NotImplementedError()

    @staticmethod
    def _emptyIcon(size):
        img = QImage(size, QImage.Format_ARGB32_Premultiplied)
        ptr = QPainter(img)
        ptr.setCompositionMode(QPainter.CompositionMode_Clear)
        ptr.fillRect(img.rect(), QColor(0, 0, 0, 0))
        return img


class FlowToolClear(FlowTool):
    def __init__(self):
        super(FlowToolClear, self).__init__()

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        return img


class FlowToolEndpoint(FlowTool):
    def __init__(self, key):
        super(FlowToolEndpoint, self).__init__()
        self._key = key

    @property
    def endpointKey(self):
        return self._key

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        ptr = QPainter(img)
        FlowBoardPainter.drawEndpoint(ptr, img.rect(), self.endpointKey)
        return img


class FlowToolBridge(FlowTool):
    def __init__(self):
        super(FlowToolBridge, self).__init__()

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        FlowBoardPainter.drawBridge(QPainter(img), img.rect())
        return img


############################ toolbar


class FlowToolButton(QCheckBox):
    def __init__(self, tool):
        super(FlowToolButton, self).__init__()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))
        self._size = 30
        assert isinstance(tool, FlowTool)
        self._tool = tool

    @property
    def tool(self):
        return self._tool

    def setSelected(self, selected):
        self.setCheckState(Qt.Checked if selected else Qt.Unchecked)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def sizeHint(self):
        return QSize(self._size, self._size)

    def paintEvent(self, event):
        ptr = QPainter(self)
        ptr.fillRect(self.rect(), FlowBoardPainter.bgcolor)
        if self.checkState() == Qt.Checked:
            ptr.setPen(QPen(QColor(255, 255, 255), 2, Qt.DotLine))
            ptr.drawRect(self.rect().adjusted(1, 1, -1, -1))
        iconrect = self.rect().adjusted(2, 2, -2, -2)
        ptr.drawImage(iconrect.topLeft(), self._tool.getIcon(iconrect.size()))


class FlowToolChooser(QWidget):
    def __init__(self):
        super(FlowToolChooser, self).__init__()
        self._endpointTools = \
            [FlowToolEndpoint(k) for k in sorted(FlowPalette.keys())]
        self._endpointButtons = []
        self._group = QButtonGroup()
        self._group.setExclusive(True)
        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        row = 0
        col = 1
        for tool in self._endpointTools:
            b = FlowToolButton(tool)
            self._endpointButtons.append(b)
            self._group.addButton(b)
            layout.addWidget(b, row, col)
            col += 1
            if col > len(self._endpointTools) / 2:
                row += 1
                col = 1

        b = FlowToolButton(FlowToolClear())
        self._group.addButton(b)
        layout.addWidget(b, 0, 0)

        b = FlowToolButton(FlowToolBridge())
        self._group.addButton(b)
        layout.addWidget(b, 1, 0)

        self.setLayout(layout)
        self._endpointButtons[0].setSelected(True)

    def selectedTool(self):
        return self._group.checkedButton().tool

    def selectNextEndpointTool(self):
        b = self._group.checkedButton()
        if isinstance(b.tool, FlowToolEndpoint):
            i = self._endpointButtons.index(b)
            if i < len(self._endpointButtons) - 1:
                self._endpointButtons[i + 1].setSelected(True)


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
        self._toolchooser = FlowToolChooser()
        self.addWidget(self._toolchooser)

    @property
    def selectedSize(self):
        qv = self._sizelist.itemData(self._sizelist.currentIndex())
        return qv.toInt()[0]

    def selectNextEndpointTool(self):
        self._toolchooser.selectNextEndpointTool()

    @pyqtSlot(int)
    def _sizelistChanged(self, _):
        self.makeNewBoard.emit(self.selectedSize)

    @pyqtSlot(bool)
    def _clearClicked(self, _):
        self.makeNewBoard.emit(self.selectedSize)
