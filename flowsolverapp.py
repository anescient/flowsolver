#!/usr/bin/env python

from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QMainWindow,\
    QPushButton, QDialog, QStatusBar, QLayout, QBoxLayout,\
    QLabel, QFileDialog, QMenuBar, QWidget
from QSquareWidget import QSquareWidgetContainer
from flowboard import FlowBoard
from flowboardeditor import FlowBoardEditor
from flowsolverwidget import FlowSolverWidget


class FlowSolverAppWindow(QMainWindow):
    def __init__(self):
        super(FlowSolverAppWindow, self).__init__()
        self.setWindowTitle("flow solver")
        self.setAcceptDrops(True)

        # toolbars can be hidden/toggled by some kind of default context menu.
        # this seems to be the only way to make them un-hide-able.
        self.setContextMenuPolicy(Qt.NoContextMenu)

        self._editor = FlowBoardEditor()
        self._editor.toolbar.setFloatable(False)
        self._editor.toolbar.setMovable(False)
        self._editor.boardChanged.connect(self._boardChanged)
        self.addToolBar(self._editor.toolbar)
        editorcontainer = QSquareWidgetContainer()
        editorcontainer.setMargin(20)
        editorcontainer.setWidget(self._editor)
        editorcontainer.setBackgroundColor(QColor(0, 0, 0))
        self.setCentralWidget(editorcontainer)

        tb = self.addToolBar("solve")
        tb.setFloatable(False)
        tb.setMovable(False)

        self._solveButton = QPushButton("solve")
        self._solveButton.clicked.connect(self._solveClicked)
        self._solveButton.setEnabled(self._editor.boardIsValid)

        actionbox = QBoxLayout(QBoxLayout.TopToBottom)
        actionbox.setSpacing(2)
        actionbox.addWidget(self._solveButton)
        actionswidget = QWidget()
        actionswidget.setLayout(actionbox)
        tb.addWidget(actionswidget)

        mb = QMenuBar()
        filemenu = mb.addMenu("File")
        filemenu.addAction("Open").triggered.connect(self._openClicked)
        filemenu.addAction("Save As").triggered.connect(self._saveClicked)
        self.setMenuBar(mb)

        self._solvepopup = FlowSolvingPopup(self)
        self._solvepopup.setModal(True)

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.proposedAction() & (Qt.CopyAction | Qt.MoveAction):
            if event.mimeData().hasUrls():
                filepath = event.mimeData().urls()[0].toLocalFile()
                if filepath:
                    event.acceptProposedAction()
                    self._editor.loadBoardFile(filepath)

    @pyqtSlot(bool)
    def _solveClicked(self, _):
        self._solvepopup.show()
        self._solvepopup.startSolve(self._editor.getBoard())

    @pyqtSlot(bool)
    def _openClicked(self, _):
        filepath = QFileDialog.getOpenFileName(caption="open board")[0]
        if filepath:
            self._editor.loadBoardFile(filepath)

    @pyqtSlot(bool)
    def _saveClicked(self, _):
        filepath = QFileDialog.getSaveFileName(caption="save board")[0]
        if filepath:
            self._editor.saveBoardFile(filepath)

    @pyqtSlot(FlowBoard)
    def _boardChanged(self, board):
        self._solveButton.setEnabled(board.isValid())


class FlowSolvingPopup(QDialog):
    def __init__(self, parent=None):
        super(FlowSolvingPopup, self).__init__(parent)

        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self._solverWidget = FlowSolverWidget()
        self._solverWidget.finished.connect(self._solverFinished)
        layout.addWidget(self._solverWidget)

        status = QStatusBar()
        status.setSizeGripEnabled(False)

        self._againButton = QPushButton("next")
        self._againButton.setVisible(False)
        self._againButton.clicked.connect(self._againClicked)
        status.addPermanentWidget(self._againButton)

        self._abortButton = QPushButton("close")
        self._abortButton.clicked.connect(self._abortClicked)
        status.addPermanentWidget(self._abortButton)

        self._messageLabel = QLabel("ready")
        status.addWidget(self._messageLabel)
        layout.addWidget(status)

        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)

        self._timer = QTimer()
        self._timer.timeout.connect(self._timerTick)

    def startSolve(self, board):
        self._againButton.setVisible(False)
        if board.isValid():
            self._solverWidget.setBoard(board)
            self._runSolve()
        else:
            self._solverWidget.setBoard(None)
            self._setMessage("board is not valid")
            self._abortButton.setText("close")

    def closeEvent(self, event):
        self._timer.stop()
        self._solverWidget.stop()
        super(FlowSolvingPopup, self).closeEvent(event)

    def _runSolve(self, again=False):
        self._setMessage("running")
        self._againButton.setVisible(False)
        self._abortButton.setText("cancel")
        self._timer.start(70)
        self._solverWidget.run(skipSolution=again)

    def _setMessage(self, msg):
        self._messageLabel.setText(msg)

    def _getTimerStr(self):
        dt = self._solverWidget.timeElapsed
        dm, ds = divmod(dt.seconds, 60)
        dh, dm = divmod(dm, 60)
        dh += dt.days * 24
        return "{0}:{1:02}:{2:02}".format(dh, dm, ds)

    @pyqtSlot(bool)
    def _solverFinished(self, solved):
        self._timer.stop()
        msg = "finished after " + self._getTimerStr()
        if solved:
            self._againButton.setVisible(True)
        else:
            msg += ", no solution found"
        self._setMessage(msg)
        self._abortButton.setText("close")

    @pyqtSlot(bool)
    def _abortClicked(self, _):
        self.close()

    @pyqtSlot(bool)
    def _againClicked(self, _):
        self._runSolve(again=True)

    @pyqtSlot()
    def _timerTick(self):
        self._setMessage("running for " + self._getTimerStr())
        self._solverWidget.repaint()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    main = FlowSolverAppWindow()
    main.show()
    sys.exit(app.exec_())
