import sys
import json
from PyQt6.QtCore import QThread, pyqtSignal
from websockets import connect
import asyncio
import websockets as ws
from websockets import ConnectionClosed


class WebSocketClient(QThread):
    textMessageReceived = pyqtSignal(str)
    videocallReceived = pyqtSignal()
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, url, user_id):
        super().__init__()
        self.url = url
        self.user_id = user_id
        self.websocket = None

    async def websocket_handler(self):
        while True:
            try:
                async with connect(self.url) as websocket:
                    self.websocket = websocket  # 保存 websocket 对象
                    self.connected.emit()
                    await websocket.send(json.dumps({"type": "initial", "user_id": self.user_id}))
                    while True:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                            self.textMessageReceived.emit(message)
                        except asyncio.TimeoutError:
                            # print("Timeout waiting for message")
                            continue  # 超时后继续等待消息
                        except ConnectionClosed as e:
                            if e.code == 1006:
                                # print('restart')
                                await asyncio.sleep(2)
                                break
            except ConnectionRefusedError as e:
                print(e)
                global count
                if count == 10:
                    return
                count += 1
                await asyncio.sleep(2)
            finally:
                self.disconnected.emit()

    async def send_message(self, data):
        if self.websocket:
            await self.websocket.send(data)

    def run(self):
        asyncio.run(self.websocket_handler())
