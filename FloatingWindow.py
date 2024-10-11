import sys

import co_caculate
import qfluentwidgets
from PyQt6.QtWidgets import QApplication, QWidget, QToolTip
from PyQt6.QtGui import QMouseEvent, QMovie
from PyQt6.QtCore import Qt
from qfluentwidgets import ImageLabel


class FloatingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = ImageLabel(self)
        self.label.setImage(r"icon/Infinity3.png")
        self.label.scaledToHeight(100)
        # self.movie = QMovie(r"icon/Infinity.gif")  # 设置GIF路径
        # self.label.setMovie(self.movie)
        # self.movie.start()
        self.label.setScaledContents(True)
        self.label.resize(100, 100)  # 设置悬浮球大小

        self.resize(100, 100)
        self.show()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_position)
            self.drag_position = event.globalPosition().toPoint()

    def taskStart(self):
        self.movie = QMovie(r"icon/Infinity.gif")  # 设置GIF路径
        self.label.setMovie(self.movie)
        self.movie.start()


class Co_WorkWindow(qfluentwidgets.FluentWindow):
    def __init__(self):
        super().__init__()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    # floating_window = FloatingWindow()
    # floating_window.show()
    Co = Co_WorkWindow()
    Co.show()
    app.exec()
