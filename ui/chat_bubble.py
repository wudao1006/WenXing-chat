from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPainter, QColor, QFont, QPixmap, QPolygon
from PyQt6.QtWidgets import QWidget, QListWidgetItem, QLabel, QSpacerItem, QSizePolicy, QHBoxLayout
from PyQt6 import QtCore, QtGui, QtWidgets


class Avatar(QLabel):
    def __init__(self, avatar, parent=None):
        super().__init__(parent)
        if isinstance(avatar, str):
            self.setPixmap(QPixmap(avatar).scaled(45, 45))
            self.image_path = avatar
        elif isinstance(avatar, QPixmap):
            self.setPixmap(avatar.scaled(45, 45))
        self.setFixedSize(QSize(45, 45))


class Triangle(QLabel):
    def __init__(self, Type, is_send=False, parent=None):
        super().__init__(parent)
        self.Type = Type
        self.is_send = is_send
        self.setFixedSize(6, 45)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super(Triangle, self).paintEvent(a0)
        if self.Type == MessageType.Text:
            painter = QPainter(self)
            triangle = QPolygon()
            if self.is_send:
                painter.setPen(QColor('#b2e281'))
                painter.setBrush(QColor('#b2e281'))
                triangle.setPoints(0, 20, 0, 35, 6, 25)
            else:
                painter.setPen(QColor('white'))
                painter.setBrush(QColor('white'))
                triangle.setPoints(0, 25, 6, 20, 6, 35)
            painter.drawPolygon(triangle)


class TextMessage(QLabel):
    heightSingal = pyqtSignal(int)

    def __init__(self, text, is_send=False, parent=None):
        super(TextMessage, self).__init__(text, parent)
        self.setFont(QFont('微软雅黑', 12))
        self.setWordWrap(True)
        self.setMaximumWidth(800)
        self.setMinimumWidth(100)
        self.setMinimumHeight(45)

        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        if is_send:
            self.setAlignment(Qt.AlignCenter | Qt.AlignRight)
            self.setStyleSheet(
                '''
                background-color:#b2e281;
                border-radius:10px;
                border-top: 10px solid #b2e281;
                border-bottom: 10px solid #b2e281;
                border-right: 10px solid #b2e281;
                border-left: 10px solid #b2e281;
                '''
            )
        else:
            self.setStyleSheet(
                '''
                background-color:white;
                border-radius:10px;
                border-top: 10px solid white;
                border-bottom: 10px solid white;
                border-right: 10px solid white;
                border-left: 10px solid white;
                '''
            )
        w = len(text) * 16 + 30
        if w < self.width():
            self.setMaximumWidth(w)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        super(TextMessage, self).paintEvent(a0)


class BubbleMessage(QWidget):
    def __init__(self, str_content, avatar, Type, is_send=False, parent=None):
        super().__init__(parent)
        self.isSend = is_send
        # self.set
        self.setStyleSheet(
            '''
            border:none;
            '''
        )
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 5, 5, 5)
        # self.resize(QSize(200, 50))
        self.avatar = Avatar(avatar)
        triangle = Triangle(Type, is_send)
        if Type == MessageType.Text:
            self.message = TextMessage(str_content, is_send)
            # self.message.setMaximumWidth(int(self.width() * 0.6))
        elif Type == MessageType.Image:
            self.message = ImageMessage(str_content)
        else:
            raise ValueError("未知的消息类型")

        self.spacerItem = QSpacerItem(45 + 6, 45, QSizePolicy.Expanding, QSizePolicy.Minimum)
        if is_send:
            layout.addItem(self.spacerItem)
            layout.addWidget(self.message, 1)
            layout.addWidget(triangle, 0, Qt.AlignTop | Qt.AlignLeft)
            layout.addWidget(self.avatar, 0, Qt.AlignTop | Qt.AlignLeft)
        else:
            layout.addWidget(self.avatar, 0, Qt.AlignTop | Qt.AlignRight)
            layout.addWidget(triangle, 0, Qt.AlignTop | Qt.AlignRight)
            layout.addWidget(self.message, 1)
            layout.addItem(self.spacerItem)
        self.setLayout(layout)


