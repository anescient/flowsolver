#!/usr/bin/env python

from datetime import datetime
from PyQt4.QtCore import Qt, QTimer, pyqtSlot
from PyQt4.QtGui import QApplication, QMainWindow, QColor, QPushButton, \
    QDialog, QStatusBar, QLayout, QBoxLayout, QLabel, QFileDialog, QMenuBar
from QSquareWidget import QSquareWidgetContainer
from flowboardeditor import FlowBoardEditor
from flowsolverwidget import FlowSolverWidget


class FlowSolverAppWindow(QMainWindow):
    def __init__(self):
        super(FlowSolverAppWindow, self).__init__()
        self.setWindowTitle("flow solver")
        self.setAcceptDrops(True)

        self._editor = FlowBoardEditor()
        self._editor.toolbar.setFloatable(False)
        self._editor.toolbar.setMovable(False)
        self.addToolBar(self._editor.toolbar)
        editorcontainer = QSquareWidgetContainer()
        editorcontainer.setMargin(20)
        editorcontainer.setWidget(self._editor)
        editorcontainer.setBackgroundColor(QColor(0, 0, 0))
        self.setCentralWidget(editorcontainer)

        tb = self.addToolBar("solve")
        tb.setFloatable(False)
        tb.setMovable(False)

        solve = QPushButton("solve")
        solve.clicked.connect(self._solveClicked)
        tb.addWidget(solve)

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
        self._solvepopup.runSolve(self._editor.getBoard())

    @pyqtSlot(bool)
    def _openClicked(self, _):
        filepath = QFileDialog.getOpenFileName(caption="open board")
        if filepath:
            self._editor.loadBoardFile(filepath)

    @pyqtSlot(bool)
    def _saveClicked(self, _):
        filepath = QFileDialog.getSaveFileName(caption="save board")
        if filepath:
            self._editor.saveBoardFile(filepath)


class FlowSolvingPopup(QDialog):
    def __init__(self, parent=None):
        super(FlowSolvingPopup, self).__init__(parent)

        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setSpacing(0)
        layout.setMargin(0)

        self._solverWidget = FlowSolverWidget()
        layout.addWidget(self._solverWidget)

        status = QStatusBar()
        status.setSizeGripEnabled(False)

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
        self._startTime = None

    def runSolve(self, board):
        if board.isValid():
            self._solverWidget.setBoard(board)
            self._setMessage("running")
            self._abortButton.setText("cancel")
            self._startTime = datetime.now()
            self._timer.start(50)
        else:
            self._solverWidget.setBoard(None)
            self._setMessage("board is not valid")

    def closeEvent(self, event):
        self._timer.stop()
        super(FlowSolvingPopup, self).closeEvent(event)

    def _setMessage(self, msg):
        self._messageLabel.setText(msg)

    def _getTimerStr(self):
        dt = datetime.now() - self._startTime
        dm = dt.seconds // 60
        ds = dt.seconds - dm * 60
        dh = dm // 60
        dm -= dh * 60
        dh += dt.days * 24
        return "{0}:{1:02}:{2:02}".format(dh, dm, ds)

    @pyqtSlot(bool)
    def _abortClicked(self, _):
        self.close()

    @pyqtSlot()
    def _timerTick(self):
        if self._solverWidget.doneSolving:
            self._timer.stop()
            self._setMessage("finished after " + self._getTimerStr())
            self._abortButton.setText("close")
        else:
            self._setMessage("running for " + self._getTimerStr())
            try:
                self._solverWidget.run()
            except:
                self._timer.stop()
                raise


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    main = FlowSolverAppWindow()
    main.show()
    sys.exit(app.exec_())
