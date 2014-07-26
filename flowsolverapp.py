#!/usr/bin/env python

from PyQt4.QtGui import QApplication, QMainWindow, QColor
from QSquareWidget import QSquareWidgetContainer
from flowboardeditor import FlowBoardEditor, FlowBoardEditorToolBar


class FlowSolverWindow(QMainWindow):
    def __init__(self):
        super(FlowSolverWindow, self).__init__()
        self.setWindowTitle("flow solver")

        etb = FlowBoardEditorToolBar()
        etb.setFloatable(False)
        etb.setMovable(False)
        self.addToolBar(etb)

        tb = self.addToolBar("toobar")
        tb.setFloatable(False)
        tb.setMovable(False)
        tb.addAction("solve")

        editor = FlowBoardEditor(etb.selectedSize)
        editor.connectToolbar(etb)

        editorcontainer = QSquareWidgetContainer()
        editorcontainer.setMargin(20)
        editorcontainer.setWidget(editor)
        editorcontainer.setBackgroundColor(QColor(0, 0, 0))
        self.setCentralWidget(editorcontainer)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    main = FlowSolverWindow()
    main.show()
    sys.exit(app.exec_())
