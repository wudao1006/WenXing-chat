# Form implementation generated from reading ui file 'mainwindow2.ui'
#
# Created by: PyQt6 UI code generator 6.4.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.
import json

from PyQt6.QtCore import QUrl
from qframelesswindow import FramelessWindow
from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow2(FramelessWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

    def setupUi(self, MainWindow2):
        MainWindow2.setObjectName("MainWindow2")
        MainWindow2.setFixedSize(643, 440)
        MainWindow2.setStyleSheet("")
        self.frame = QtWidgets.QFrame(parent=MainWindow2)
        self.frame.setGeometry(QtCore.QRect(10, 20, 621, 401))
        self.frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame.setObjectName("frame")
        self.user_name = LineEdit(parent=self.frame)
        self.user_name.setGeometry(QtCore.QRect(230, 130, 301, 41))
        self.user_name.setObjectName("user_name")
        self.username = QtWidgets.QLabel(parent=self.frame)
        self.username.setGeometry(QtCore.QRect(110, 130, 61, 31))
        self.username.setStyleSheet("font: 16pt \"Microsoft YaHei UI\";")
        self.username.setObjectName("username")
        self.psd = QtWidgets.QLabel(parent=self.frame)
        self.psd.setGeometry(QtCore.QRect(110, 210, 81, 31))
        self.psd.setStyleSheet("font: 16pt \"Microsoft YaHei UI\";")
        self.psd.setObjectName("psd")
        self.password = PasswordLineEdit(parent=self.frame)
        self.password.setGeometry(QtCore.QRect(230, 200, 301, 41))
        self.password.setObjectName("password")
        self.remember = QtWidgets.QCheckBox(parent=self.frame)
        self.remember.setGeometry(QtCore.QRect(160, 270, 98, 23))
        self.remember.setObjectName("remember")
        self.forget_psd = HyperlinkLabel(QUrl("http://www.baidu.com"), " forget?", parent=self.frame)
        self.forget_psd.setGeometry(QtCore.QRect(400, 260, 101, 30))
        self.forget_psd.setStyleSheet("""
                background-color: transparent;
                border: none;
                color: rgb(0, 85, 255);
                font: 12pt "Microsoft YaHei UI";
        """)
        # self.forget_psd.setText("")
        self.forget_psd.setObjectName("forget_psd")
        self.login_button = QtWidgets.QPushButton(parent=self.frame)
        self.login_button.setGeometry(QtCore.QRect(350, 300, 161, 51))
        self.login_button.setStyleSheet("background_color:rgb(170, 255, 255);\n"
                                        "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(0, 255, 255, 255));\n"
                                        "font: 16pt \"Microsoft YaHei UI\";\n"
                                        "border-radius:10px;\n"
                                        "border_style:outset;\n"
                                        "")
        self.login_button.setObjectName("login_button")
        self.label_4 = QtWidgets.QLabel(parent=self.frame)
        self.label_4.setGeometry(QtCore.QRect(210, -30, 531, 271))
        self.label_4.setStyleSheet("width:100px;\n"
                                   "height:60px;")
        self.label_4.setText("")
        self.label_4.setPixmap(QtGui.QPixmap(":/new/image/image/logo2(1).png"))
        self.label_4.setScaledContents(False)
        self.label_4.setObjectName("label_4")
        self.logo = AvatarWidget(parent=self.frame)
        self.logo.setGeometry(QtCore.QRect(40, 50, 54, 16))
        self.logo.setObjectName("logo")
        self.registerButton = QtWidgets.QPushButton(parent=self.frame)
        self.registerButton.setGeometry(QtCore.QRect(100, 300, 161, 51))
        self.registerButton.setStyleSheet("background_color:rgb(170, 255, 255);\n"
                                          "background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 rgba(0, 0, 0, 255), stop:1 rgba(0, 255, 255, 255));\n"
                                          "font: 16pt \"Microsoft YaHei UI\";\n"
                                          "border-radius:10px;\n"
                                          "border_style:outset;\n"
                                          "")
        self.label_4.raise_()
        self.user_name.raise_()
        self.username.raise_()
        self.psd.raise_()
        self.password.raise_()
        self.remember.raise_()
        self.forget_psd.raise_()
        self.login_button.raise_()
        self.registerButton.raise_()
        self.logo.raise_()

        self.retranslateUi(MainWindow2)
        QtCore.QMetaObject.connectSlotsByName(MainWindow2)

    def retranslateUi(self, MainWindow2):
        _translate = QtCore.QCoreApplication.translate
        MainWindow2.setWindowTitle(_translate("MainWindow2", "MainWindow2"))
        self.username.setText(_translate("MainWindow2", "账号"))
        self.psd.setText(_translate("MainWindow2", "密码"))
        self.remember.setText(_translate("MainWindow2", "记住我"))
        self.login_button.setText(_translate("MainWindow2", "登录"))
        self.registerButton.setText(_translate("MainWindow2", "注册"))
        self.logo.setText(_translate("MainWindow2", "TextLabel"))


from qfluentwidgets import AvatarWidget, HyperlinkLabel, LineEdit, PasswordLineEdit, MessageBox
