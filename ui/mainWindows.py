import asyncio
import json
import os
import base64
import shutil
import time
import signal
import threading
from functools import partial
import qfluentwidgets
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import QUrl, QByteArray, QTimer, pyqtSlot, QEventLoop, QThread
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QNetworkReply, QNetworkAccessManager, QNetworkRequest
from PyQt6.QtWidgets import QListWidgetItem
from qfluentwidgets import IconWidget, AvatarWidget, ListWidget, ScrollArea, TransparentToolButton, MessageBox, \
    RoundMenu, Action, FluentIcon, DotInfoBadge, Dialog, MessageBoxBase
from LoginWindow import Ui_MainWindow2
from mainlist import Ui_mainList  # 确保文件名和类名正确
from add_friend_window import add_friend_window
from charWindow import Chat_Window, BubbleMessage
from registWindow import RegisteWindow
from websockets import connect
from Qwebsocket import WebSocketClient
from qasync import QEventLoop, asyncSlot
import webbrowser


class GlobalVariable:
    user_id = None
    user_avatar = None


class MainWindow(QtWidgets.QMainWindow, Ui_mainList):
    def __init__(self):
        super().__init__()
        # 初始化WebSocke
        self.websocket = WebSocketClient("ws://localhost:18080/ws", GlobalVariable.user_id)
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
        self.add_friend = TransparentToolButton(QIcon(r"D:\Icon\add_friend.ico"), parent=self)
        self.add_friend.setGeometry(QtCore.QRect(340, 98, 31, 31))
        self.add_friend.setObjectName("add_friend")
        self.add_friend.clicked.connect(self.to_add_friend)
        self.unread_messages = {}



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
            if sender in self.chat_windows:
                self.chat_windows[sender].receive_message(message_data["message"])
            else:
                # 存储未读消息
                if sender not in self.unread_messages:
                    self.unread_messages[sender] = []
                self.unread_messages[sender].append(message_data["message"])
                self.update_badge_status(sender, 1)
        elif message_data["type"] == "video_call":
            sender = message_data["sender"]
            self.show_video_call_dialog(sender)

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
        url = QUrl(f'http://localhost:18080/friends_list?user_id={GlobalVariable.user_id}')
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
                print("路径不存在，执行创建操作")
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
            self.FriendlistWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            self.FriendlistWidget.customContextMenuRequested.connect(lambda pos, fr=friend: self.fr_menu(pos, fr))


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

    def request_avatar(self, user_id):
        url = QUrl('http://localhost:18080/get_avatar')
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

        if chat_id in self.chat_windows:
            print("existed")
            # 如果聊天窗口已存在，则显示该窗口
            self.chat_windows[chat_id].show()
            self.chat_windows[chat_id].raise_()  # 将窗口置于最前
        else:
            # 如果聊天窗口不存在，则创建新窗口
            chat_window = ChatWindow(info,self.websocket)
            self.chat_windows[chat_id] = chat_window
            chat_window.show()
            # 显示未读消息
            if chat_id in self.unread_messages:
                for msg in self.unread_messages[chat_id]:
                    chat_window.receive_message(msg)
                del self.unread_messages[chat_id]
                self.update_badge_status(chat_id, 0)


    def chatWindowClosed(self, username):
        # 从字典中移除已关闭的聊天窗口
        if username in self.chat_windows:
            del self.chat_windows[user]

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

    def show_video_call_dialog(self, sender):
        dialog = VideoBox(sender)
        if dialog.exec():
            data = {'type': 'video_call_back', 'result': "accept", "receiver": sender}
            self.websocket.send_message(json.dumps(data))
            url = r"http://localhost:9998?role=receiver&user_id="+str(GlobalVariable.user_id)+"&chater_id="+str(sender);
            webbrowser.open(url)
        else:
            data={'type': 'video_call_back', 'result':"reject", "receiver": sender}
            self.websocket.send_message(json.dumps(data))


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
        url = QUrl('http://localhost:18080/login')
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

    def update_status(self, status_code):
        url = QUrl('http://localhost:18080/update_status')
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
            url = QUrl('http://localhost:18080/register')
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
        url = QUrl('http://localhost:18080/send_friend_request')
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
        url = QUrl(f'http://localhost:18080/pending_friend_requests?user_id={GlobalVariable.user_id}')
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
        url = QUrl('http://localhost:18080/accept_friend_request')
        self.send_request(url, request)

    def handle_reject_request(self, request):
        url = QUrl('http://localhost:18080/unaccept')
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

        # 添加 QShortcut
        self.shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self)
        self.shortcut.activated.connect(self.send_message_wrapper)

    #     self.message_queue = asyncio.Queue()
    #     asyncio.create_task(self.process_message_queue())
    #
    # async def process_message_queue(self):
    #     while True:
    #         message_data = await self.message_queue.get()
    #         await self.save_message(message_data)

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
                    "receiver": self.info["user_id"]
                }
                await self.websocket.send_message(json.dumps(data))
                url = r"http://localhost:9998?role=caller&user_id=" + str(GlobalVariable.user_id) + "&chater_id=" + str(
                    self.info["user_id"]);
                # url = r"http://baidu.com"
                webbrowser.open(url)
            else:
                w=MessageBox("无法发起通话！","该用户不在线/正忙 ！", self)
                w.exec()




    def send_message_wrapper(self,type):
        loop = asyncio.get_running_loop()
        loop.create_task(self.send_message(type))

    def receive_message(self, message):
        if message:
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
    def __init__(self, sender,parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("视频通话")
        avatar_path = os.path.join("other", "avatar", str(sender) + ".png")
        self.avatar = Avatar()
        self.avatar.setImage(avatar_path)
        self.avatar.setRadius(32)

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.avatar)

        # 设置对话框的最小宽度
        self.widget.setMinimumWidth(350)



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