#!/usr/bin/env python

import pickle
from copy import deepcopy
from PyQt4.QtCore import Qt, QSize, QObject, pyqtSignal, pyqtSlot
from PyQt4.QtGui import QWidget, QToolBar, QComboBox, QButtonGroup, \
    QPushButton, QCheckBox, QGridLayout, QBoxLayout, QSizePolicy, \
    QColor, QPen, QImage
from flowboard import FlowBoard
from flowpainter import SpacedGrid, FlowPalette, FlowBoardPainter


class FlowBoardEditor(QWidget):

    boardChanged = pyqtSignal(bool)  # argument: board is valid

    def __init__(self):
        super(FlowBoardEditor, self).__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self._toolbar = FlowBoardEditorToolBar()
        self._connectToolbar(self._toolbar)
        self._board = None
        self._grid = None
        self._lastMoveCell = None
        self.newBoard(self._toolbar.selectedSize)

    @property
    def toolbar(self):
        return self._toolbar

    @property
    def selectedTool(self):
        return self.toolbar.tools.selected

    @property
    def boardIsValid(self):
        return self._board.isValid()

    def newBoard(self, boardSize):
        self.setBoard(FlowBoard(boardSize))
        self.toolbar.tools.selectFirstOpenEndpoint(self._board)

    def setBoard(self, board):
        self.toolbar.selectSize(board.size)
        self._board = board
        self._updateGrid()
        self._lastMoveCell = None
        self.repaint()
        self.boardChanged.emit(self.boardIsValid)

    def getBoard(self):
        return deepcopy(self._board)

    def loadBoardFile(self, filepath):
        loadboard = pickle.load(open(filepath, 'rb'))
        if isinstance(loadboard, FlowBoard):
            board = FlowBoard(loadboard.size)
            board.__dict__.update(loadboard.__dict__)
            self.setBoard(board)

    def saveBoardFile(self, filepath):
        pickle.dump(self._board, open(filepath, 'wb'))

    def resizeEvent(self, event):
        super(FlowBoardEditor, self).resizeEvent(event)
        self._updateGrid()

    def paintEvent(self, event):
        super(FlowBoardEditor, self).paintEvent(event)
        ptr = FlowBoardPainter(self)
        ptr.drawGrid(self._grid)
        if self._lastMoveCell:
            if self.selectedTool.canApply(self._board, self._lastMoveCell):
                ptr.drawCellHighlight(self._grid, self._lastMoveCell)
        ptr.drawBoardFeatures(self._grid, self._board)

    def mousePressEvent(self, event):
        cell = self._grid.findCell(event.pos())
        if cell:
            self._cellClicked(cell, event.button())
            return
        super(FlowBoardEditor, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super(FlowBoardEditor, self).mouseMoveEvent(event)
        cell = self._grid.findCell(event.pos())
        if cell != self._lastMoveCell:
            self._lastMoveCell = cell
            if cell is not None:
                self._cellHover(cell, event.buttons())
            self.repaint()

    def wheelEvent(self, event):
        self.toolbar.tools.stepEndpointSelection(event.delta() < 0)

    def _cellClicked(self, cell, button):
        if button == Qt.LeftButton:
            tool = self.selectedTool
            if tool.canApply(self._board, cell):
                tool.applyAction(self._board, cell)
                self.repaint()
                self.boardChanged.emit(self.boardIsValid)
        elif button == Qt.RightButton:
            if self._takeToolFromCell(cell):
                self._board.clear(cell)
                self.repaint()
                self.boardChanged.emit(self.boardIsValid)

    def _cellHover(self, cell, buttons):
        if buttons & Qt.LeftButton:
            tool = self.selectedTool
            if tool.continuous and tool.canApply(self._board, cell):
                tool.applyAction(self._board, cell)
                self.boardChanged.emit(self.boardIsValid)

    def _takeToolFromCell(self, cell):
        if self._board.hasBridgeAt(cell):
            self.toolbar.tools.selectBridge()
            return True
        if self._board.hasBlockageAt(cell):
            self.toolbar.tools.selectBlock()
            return True
        key = self._board.endpointKeyAt(cell)
        if key is not None:
            self.toolbar.tools.selectEndpoint(key)
            return True
        return False

    def _updateGrid(self):
        self._grid = SpacedGrid(\
            self._board.size, self._board.size, self.rect().size(), 2)

    def _connectToolbar(self, toolbar):
        toolbar.makeNewBoard.connect(self._makeNewBoard)

    @pyqtSlot(int)
    def _makeNewBoard(self, size):
        self.newBoard(size)


############################ cell tools


class FlowTool(QObject):
    _continuous = False

    def __init__(self):
        super(FlowTool, self).__init__()
        self._icon = None

    def getIcon(self, size):
        if not self._icon or self._icon.size() != size:
            self._icon = self._makeIcon(size)
        return self._icon

    @property
    def continuous(self):
        return self._continuous

    def canApply(self, board, cell):
        raise NotImplementedError()

    def applyAction(self, board, cell):
        raise NotImplementedError()

    def _makeIcon(self, size):
        raise NotImplementedError()

    @staticmethod
    def _emptyIcon(size):
        img = QImage(size, QImage.Format_ARGB32_Premultiplied)
        ptr = FlowBoardPainter(img)
        ptr.fillBackground()
        ptr.end()
        return img


class FlowToolClear(FlowTool):
    _continuous = True

    def __init__(self):
        super(FlowToolClear, self).__init__()

    def canApply(self, board, cell):
        return True

    def applyAction(self, board, cell):
        board.clear(cell)

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        ptr = FlowBoardPainter(img)
        ptr.traceBound(img.rect())
        ptr.end()
        return img


class FlowToolEndpoint(FlowTool):

    applied = pyqtSignal(int, FlowBoard)  # arguments: key, board modified

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
        ptr = FlowBoardPainter(img)
        ptr.drawEndpoint(img.rect(), self.endpointKey)
        ptr.end()
        return img


class FlowToolBridge(FlowTool):
    def __init__(self):
        super(FlowToolBridge, self).__init__()

    def canApply(self, board, cell):
        return board.bridgeValidAt(cell)

    def applyAction(self, board, cell):
        board.setBridge(cell)

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        ptr = FlowBoardPainter(img)
        ptr.drawBridge(img.rect())
        ptr.end()
        return img


class FlowToolBlock(FlowTool):
    _continuous = True

    def __init__(self):
        super(FlowToolBlock, self).__init__()

    def canApply(self, board, cell):
        return board.blockageValidAt(cell)

    def applyAction(self, board, cell):
        board.setBlockage(cell)

    def _makeIcon(self, size):
        img = FlowTool._emptyIcon(size)
        ptr = FlowBoardPainter(img)
        ptr.drawBlock(img.rect())
        ptr.end()
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
        ptr = FlowBoardPainter(self)
        ptr.fillBackground()
        if self.checkState() == Qt.Checked:
            ptr.setPen(QPen(QColor(255, 255, 255), 2, Qt.DotLine))
            ptr.drawRect(self.rect().adjusted(1, 1, -1, -1))
        iconrect = self.rect().adjusted(2, 2, -2, -2)
        ptr.drawImage(iconrect.topLeft(), self._tool.getIcon(iconrect.size()))
        ptr.end()


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
        col = 2
        for tool in endpointTools:
            tool.applied.connect(self._endpointToolApplied)
            toolButton = FlowToolButton(tool)
            self._endpointButtons.append(toolButton)
            self._group.addButton(toolButton)
            layout.addWidget(toolButton, row, col)
            col += 1
            if col - 1 > len(endpointTools) / 2:
                row += 1
                col = 2

        clearToolButton = FlowToolButton(FlowToolClear())
        clearToolButton.setToolTip("clear")
        self._group.addButton(clearToolButton)
        layout.addWidget(clearToolButton, 0, 0)
        clearToolButton.setSelected(True)

        self._bridgeToolButton = FlowToolButton(FlowToolBridge())
        self._bridgeToolButton.setToolTip("bridge")
        self._group.addButton(self._bridgeToolButton)
        layout.addWidget(self._bridgeToolButton, 1, 1)

        self._blockToolButton = FlowToolButton(FlowToolBlock())
        self._blockToolButton.setToolTip("blockage")
        self._group.addButton(self._blockToolButton)
        layout.addWidget(self._blockToolButton, 1, 0)

        self.setLayout(layout)

    @property
    def selected(self):
        b = self._group.checkedButton()
        return b.tool if b else None

    def paintEvent(self, event):
        ptr = FlowBoardPainter(self)
        ptr.fillBackground()
        ptr.end()
        super(FlowToolChooser, self).paintEvent(event)

    def selectFirstOpenEndpoint(self, board):
        for button in self._endpointButtons:
            if not board.hasCompleteEndpoints(button.tool.endpointKey):
                button.setSelected(True)
                break

    def selectEndpoint(self, key):
        for button in self._endpointButtons:
            if button.tool.endpointKey == key:
                button.setSelected(True)
                return
        raise ValueError("no such tool")

    def stepEndpointSelection(self, forward=True):
        if isinstance(self.selected, FlowToolEndpoint):
            keys = sorted(FlowPalette)
            i = keys.index(self.selected.endpointKey)
            i = (i + (1 if forward else -1)) % len(keys)
            self.selectEndpoint(keys[i])

    def selectBridge(self):
        self._bridgeToolButton.setSelected(True)

    def selectBlock(self):
        self._blockToolButton.setSelected(True)

    @pyqtSlot(int, FlowBoard)
    def _endpointToolApplied(self, endpointKey, board):
        assert isinstance(self.selected, FlowToolEndpoint)
        assert endpointKey == self.selected.endpointKey
        if board.hasCompleteEndpoints(endpointKey):
            self.selectFirstOpenEndpoint(board)


class FlowBoardEditorToolBar(QToolBar):

    makeNewBoard = pyqtSignal(int)  # argument: board size

    def __init__(self):
        super(FlowBoardEditorToolBar, self).__init__()
        self.setSizePolicy(\
            QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))

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
    def tools(self):
        return self._toolchooser

    @pyqtSlot(int)
    def _sizelistChanged(self, _):
        self.makeNewBoard.emit(self.selectedSize)

    @pyqtSlot(bool)
    def _clearClicked(self, _):
        self.makeNewBoard.emit(self.selectedSize)
