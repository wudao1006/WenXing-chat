# Form implementation generated from reading ui file 'vedio_chat.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.
import ctypes
import sys

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QUrl, Qt
import webbrowser
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QMainWindow
from qfluentwidgets import ScrollArea
from qframelesswindow import FramelessWindow


class Vedio_chat(FramelessWindow):
    def __init__(self, user_id, chat_id):
        super().__init__()
        self.setupUi(self)
        self.sender = user_id
        self.receiver = chat_id

    def setupUi(self,Form):
        Form.setObjectName("Form")
        Form.resize(700,600)
        self.scrollArea = ScrollArea(parent=Form)
        self.scrollArea.setGeometry(QtCore.QRect(0, 60, 700, 540))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setStyleSheet('''border-bottom:none;''')
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # self.browser = QWebEngineView(self)
        # self.browser.setUrl(QUrl("http://localhost:9998?role=caller&user_id=1&chater_id=10008"))
        # self.browser.setGeometry(QtCore.QRect(0,60,700,540))
        webbrowser.open(r"http://localhost:9998?role=caller&user_id=1&chater_id=10008")


    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Vedio_chat(1,10008)
    window.show()
    sys.exit(app.exec())
