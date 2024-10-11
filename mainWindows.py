import asyncio
import json
import os
import io
import base64
import shutil
import time
import signal
import threading
import qframelesswindow
from PIL import Image
from functools import partial
import qfluentwidgets
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import QUrl, QByteArray, QTimer, pyqtSlot, QEventLoop, QThread
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QNetworkReply, QNetworkAccessManager, QNetworkRequest
from PyQt6.QtWidgets import QListWidgetItem,QFileDialog,QToolTip
from qfluentwidgets import IconWidget, AvatarWidget, ListWidget, ScrollArea, TransparentToolButton, MessageBox, \
    RoundMenu, Action, FluentIcon, DotInfoBadge, Dialog, MessageBoxBase
from LoginWindow import Ui_MainWindow2
from mainlist import Ui_mainList  # 确保文件名和类名正确
from add_friend_window import add_friend_window
from charWindow import Chat_Window, BubbleMessage ,CustomMessageBox
from registWindow import RegisteWindow
from websockets import connect
from FloatingWindow import FloatingWindow
from Qwebsocket import WebSocketClient
from qasync import QEventLoop, asyncSlot
import webbrowser
import multiprocessing
import co_caculate



class GlobalVariable:
    user_id = None
    userName = None
    user_avatar = None
    chat_windows= {}
    is_working = False
    avatar_path = f"user/{user_id}/avatar.png"
    c_float = None

class GlobalURL:
    base_url = "http://localhost:18080/"
    ws_url = "ws://localhost:18080/ws"


class MainWindow(QtWidgets.QMainWindow, Ui_mainList):
    def __init__(self):
        super().__init__()
        # 初始化WebSocke
        self.websocket = WebSocketClient(GlobalURL.ws_url, GlobalVariable.user_id)
        self.websocket.disconnected.connect(self.on_disconnected)
        self.websocket.textMessageReceived.connect(self.on_message_received)
        self.websocket.errorOccurred.connect(self.on_error)

        # 在登录成功后连接WebSocket
        websocket_thread = threading.Thread(target=self.websocket.run)
        websocket_thread.start()

        self.setupUi(self)
        self.set_stylesheet()
        self.set_avatar()
        self.post_friend_list()
        self.add_friend = TransparentToolButton(QIcon(r"icon/add_friend.ico"), parent=self)
        self.add_friend.setGeometry(QtCore.QRect(340, 98, 31, 31))
        self.add_friend.setObjectName("add_friend")
        self.Co_Work = TransparentToolButton(QIcon(r"icon/cowork.png"),parent=self)
        self.Co_Work.setGeometry((QtCore.QRect(300,98,31,31)))
        self.Co_Work.setObjectName("Co_Work")
        self.add_friend.clicked.connect(self.to_add_friend)
        self.Co_Work.clicked.connect(self.is_startCoWork)
        self.unread_messages = {}
        self.pub_float = None
        self.FriendlistWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.FriendlistWidget.customContextMenuRequested.connect(self.show_fl_menu)




    def on_connected(self):
        print("WebSocket connected")
        # 发送包含 user_id 的初始化
        # initial_message = json.dumps({"type":"initial", "user_id": GlobalVariable.user_id}).encode('utf-8')
        # self.websocket.sendTextMessage(initial_message)

    def on_disconnected(self):
        print("WebSocket disconnected")

    def on_message_received(self, message):
        # 处理接收到的消息，并将其传递给相应的聊天窗口
        message_data = json.loads(message)
        if "sender" in message_data and "message" in message_data:
            sender = message_data["sender"]
            if sender in GlobalVariable.chat_windows:
                GlobalVariable.chat_windows[sender].receive_message(message_data["message"])
            else:
                # 存储未读消息
                if sender not in self.unread_messages:
                    self.unread_messages[sender] = []
                self.unread_messages[sender].append(message_data["message"])
                self.update_badge_status(sender, 1)
        elif message_data["type"] == "video_call":
            sender = message_data["sender"]
            sender_name = message_data["name"]
            self.show_video_call_dialog(sender,sender_name)
        elif message_data["type"] == "co_Invite":
            sender = message_data["publisher"]
            if sender in GlobalVariable.chat_windows:
                GlobalVariable.chat_windows[sender].addInvuteBubble(GlobalVariable.avatar_path, False)
                GlobalVariable.chat_windows[sender].show()
                GlobalVariable.chat_windows[sender].raise_()
            # 待补充跳出逻辑
        elif message_data["type"] == "Co_Start":
            GlobalVariable.c_float.CoStart()
            print("Co_Woro start")

        elif message_data["type"] == "Co_Close":
            GlobalVariable.c_float.close()
            GlobalVariable.c_float.deleteLater()
            GlobalVariable.c_float=None
            print("Co_Work is closed")

    def on_error(self, error):
        print(f"WebSocket error: {error}")

    def set_stylesheet(self):
        self.FriendlistWidget.setStyleSheet("""
            QListWidget::item:selected {
                background-color: #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)

    def post_friend_list(self):
        url=GlobalURL.base_url+f"friends_list?user_id={GlobalVariable.user_id}"
        url = QUrl(url)
        request = QNetworkRequest(url)
        # request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        # data = {
        #     'user_id': GlobalVariable.user_id
        # }
        # json_data = json.dumps(data).encode('utf-8')
        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.fl_handle)
        manager.get(request)

    def fl_handle(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data()
            friends = json.loads(response_data)
            if friends:
               self.update_fl(friends)
        else:
            print(f"Error: {reply.errorString()}")

    def update_fl(self, friends):
        self.FriendlistWidget.clear()
        for friend in friends:
            fr_id = friend["user_id"]
            avatar_path = r"other\avatar" + "\\" + str(fr_id) + ".png"
            if not os.path.exists(avatar_path):
                self.request_avatar(fr_id)
        for friend in friends:
            item = QListWidgetItem()
            item.setData(1,friend)  # 存储user_id
            widget = self.create_friend_widget(friend)
            # 检查是否有未读消息
            # if friend["user_id"] in self.unread_messages:
            #     DotInfoBadge.warning(parent=self, target=widget, position=DotInfoBadge.Position.TOP_RIGHT)
            item.setSizeHint(widget.sizeHint())
            self.FriendlistWidget.addItem(item)
            self.FriendlistWidget.setItemWidget(item, widget)


    def create_friend_widget(self, friend):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()

        fr_id = friend["user_id"]
        avatar_path = r"other\avatar" + "\\" + str(fr_id) + ".png"
        avatar_label = AvatarWidget()

        avatar_label.setImage(avatar_path)
        avatar_label.setRadius(16)

        name_label = QtWidgets.QLabel(friend["username"])
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        status_label = IconWidget()
        path = "icon\\" + friend["status"]+".png"
        status_label.setIcon(QIcon(path))
        status_label.setFixedSize(16, 16)

        layout.addWidget(avatar_label)
        layout.addWidget(name_label)
        layout.addWidget(status_label)
        layout.addStretch()  # 添加弹性空间，使布局更美观
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        widget.setLayout(layout)

        return widget

    def show_fl_menu(self, pos):
        item = self.FriendlistWidget.itemAt(pos)
        if item:
            friend = item.data(1)
            self.fr_menu(pos,friend)
    def fr_menu(self, pos, friend):
        menu = RoundMenu(self)
        menu.addAction(Action(FluentIcon.DELETE, '删除',triggered=lambda :self.delete_friend(friend)))
        menu.addAction(Action(FluentIcon.UPDATE, '刷新',triggered=lambda :self.refresh_friend_list()))

        # print("119")
        global_pos = QtCore.QPoint(self.mapToGlobal(pos).x(), self.mapToGlobal(pos).y()+100)
        action = menu.exec(global_pos)


    def refresh_friend_list(self):
        print("刷新好友列表")
        self.post_friend_list()

    def delete_friend(self, friend):
        print(f"删除好友: {friend['username']}")

    def set_avatar(self):
        user_folder = os.path.join("user", str(GlobalVariable.user_id))
        avatar_path = os.path.join(user_folder, "avatar.png")

        if os.path.exists(user_folder) and os.path.exists(avatar_path):
            self.avatar.setImage(avatar_path)
        else:
            os.makedirs(user_folder, exist_ok=True)
            self.request_avatar(GlobalVariable.user_id)
        self.avatar.setRadius(40)

        self.avatar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.avatar.customContextMenuRequested.connect(self.avatar_menu)

    def avatar_menu(self, pos):
        menu = RoundMenu(self)
        menu.addAction(Action(FluentIcon.UPDATE, '更换头像',triggered=lambda:self.change_avatar()))

        global_pos = QtCore.QPoint(self.mapToGlobal(pos).x(), self.mapToGlobal(pos).y())
        action = menu.exec(global_pos)

    def change_avatar(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择头像", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            with open(file_name, "rb") as image_file:
                image = Image.open(image_file)
                image = image.convert("RGB")  # Ensure image is in RGB mode
                output = io.BytesIO()
                image.save(output, format="PNG", optimize=True)
                output_size = output.tell()

                # 压缩图片
                quality = 95
                while output_size > 1 * 1024 * 1024 and quality > 10:
                    output = io.BytesIO()
                    image.save(output, format="PNG", optimize=True, quality=quality)
                    output_size = output.tell()
                    quality -= 5

                compressed_image_path = os.path.join("user", str(GlobalVariable.user_id), "avatar_t.png")
                with open(compressed_image_path, "wb") as f:
                    f.write(output.getvalue())
                print(f"Image saved successfully at {compressed_image_path}")

                self.avatar.setImage(compressed_image_path)
                self.avatar.setRadius(40)
                # 以base64编码发至后端
                encoded_string = base64.b64encode(output.getvalue()).decode('utf-8')
                self.send_avatar(encoded_string)

    def send_avatar(self, encoded_string):
        url = GlobalURL.base_url+"update_avatar"
        url=QUrl(url)
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        data = {
            'user_id': GlobalVariable.user_id,
            'avatar':encoded_string
        }
        json_data = json.dumps(data).encode('utf-8')
        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.handle_updateAvatar_response)
        manager.post(request, QByteArray(json_data))

    # 有问题
    def handle_updateAvatar_response(self,reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            print("update success!")
            t_path = os.path.join("user", str(GlobalVariable.user_id), "avatar_t.png")
            path = os.path.join("user", str(GlobalVariable.user_id), "avatar.png")
            os.replace(t_path,path)
    def request_avatar(self, user_id):
        url = GlobalURL.base_url+"get_avatar"
        url = QUrl(url)
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        data = {
            'user_id': user_id
        }
        json_data = json.dumps(data).encode('utf-8')
        if user_id == GlobalVariable.user_id:
            manager = QNetworkAccessManager(self)
            manager.finished.connect(self.handle_useravatar_response)
            manager.post(request, QByteArray(json_data))
        else:
            manager = QNetworkAccessManager(self)
            manager.finished.connect(lambda reply: self.handle_other_response(user_id, reply))
            manager.post(request, QByteArray(json_data))

    def handle_useravatar_response(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            avatar_base64 = json.loads(response_data).get('avatar', '')
            avatar_data = base64.b64decode(avatar_base64)

            user_folder = os.path.join("user", GlobalVariable.user_id)
            avatar_path = os.path.join(user_folder, "avatar.png")

            with open(avatar_path, 'wb') as avatar_file:
                avatar_file.write(avatar_data)

            self.avatar.setImage(avatar_path)
        else:
            print(f"Error: {reply.errorString()}")

    def handle_other_response(self, user_id, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            missing_padding = len(response_data) % 4
            if missing_padding:
                response_data += '=' * (4 - missing_padding)
            try:
                avatar_data = base64.b64decode(response_data)
            except EOFError as e:
                print(f"Base64 解码错误: {e}")
            avatar_path = os.path.join("other\\avatar", str(user_id) + ".png")
            with open(avatar_path, 'wb') as avatar_file:
                avatar_file.write(avatar_data)
        else:
            print(f"Error: {reply.errorString()}")

    def to_add_friend(self):
        add_friend = Add_fr()
        add_friend.show()

    def to_chatwindow(self, item):
        info = item.data(1)
        chat_id = info["user_id"]

        if chat_id in GlobalVariable.chat_windows:
            print("existed")
            # 如果聊天窗口已存在，则显示该窗口
            GlobalVariable.chat_windows[chat_id].show()
            GlobalVariable.chat_windows[chat_id].raise_()  # 将窗口置于最前
        else:
            # 如果聊天窗口不存在，则创建新窗口
            self.request_avatar(chat_id)
            chat_window = ChatWindow(info,self.websocket)
            GlobalVariable.chat_windows[chat_id] = chat_window
            chat_window.show()
            # 显示未读消息
            if chat_id in self.unread_messages:
                for msg in self.unread_messages[chat_id]:
                    chat_window.receive_message(msg)
                del self.unread_messages[chat_id]
                self.update_badge_status(chat_id, 0)

    # def chatWindowClosed(self, username):
    #     # 从字典中移除已关闭的聊天窗口
    #     if username in self.chat_windows:
    #         del self.chat_windows[user]

    # 有问题，徽章无法显示
    def update_badge_status(self, user_id, status):
        items = self.FriendlistWidget.findItems("*", QtCore.Qt.MatchFlag.MatchWildcard)
        for item in items:
            friend = item.data(1)
            if friend["user_id"] == user_id:
                if status == 0:
                    widget = self.FriendlistWidget.itemWidget(item)
                     # 移除红点标记
                    DotInfoBadge.success(parent=self.FriendlistWidget,target=widget)
                elif status == 1:
                    widget = self.FriendlistWidget.itemWidget(item)
                    DotInfoBadge.warning(parent=self.FriendlistWidget,target=widget, position=qfluentwidgets.InfoBadgePosition.TOP_RIGHT)
                break

    def show_video_call_dialog(self, sender,name):
        dialog = VideoBox(sender, name, self)
        if dialog.exec():
            data = {'type': 'video_call_back', 'result': "accept", "receiver": sender}
            self.websocket.send_message(json.dumps(data))
            url = r"http://localhost:9998?role=receiver&user_id="+str(GlobalVariable.user_id)+"&chater_id="+str(sender);
            webbrowser.open(url)
        else:
            data={'type': 'video_call_back', 'result':"reject", "receiver": sender}
            self.websocket.send_message(json.dumps(data))

    def is_startCoWork(self):
        w = MessageBox("协同", "是否要开启协同功能？", self)
        if w.exec():
            if GlobalVariable.is_working == False:
                self.pub_float=Floating_P()
                self.pub_float.show()
                GlobalVariable.is_working=True
            else:
                QtWidgets.QMessageBox.warning(self, "提示", "当前无法开启协同功能！（协同功能已开启）")
        else:
            print('取消')

    def start_event_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_forever()


class Login(Ui_MainWindow2):
    login_successful = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.registerButton.clicked.connect(self.to_register)
        self.login_button.clicked.connect(self.on_login)
        self.login_successful.connect(self.to_mainWindow)
        self.login_successful.connect(partial(self.update_status,1))
    def on_login(self):
        url = GlobalURL.base_url+"login"
        url = QUrl(url)
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')

        data = {
            'account': self.user_name.text(),
            'password': self.password.text(),
        }
        json_data = json.dumps(data).encode('utf-8')

        login_manager = QNetworkAccessManager(self)
        login_manager.finished.connect(self.handleResponse)
        login_manager.post(request, QByteArray(json_data))

    def handleResponse(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response = reply.readAll().data().decode()
            is_login = json.loads(response)["is_login"]
            if is_login:
                GlobalVariable.user_id = self.user_name.text()
                user_folder = os.path.join("user", GlobalVariable.user_id)
                GlobalVariable.user_avatar = os.path.join(user_folder, "avatar")
                user_json = os.path.join(user_folder, "user.json")
                if os.path.exists(user_json):
                    with open(user_json, "r") as f:
                        user_data = json.load(f)
                    GlobalVariable.userName=user_data["userName"]
                else:
                    url=GlobalURL.base_url+"getUser"
                    url=QUrl(url)
                    data = {
                        "account":GlobalVariable.user_id
                    }
                    json_data = json.dumps(data).encode('utf-8')
                    manager = QNetworkAccessManager(self)
                    manager.finished.connect(lambda reply: self.setInf(user_json, reply))
                    manager.post(QNetworkRequest(url), QByteArray(json_data))
                self.login_successful.emit()
                self.close()
            else:
                w = MessageBox(" ", "账号或密码错误！", self)
                w.setStyleSheet('''
                font-size:30px;
                ''')
                w.yesButton.hide()
                w.buttonLayout.insertStretch(0, 1)
                w.cancelButton.hide()
                w.buttonLayout.insertStretch(1)
                w.show()
                self.password.setText("")
                QTimer.singleShot(1000, lambda: w.close())
        else:
            print('Error:', reply.errorString())

    def setInf(self, path, reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response = reply.readAll().data().decode()
            response_data=json.loads(response)
            with open(path, "w") as f:
                json.dump(response_data, f)
            GlobalVariable.userName = response_data["userName"]
        else:
            print('Error:', reply.errorString())
    def update_status(self, status_code):
        url = GlobalURL.base_url+"update_status"
        url = QUrl(url)
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        data = {
            'user_id': GlobalVariable.user_id,
            'status_code': status_code,
        }
        json_data = json.dumps(data).encode('utf-8')

        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.handle_us)
        manager.post(request, QByteArray(json_data))

    def handle_us(self, reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
                print("Status updated successfully")
        else:
                print(f"Error: {reply.errorString()}")

    def update_user_id(self):
        self.user_name.setText(str(GlobalVariable.user_id))

    def to_register(self):
        register = Register()
        register.registration_successful.connect(self.update_user_id)
        register.show()

    def to_mainWindow(self):
        window = MainWindow()
        window.show()


class Register(RegisteWindow):
    registration_successful = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.pushButton.clicked.connect(self.register)

    def register(self):
        if len(self.username.text()) > 30:
            print("Please less than 30 characters")
        elif self.password.text() != self.confirm_psd.text():
            print("please confirm your password")
        else:
            url = GlobalURL.base_url+"register"
            url = QUrl(url)
            request = QNetworkRequest(url)
            request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
            data = {
                'username': self.username.text(),
                'password': self.password.text()
            }
            json_data = json.dumps(data).encode('utf-8')
            manager = QNetworkAccessManager(self)
            manager.finished.connect(self.r_handle)
            manager.post(request, json_data)

    def r_handle(self):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response = reply.readAll().data().decode()
            user_id = json.loads(response)["user_id"]
            # 创建用户文件夹
            folder_path = os.path.join("user", str(user_id))
            os.makedirs(folder_path, exist_ok=True)
            # 复制默认头像文件并重命名为avatar
            src_file = "moren.png"
            dst_file = os.path.join(folder_path, "avatar.png")
            shutil.copyfile(src_file, dst_file)

            GlobalVariable.user_id = user_id
            self.registration_successful.emit()
            self.close()
        else:
            print(f"Error: {reply.errorString()}")


class Add_fr(add_friend_window):
    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager()
        self.load_friend_requests()
        self.lineEdit.returnPressed.connect(self.search_friend)

    def search_friend(self):
        friend_id = self.lineEdit.text()
        url=GlobalURL.base_url+"send_friend_request"
        url = QUrl(url)
        request = QNetworkRequest(url)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        data = {
            'sender': GlobalVariable.user_id,
            'receiver': friend_id
        }
        json_data = json.dumps(data).encode('utf-8')

        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.handle_search_response)
        self.network_manager.post(request, QByteArray(json_data))

    def handle_search_response(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            result = json.loads(response_data).get('is_sent', False)
            if result:
                QtWidgets.QMessageBox.information(self, "提示", "您的好友请求已发送！")
            else:
                QtWidgets.QMessageBox.warning(self, "提示", "抱歉，该账号不存在！/ 无法添加这个账号")
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"请求失败: {reply.errorString()}")

    def load_friend_requests(self):
        url = GlobalURL.base_url+f"friend_requests?user_id={GlobalVariable.user_id}"
        # url = QUrl(f'http://localhost:18080/pending_friend_requests?user_id={GlobalVariable.user_id}')
        url=QUrl(url)
        request = QNetworkRequest(url)
        # request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, 'application/json')
        # data = {
        #     'user_id': GlobalVariable.user_id
        # }
        # json_data = json.dumps(data).encode('utf-8')
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self.handle_friend_requests_response)
        self.network_manager.get(request)

    def handle_friend_requests_response(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            response_data = json.loads(response_data)
            friend_requests = response_data.get('requests',[])  if response_data else {}
            if friend_requests:
               self.update_friend_requests(friend_requests)
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"请求失败: {reply.errorString()}")

    def update_friend_requests(self, friend_requests):
        self.listWidget.clear()
        for request in friend_requests:
            item = QListWidgetItem()
            item.setData(0, request)
            widget = self.create_friend_request_widget(request)
            item.setSizeHint(widget.sizeHint())
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, widget)

    def create_friend_request_widget(self, request):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()

        # avatar_label = AvatarWidget()
        # avatar_label.setImage(request["avatar"])
        # avatar_label.setRadius(20)

        name_label = QtWidgets.QLabel(request["senderName"])
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        id_label = QtWidgets.QLabel(f"ID: {request['sender']}")
        id_label.setStyleSheet("font-size: 12px;")

        # layout.addWidget(avatar_label)
        layout.addWidget(name_label)
        layout.addWidget(id_label)
        layout.addStretch()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        widget.setLayout(layout)

        widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(lambda pos, req=request: self.show_context_menu(pos, req))
        return widget

    def show_context_menu(self, pos, request):
        menu = RoundMenu(self)
        accept_action = menu.addAction(Action(FluentIcon.ACCEPT, '接受', triggered=lambda: self.handle_accept_request(request)))
        reject_action = menu.addAction(Action(FluentIcon.CANCEL, '拒绝', triggered=lambda: print("你拒绝了该用户的请求。")))
        g_pos = QtCore.QPoint(self.mapToGlobal(pos).x(), self.mapToGlobal(pos).y()+100)
        menu.exec(g_pos)


    def handle_accept_request(self, request):
        url = GlobalURL.base_url+"accept_friend_request"
        url = QUrl(url)
        self.send_request(url, request)

    def handle_reject_request(self, request):
        url=GlobalURL.base_url+"unaccept"
        url = QUrl(url)
        self.send_request(url, request)

    def send_request(self, url, request):
        request_data = {
            'request_id': request['request_id']
        }
        json_data = json.dumps(request_data).encode('utf-8')

        manager = QNetworkAccessManager(self)
        manager.finished.connect(lambda reply, req=request: self.handle_response(reply, req))
        manager.post(QNetworkRequest(url), QByteArray(json_data))

    def handle_response(self, reply: QNetworkReply, request):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            result = json.loads(response_data).get('is_request_accepted', False)
            if result:
                QtWidgets.QMessageBox.information(self, "提示", "操作成功！")
                self.mark_request_as_processed(request)
            else:
                QtWidgets.QMessageBox.warning(self, "提示", "操作失败！")
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"请求失败: {reply.errorString()}")

    def mark_request_as_processed(self, request):
        for index in range(self.listWidget.count()):
            item = self.listWidget.item(index)
            if item.data(0) == request:
                widget = self.listWidget.itemWidget(item)
                widget.setEnabled(False)
                break


class ChatWindow(Chat_Window):
    def __init__(self, chater_info, websocket):
        super().__init__()
        self.info = chater_info
        self.chater_name.setText(self.info["username"])
        self.avatar_main.setImage(r"other\avatar" + "\\" + str(chater_info["user_id"]) + ".png")
        self.avatar_main.setRadius(24)
        self.websocket = websocket
        self.history.clicked.connect(self.show_history)
        self.send.clicked.connect(lambda :self.send_message_wrapper("message"))
        self.messages = []
        self.sight_chat.clicked.connect(lambda :self.send_message_wrapper("video_call"))
        self.CoWork.clicked.connect(lambda :self.send_message_wrapper("co_Invite"))

        # 添加 QShortcut
        self.shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self)
        self.shortcut.activated.connect(lambda :self.send_message_wrapper("message"))

    #     self.message_queue = asyncio.Queue()
    #     asyncio.create_task(self.process_message_queue())
    #
    # async def process_message_queue(self):
    #     while True:
    #         message_data = await self.message_queue.get()
    #         await self.save_message(message_data)

    def closeEvent(self, event):
        # 在这里添加你想在关闭窗口时执行的额外处理
        del GlobalVariable.chat_windows[self.info["user_id"]]
        event.accept()

    # @asyncSlot()
    async def send_message(self,type):
        if type == "message":
            message = self.input_message.toPlainText()
            if message:
                avatar_path = r"user/" + str(GlobalVariable.user_id) + "/avatar.png"
                message_data = json.dumps(
                    {"type": "message", "sender": GlobalVariable.user_id, "receiver": self.info["user_id"],
                     "message": message}).encode('utf-8')
                await self.websocket.send_message(message_data)
                self.addChatBubble(avatar_path, message, True)
                self.input_message.clear()
                # await self.message_queue.put(message_data)
                # self.messages.append(json.dumps({
                #                 "is_user": True,
                #                 "message": message
                #             }))
                self.save_message(json.dumps({
                    "is_user": True,
                    "message": message
                }))
        elif type == "video_call":
            if self.info["status"] == "1":
                data = {
                    "type": "video_call",
                    "sender": GlobalVariable.user_id,
                    "sender_name": GlobalVariable.userName,
                    "receiver": self.info["user_id"]
                }
                await self.websocket.send_message(json.dumps(data))
                url = r"http://localhost:9998?role=caller&user_id=" + str(GlobalVariable.user_id) + "&chater_id=" + str(
                    self.info["user_id"]);

                webbrowser.open(url)
            else:
                w=MessageBox("无法发起通话！","该用户不在线/正忙 ！", self)
                w.exec()
        elif type == "co_Invite":
            if self.info["status"] == "1" or self.info["status"] == "0":
                avatar_path = r"user/" + str(GlobalVariable.user_id) + "/avatar.png"
                data = {
                    "type": "co_Invite",
                    "sender": GlobalVariable.user_id,
                    "receiver": self.info["user_id"]
                }
                await self.websocket.send_message(json.dumps(data))
                self.addInvuteBubble(avatar_path, True)
            else:
                w=MessageBox("无法发起协同！","该用户不在线/正忙 ！", self)
                w.exec()

    def send_message_wrapper(self,type):
        loop = asyncio.get_running_loop()
        loop.create_task(self.send_message(type))

    def receive_message(self, message):
        # if type == "message":(以后用于区分文本消息，图片消息，和视频、语音消息）
            print(f"{GlobalVariable.user_id} received message")
            avatar_path = r"other\avatar" + "\\" + str(self.info["user_id"]) + ".png"
            self.addChatBubble(avatar_path,message, False)
            # self.messages.append(json.dumps({
            #                 "is_user": False,
            #                 "message": message
            #             }))
            self.save_message(json.dumps({
                "is_user": False,
                "message": message
            }))

    def addChatBubble(self, avatar_path, text, is_sender):
        bubble = BubbleMessage(text, avatar_path, "Text", is_sender)
        self.scrollAreaLayout.addWidget(bubble)
        self.scrollAreaLayout.addStretch()
        QTimer.singleShot(200, self.scrollToBottom)
        # self.messages.addItem(item)
        # self.messages.setItemWidget(item, bubble)

    def addInvuteBubble(self,avatar_path, is_sender):
        if is_sender == False:
           invite_button = qfluentwidgets.TransparentPushButton(QIcon(r"icon/cowork.png"), "对方发起协同请求，点击此处接受")
           # invite_button.setFixedSize(300,50)
           invite_button.clicked.connect(self.Ac_CoWork)
        else:
           invite_button = qfluentwidgets.TransparentPushButton(QIcon(r"icon/cowork.png"),"发起协同请求，正等待对方处理")


        # 设置计时器
        timer = QTimer(self)
        timer.timeout.connect(lambda: self.on_invite_timeout(invite_button))
        timer.start(60000)  # 设置60秒时效限制

        bubble = BubbleMessage("", avatar_path, "Co_Invite", is_sender, invite_button)
        self.scrollAreaLayout.addWidget(bubble)
        self.scrollAreaLayout.addStretch()
        QTimer.singleShot(200, self.scrollToBottom)

    def on_invite_timeout(self, invite_button):
        invite_button.setEnabled(False)
        invite_button.setText("请求已过期")

    def Ac_CoWork(self):
        if GlobalVariable.is_working == False:
            url=GlobalURL.base_url+"joinCoWork"
            url=QUrl(url)
            data = {
                'publisher': self.info["user_id"],
                'consumer': GlobalVariable.user_id
            }
            json_data = json.dumps(data).encode('utf-8')

            manager = QNetworkAccessManager(self)
            manager.finished.connect(self.handle_ac_cowork_response)
            manager.post(QNetworkRequest(url), QByteArray(json_data))
        else:
            QtWidgets.QMessageBox.critical(self, "错误", "you can't co_work with different publishers once")

    def handle_ac_cowork_response(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            response_data = json.loads(response_data)
            type = response_data["result"]
            if type == "success":
                GlobalVariable.c_float = Floating_C(self.info["username"], self.info["user_id"])
            else:
                QtWidgets.QMessageBox.critical(self, "错误", f"请求失败: {reply.errorString()}")
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"请求失败: {reply.errorString()}")

    # def co_start(self):
    #     self.c_float.taskStart()

    def scrollToBottom(self):
        scrollbar = self.scrollArea.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def save_message(self, message_data):
        user_id = GlobalVariable.user_id
        chater_id = self.info["user_id"]
        file_path = f"user\\{user_id}\\chat_history\\{chater_id}.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                chat_history = json.load(file)
        else:
            chat_history = []
        chat_history.append(message_data)
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(chat_history, file, ensure_ascii=False, indent=4)

    def show_history(self):
        user_id = GlobalVariable.user_id
        chater_id = self.info["user_id"]
        file_path = f"user\\{user_id}\\chat_history\\{chater_id}.json"
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                chat_history = json.load(file)
                # 将字符串转换为字典对象
                chat_history = [json.loads(message) if isinstance(message, str) else message for message in
                                chat_history]
            history_window = HistoryWindow(chat_history, user_id, chater_id, self.info["username"])
            history_window.show()

    # 在关闭窗口时，一次性将该窗口的信息保存至历史消息
    # def closeEvent(self, event):
        # 在窗口关闭时保存消息
        # user_id = GlobalVariable.user_id
        # chater_id = self.info["user_id"]
        # file_path = f"user\\{user_id}\\chat_history\\{chater_id}.json"
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # if os.path.exists(file_path):
        #     with open(file_path, 'r', encoding='utf-8') as file:
        #         chat_history = json.load(file)
        # else:
        #     chat_history = []
        # chat_history.extend(message)
        # with open(file_path, 'w', encoding='utf-8') as file:
        #     json.dump(chat_history, file, ensure_ascii=False, indent=4)
        # event.accept()



    # def eventFilter(self, source, event):
    #     if event.type() == QtCore.QEvent.Type.KeyPress and source is self.input_message:
    #         if event.key() == QtCore.Qt.Key.Key_Return:
    #             self.send_message()
    #             return True
    #     return super().eventFilter(source, event)



# def on_app_exit():
#     # 在应用程序退出时调用 update_status 函数
#     if GlobalVariable.user_id != None:
#        Login().update_status(0)# 例如，将状态更新为 0
#
# def signal_handler(sig, frame):
#     on_app_exit()
#     sys.exit(0)

class HistoryWindow(Chat_Window):
    def __init__(self, chat_history,user_id, chater_id, charter_name):
        super().__init__()
        self.setWindowTitle("Chat History")
        self.avatar_main.close()
        self.send.close()
        self.imageButton.close()
        self.history.close()
        self.voice_chat.close()
        self.file.close()
        self.sight_chat.close()
        self.CoWork.close()
        self.scrollArea_2.setGeometry(QtCore.QRect(0,350,0,0))
        self.input_message.setGeometry(QtCore.QRect(0,0,0,0))
        self.chater_name.setGeometry(QtCore.QRect(5,10,200,65))
        self.chater_name.setText(f"与{charter_name}的聊天记录")

        user_avatar = r"user/"+str(user_id)+"/avatar.png"
        chater_avatar = r"other/avatar/"+str(chater_id)+".png"
        try:
            for message in chat_history:
                if message["is_user"] == True:
                    self.addChatBubble(user_avatar, message["message"], True)
                else:
                    self.addChatBubble(chater_avatar, message["message"], False)
        except Exception as e:
            print(f"error:{e}")

        QTimer.singleShot(200, self.scrollToBottom)


    def addChatBubble(self, avatar_path, text, is_sender):
        bubble = BubbleMessage(text, avatar_path, "Text", is_sender)
        self.scrollAreaLayout.addWidget(bubble)
        self.scrollAreaLayout.addStretch()
        # self.messages.addItem(item)
        # self.messages.setItemWidget(item, bubble)

    def scrollToBottom(self):
        scrollbar = self.scrollArea.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


class VideoBox(MessageBoxBase):
    def __init__(self, sender, name, parent = None):
        super().__init__(parent)
        self.titleLabel = qfluentwidgets.SubtitleLabel(f"视频通话({name})")
        avatar_path = os.path.join("other", "avatar", str(sender) + ".png")
        self.avatar = qfluentwidgets.AvatarWidget()
        self.avatar.setImage(avatar_path)
        self.avatar.setRadius(32)

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.avatar)

        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(350)

# 协同接受方的悬浮球

def consumer(pub_id, con_id,stop_event):
    while not stop_event.is_set():
        co_caculate.setConnect(con_id)
        co_caculate.setConsumer(con_id, pub_id)
        # co_caculate.setImage("t1")
        co_caculate.Consumer(pub_id)

class Floating_C(FloatingWindow):
    def __init__(self,publisher,pub_id):
        super().__init__()
        self.publisher = publisher
        self.pub_id = pub_id
        # co_caculate.setConnect(int(GlobalVariable.user_id))
        # co_caculate.setConsumer(int(GlobalVariable.user_id), int(pub_id))

    def enterEvent(self, event):
        QToolTip.showText(event.globalPosition().toPoint(), f"协同对象：{self.publisher}", self)

    def contextMenuEvent(self, event):
        menu = RoundMenu(self)
        reject_action = menu.addAction(
            Action(FluentIcon.CLOSE, '退出协同计算', triggered=lambda: self.QuitCoWork()))
        restart_action = menu.addAction(
            Action(FluentIcon.UPDATE, '重连协同计算', triggered=lambda: self.RestartCoWork()))
        g_pos = event.globalPos()
        menu.exec(g_pos)

    async def run_consumer(self, stop_event):
        loop = asyncio.get_running_loop()
        # await loop.run_in_executor(None, co_caculate.Consumer, self.pub_id)
        process = multiprocessing.Process(target=consumer, args=(self.pub_id,int(GlobalVariable.user_id),stop_event))
        process.start()

        # 等待进程完成（异步）
        while process.is_alive():
            await asyncio.sleep(1)
        co_caculate.closeConnect()
        process.join()

    def CoStart(self):
        self.taskStart()
        self.stop_event = multiprocessing.Event()  # 初始化停止事件
        asyncio.create_task(self.run_consumer(self.stop_event))
        # asyncio.create_task(self.run_consumer())

    def RestartCoWork(self):
        if self.stop_event:
            self.stop_event.set()  # 触发停止事件
        self.stop_event = multiprocessing.Event()  # 重置停止事件
        asyncio.create_task(self.run_consumer(self.stop_event))

    def QuitCoWork(self):
        data={"publisher":self.pub_id,
              "consumer":GlobalVariable.user_id
              }
        json_data = json.dumps(data).encode('utf-8')
        url = GlobalURL.base_url+"quitCoWork"
        url=QUrl(url)
        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.handle_QCW)
        manager.post(QNetworkRequest(url), QByteArray(json_data))

    def handle_QCW(self,reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            # print(response_data)
            QtWidgets.QMessageBox.information(self, "提示", "已退出协同计算！")
            GlobalVariable.is_working = True
            GlobalVariable.c_float= None
            co_caculate.closeConnect()
            self.close()
            self.deleteLater()
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"关闭失败: {reply.errorString()}")


def GetResult(pub_id,stop_event):
    while not stop_event.is_set():
        co_caculate.setConnect(pub_id)
        co_caculate.getResult(pub_id)


# 协同发起方的悬浮球
class Floating_P(FloatingWindow):
    def __init__(self):
        super().__init__()
        self.consumers=0
        self.update_interval = 10000  # 设置查询间隔为10秒（10000毫秒）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.up_consumers)
        self.start_timer()
        self.initial()
        if not co_caculate.setConnect(int(GlobalVariable.user_id)):
            print("set connect error")
        if not co_caculate.setPublish(int(GlobalVariable.user_id)):
            print("set publish error")
        self.win = qframelesswindow.FramelessMainWindow()
        self.win.setGeometry(QtCore.QRect(600, 300, 400, 200))

    def initial(self):
        data={"publisher":GlobalVariable.user_id}
        json_data = json.dumps(data).encode('utf-8')
        url=GlobalURL.base_url+"initialCoWork"
        url=QUrl(url)
        manager = QNetworkAccessManager(self)
        manager.finished.connect(lambda:print("Initial success"))
        manager.post(QNetworkRequest(url),QByteArray(json_data))


    def enterEvent(self, event):
        QToolTip.showText(event.globalPosition().toPoint(), f"当前协同对象人数：{self.consumers}", self)

    def start_timer(self):
        self.timer.start(self.update_interval)

    def stop_timer(self):
        self.timer.stop()

    def up_consumers(self):
        try:
            url = GlobalURL.base_url+f"getConsumers?user_id={GlobalVariable.user_id}"
            url = QUrl(url)
            request = QNetworkRequest(url)
            manager = QNetworkAccessManager(self)
            manager.finished.connect(self.handle_up)
            manager.get(request)
        except Exception as e:
            print(f"请求出错：{e}")

    def handle_up(self, reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            response_data = json.loads(response_data)
            self.consumers = response_data["consumers"]
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"请求失败: {reply.errorString()}")
        # 重新设置定时器，定期更新消费者人数
        self.start_timer()

    def contextMenuEvent(self, event):
        menu = RoundMenu(self)
        accept_action = menu.addAction(
            Action(QIcon(r"icon/cowork.png"), '开启协同计算', triggered=lambda: self.StartCoWork()))
        reject_action = menu.addAction(
            Action(FluentIcon.CLOSE, '关闭协同计算', triggered=lambda: self.CloseCoWork()))
        message_action = menu.addAction(
            Action(FluentIcon.MESSAGE, '发布消息', triggered=lambda: self.publish_message()))
        Docker_action = menu.addAction(
            Action(QIcon(r"icon/docker.png"), '上传Dokcer镜像', triggered=lambda: self.publish_docker()))
        data_action = menu.addAction(
            Action(QIcon(r"icon/database.png"), '上传数据集', triggered=lambda:self.publish_data()))
        result_action = menu.addAction(
            Action(QIcon(r"icon/result.png"), '获取协同结果', triggered=lambda:self.getResult()))
        # refresh_action = menu.addAction(
        #     Action(FluentIcon.UPDATE, '重连结果队列', triggered=lambda: self.RestartCoWork()))
        g_pos = event.globalPos()
        menu.exec(g_pos)

    def StartCoWork(self):
        data={"publisher":GlobalVariable.user_id}
        json_data = json.dumps(data).encode('utf-8')
        url = GlobalURL.base_url+"startCoWork"
        url=QUrl(url)
        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.handle_SCW)
        manager.post(QNetworkRequest(url), QByteArray(json_data))

    def handle_SCW(self,reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            # print(response_data)
            QtWidgets.QMessageBox.information(self, "提示", "协同计算已开启！")
            self.taskStart()
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"开启失败: {reply.errorString()}")

    def CloseCoWork(self):
        data={"publisher":GlobalVariable.user_id}
        json_data = json.dumps(data).encode('utf-8')
        url = GlobalURL.base_url+"closeCoWork"
        url=QUrl(url)
        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.handle_CCW)
        manager.post(QNetworkRequest(url), QByteArray(json_data))

    def handle_CCW(self,reply:QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            response_data = reply.readAll().data().decode()
            # print(response_data)
            QtWidgets.QMessageBox.information(self, "提示", "协同计算已关闭！")
            GlobalVariable.is_working = True
            self.stop_timer()
            co_caculate.closeConnect()
            self.close()
        else:
            QtWidgets.QMessageBox.critical(self, "错误", f"关闭失败: {reply.errorString()}")

    def publish_message(self):
        self.win.show()
        w=CustomMessageBox(self.win)
        w.titleLabel.setText("请输入要发布的消息")
        w.urlLineEdit.setPlaceholderText("请在这输入")

        if w.exec():
            message = w.urlLineEdit.text()
            co_caculate.Publish(int(GlobalVariable.user_id), "message" , message)
        self.win.close()

    def publish_docker(self):
        self.win.show()
        w = CustomMessageBox(self.win)
        w.titleLabel.setText("请输入Docker镜像的ID")
        w.urlLineEdit.setPlaceholderText("请在这输入")

        if w.exec():
            message = w.urlLineEdit.text()
            co_caculate.Publish(int(GlobalVariable.user_id), "dockerfile", message)
        self.win.close()

    def publish_data(self):
        self.win.show()
        w = CustomMessageBox(self.win)
        w.titleLabel.setText("请输入数据子集的文件夹地址")
        w.urlLineEdit.setPlaceholderText("请在这输入(绝对地址/相对地址)")

        if w.exec():
            message = w.urlLineEdit.text()
            co_caculate.Publish(int(GlobalVariable.user_id), "datafile_direct", message)
        self.win.close()


    async def run_consumer(self, stop_event):
        loop = asyncio.get_running_loop()
        # await loop.run_in_executor(None, co_caculate.Consumer, self.pub_id)
        process = multiprocessing.Process(target=GetResult, args=(int(GlobalVariable.user_id),stop_event))
        process.start()

        # 等待进程完成（异步）
        while process.is_alive():
            await asyncio.sleep(1)
        co_caculate.closeConnect()
        process.join()

    def getResult(self):
        self.stop_event = multiprocessing.Event()  # 初始化停止事件
        asyncio.create_task(self.run_consumer(self.stop_event))

    def RestartCoWork(self):
        if self.stop_event:
            self.stop_event.set()  # 触发停止事件
        self.stop_event = multiprocessing.Event()  # 重置停止事件
        asyncio.create_task(self.run_consumer(self.stop_event))



# 单机测试两个实例
def run_instance(instance_id):
    app = QtWidgets.QApplication([])
    login_window = Login()
    login_window.setWindowTitle(f"Instance {instance_id}")
    login_window.show()
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    login_window = Login()
    login_window.show()

    # # 连接 aboutToQuit 信号到 on_app_exit 槽函数
    # app.aboutToQuit.connect(on_app_exit)
    #
    # # 捕捉系统信号以处理崩溃情况
    # signal.signal(signal.SIGINT, signal_handler)
    # signal.signal(signal.SIGTERM, signal_handler)
    # try:
    #     app.exec()
    # except Exception as e:
    #     # on_app_exit()
    #     sys.exit(1)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_forever()

    # 单机测试两个实例
    # 创建两个进程
    # process_1 = multiprocessing.Process(target=run_instance, args=(1,))
    # process_2 = multiprocessing.Process(target=run_instance, args=(2,))
    #
    # # 启动进程
    # process_1.start()
    # process_2.start()
    #
    # # 等待进程完成
    # process_1.join()
    # process_2.join()