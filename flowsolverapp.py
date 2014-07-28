#!/usr/bin/env python

from datetime import datetime
from PyQt4.QtCore import QTimer, pyqtSlot
from PyQt4.QtGui import QApplication, QMainWindow, QColor, QPushButton, \
    QDialog, QStatusBar, QLayout, QBoxLayout, QLabel
from QSquareWidget import QSquareWidgetContainer
from flowboardeditor import FlowBoardEditor
from flowsolverwidget import FlowSolverWidget


class FlowSolverAppWindow(QMainWindow):
    def __init__(self):
        super(FlowSolverAppWindow, self).__init__()
        self.setWindowTitle("flow solver")

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

    def solve(self):
        popup = FlowSolvingPopup(self, self._editor.getBoard())
        popup.setModal(True)
        popup.show()
        popup.runSolve()

    @pyqtSlot(bool)
    def _solveClicked(self, _):
        self.solve()


class FlowSolvingPopup(QDialog):
    def __init__(self, parent, board):
        super(FlowSolvingPopup, self).__init__(parent)
        self._board = board
        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setSpacing(0)
        layout.setMargin(0)

        self._solverWidget = FlowSolverWidget(self._board)
        layout.addWidget(self._solverWidget)

        status = QStatusBar()
        status.setSizeGripEnabled(False)

        abort = QPushButton("cancel")
        abort.clicked.connect(self._abortClicked)
        status.addPermanentWidget(abort)

        self._messageLabel = QLabel("ready")
        status.addWidget(self._messageLabel)

        layout.addWidget(status)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)

        self._timer = QTimer()
        self._timer.timeout.connect(self._timerTick)
        self._startTime = None

        self._steps = 0

    def runSolve(self):
        if self._board.isValid():
            self._setMessage("running")
            self._startTime = datetime.now()
            self._timer.start(50)
        else:
            self._setMessage("board is not valid")

    def closeEvent(self, event):
        self._timer.stop()
        super(FlowSolvingPopup, self).closeEvent(event)

    def _setMessage(self, msg):
        self._messageLabel.setText(msg)

    def _setTimerMessage(self):
        dt = datetime.now() - self._startTime
        dm = dt.seconds // 60
        ds = dt.seconds - dm * 60
        dh = dm // 60
        dm -= dh * 60
        dh += dt.days * 24
        self._setMessage("running for {0}:{1:02}:{2:02}".format(dh, dm, ds))

    @pyqtSlot(bool)
    def _abortClicked(self, _):
        self.close()

    @pyqtSlot()
    def _timerTick(self):
        self._setTimerMessage()
        self._steps += 1
        print "run {0} steps".format(self._steps)
        self._solverWidget.run(self._steps)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    main = FlowSolverAppWindow()
    main.show()
    sys.exit(app.exec_())
