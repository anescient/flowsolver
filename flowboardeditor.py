#!/usr/bin/env python

import pickle
from copy import deepcopy
from PyQt4.QtCore import Qt, QPoint, QSize, QObject, pyqtSignal, pyqtSlot
from PyQt4.QtGui import QPainter, QWidget, QToolBar, QComboBox, QButtonGroup, \
    QPushButton, QCheckBox, QGridLayout, QBoxLayout, QSizePolicy, \
    QColor, QPen, QImage
from grid import SpacedGrid
from flowboard import FlowBoard, FlowPalette, FlowBoardPainter


class FlowBoardEditor(QWidget):

    boardChanged = pyqtSignal(bool)

    def __init__(self):
        super(FlowBoardEditor, self).__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self._toolbar = FlowBoardEditorToolBar()
        self._connectToolbar(self._toolbar)
        self._board = None
        self._grid = None
        self._hoverCell = None
        self.newBoard(self._toolbar.selectedSize)

    @property
    def toolbar(self):
        return self._toolbar

    @property
    def selectedTool(self):
        return self._toolbar.selectedTool

    @property
    def boardIsValid(self):
        return self._board.isValid()

    def newBoard(self, boardSize):
        self.setBoard(FlowBoard(boardSize))
        self._toolbar.selectFirstEndpointTool()

    def setBoard(self, board):
        self._toolbar.selectSize(board.size)
        self._board = board
        self._updateGrid()
        self._hoverCell = None
        self.repaint()
        self.boardChanged.emit(self.boardIsValid)

    def getBoard(self):
        return deepcopy(self._board)

    def loadBoardFile(self, filepath):
        board = pickle.load(open(filepath, 'rb'))
        if isinstance(board, FlowBoard):
            self.setBoard(board)

    def saveBoardFile(self, filepath):
        pickle.dump(self._board, open(filepath, 'wb'))

    def resizeEvent(self, event):
        super(FlowBoardEditor, self).resizeEvent(event)
        self._updateGrid()

    def paintEvent(self, event):
        super(FlowBoardEditor, self).paintEvent(event)
        QPainter(self).drawImage(QPoint(0, 0), self._renderBoard())

    def mousePressEvent(self, event):
        cell = self._grid.findCell(event.pos())
        if cell:
            self._cellClicked(cell, event.button())
            return
        super(FlowBoardEditor, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super(FlowBoardEditor, self).mouseMoveEvent(event)
        self._markCell(self._grid.findCell(event.pos()))

    def _cellClicked(self, cell, button):
        if button == Qt.LeftButton:
            tool = self.selectedTool
            if tool.canApply(self._board, cell):
                tool.applyAction(self._board, cell)
                self.repaint()
                self.boardChanged.emit(self.boardIsValid)
        elif button == Qt.RightButton:
            key = self._board.endpointKeyAt(cell)
            if key is not None:
                self._board.clear(cell)
                self._toolbar.selectEndpointTool(key)
                self.repaint()
                self.boardChanged.emit(self.boardIsValid)

    def _markCell(self, cell):
        if self._hoverCell != cell:
            self._hoverCell = cell
            self.repaint()

    def _updateGrid(self):
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)

    def _renderBoard(self):
        fbp = FlowBoardPainter(self._grid)
        fbp.drawGrid()
        if self._hoverCell:
            if self.selectedTool.canApply(self._board, self._hoverCell):
                fbp.drawCellHighlight(self._hoverCell)
        fbp.drawEndpoints(self._board.endpoints)
        fbp.drawBridges(self._board.bridges)
        return fbp.image

    def _connectToolbar(self, toolbar):
        toolbar.makeNewBoard.connect(self._makeNewBoard)

    @pyqtSlot(int)
    def _makeNewBoard(self, size):
        self.newBoard(size)


############################ cell tools


class FlowTool(QObject):
    def __init__(self):
        super(FlowTool, self).__init__()
        self._icon = None

    def getIcon(self, size):
        if not self._icon or self._icon.size() != size:
            self._icon = self._makeIcon(size)
        return self._icon

    def canApply(self, board, cell):
        raise NotImplementedError()

    def applyAction(self, board, cell):
        raise NotImplementedError()

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

    def canApply(self, board, cell):
        return True

    def applyAction(self, board, cell):
        board.clear(cell)

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        ptr = QPainter(img)
        ptr.setPen(QPen(FlowBoardPainter.gridcolor, 2, join=Qt.MiterJoin))
        ptr.drawRect(img.rect().adjusted(1, 1, -1, -1))
        return img


class FlowToolEndpoint(FlowTool):

    applied = pyqtSignal(int, FlowBoard)

    def __init__(self, key):
        super(FlowToolEndpoint, self).__init__()
        self._key = key

    @property
    def endpointKey(self):
        return self._key

    def canApply(self, board, cell):
        return True

    def applyAction(self, board, cell):
        board.setEndpoint(cell, self.endpointKey)
        self.applied.emit(self.endpointKey, board)

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        ptr = QPainter(img)
        FlowBoardPainter.drawEndpoint(ptr, img.rect(), self.endpointKey)
        return img


class FlowToolBridge(FlowTool):
    def __init__(self):
        super(FlowToolBridge, self).__init__()

    def canApply(self, board, cell):
        return board.isInnerCell(cell)

    def applyAction(self, board, cell):
        board.setBridge(cell)

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
        self._group = QButtonGroup()
        self._group.setExclusive(True)
        layout = QGridLayout()
        layout.setSpacing(0)
        layout.setMargin(4)
        layout.setAlignment(Qt.AlignCenter)

        endpointTools = [FlowToolEndpoint(k) for k in sorted(FlowPalette)]
        self._endpointButtons = []
        row = 0
        col = 1
        for tool in endpointTools:
            tool.applied.connect(self._endpointToolApplied)
            b = FlowToolButton(tool)
            self._endpointButtons.append(b)
            self._group.addButton(b)
            layout.addWidget(b, row, col)
            col += 1
            if col > len(endpointTools) / 2:
                row += 1
                col = 1
        self._endpointButtons[0].setSelected(True)

        b = FlowToolButton(FlowToolClear())
        b.setToolTip("clear")
        self._group.addButton(b)
        layout.addWidget(b, 0, 0)

        b = FlowToolButton(FlowToolBridge())
        b.setToolTip("bridge")
        self._group.addButton(b)
        layout.addWidget(b, 1, 0)

        self.setLayout(layout)

    @property
    def selectedTool(self):
        b = self._group.checkedButton()
        return b.tool if b else None

    def paintEvent(self, event):
        QPainter(self).fillRect(self.rect(), FlowBoardPainter.bgcolor)
        super(FlowToolChooser, self).paintEvent(event)

    def selectFirstEndpointTool(self):
        self._endpointButtons[0].setSelected(True)

    def selectEndpointTool(self, key):
        for button in self._endpointButtons:
            if button.tool.endpointKey == key:
                button.setSelected(True)
                return
        raise ValueError("no such tool")

    @pyqtSlot(int, FlowBoard)
    def _endpointToolApplied(self, endpointKey, board):
        assert isinstance(self.selectedTool, FlowToolEndpoint)
        assert endpointKey == self.selectedTool.endpointKey
        if board.hasCompleteEndpoints(endpointKey):
            i = self._endpointButtons.index(self._group.checkedButton())
            if i < len(self._endpointButtons) - 1:
                self._endpointButtons[i + 1].setSelected(True)


class FlowBoardEditorToolBar(QToolBar):

    makeNewBoard = pyqtSignal(int)  # argument: board size

    def __init__(self):
        super(FlowBoardEditorToolBar, self).__init__()

        boardbox = QBoxLayout(QBoxLayout.TopToBottom)
        boardbox.setSpacing(2)

        self._sizelist = QComboBox()
        for s in xrange(5, 15):
            self._sizelist.addItem("{0}x{0}".format(s), s)
        self._sizelist.setCurrentIndex(2)
        boardbox.addWidget(self._sizelist)
        self._sizelist.currentIndexChanged.connect(self._sizelistChanged)

        clearbutton = QPushButton("clear")
        boardbox.addWidget(clearbutton)
        clearbutton.clicked.connect(self._clearClicked)

        boardboxwidget = QWidget()
        boardboxwidget.setLayout(boardbox)
        self.addWidget(boardboxwidget)

        self._toolchooser = FlowToolChooser()
        self.addWidget(self._toolchooser)

    @property
    def selectedSize(self):
        qv = self._sizelist.itemData(self._sizelist.currentIndex())
        return qv.toInt()[0]

    def selectSize(self, size):
        if size != self.selectedSize:
            i = self._sizelist.findData(size)
            if i >= 0:
                self._sizelist.setCurrentIndex(i)

    @property
    def selectedTool(self):
        return self._toolchooser.selectedTool

    def selectFirstEndpointTool(self):
        self._toolchooser.selectFirstEndpointTool()

    def selectEndpointTool(self, key):
        self._toolchooser.selectEndpointTool(key)

    @pyqtSlot(int)
    def _sizelistChanged(self, _):
        self.makeNewBoard.emit(self.selectedSize)

    @pyqtSlot(bool)
    def _clearClicked(self, _):
        self.makeNewBoard.emit(self.selectedSize)
