import cv2
import asyncio
import pyaudio
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, AudioStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling, BYE
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt


class VideoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.local_view = QLabel(self)
        self.remote_view = QLabel(self)
        layout = QVBoxLayout()
        layout.addWidget(self.local_view)
        layout.addWidget(self.remote_view)
        self.setLayout(layout)

    def update_local_frame(self, frame):
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.local_view.setPixmap(pixmap)

    def update_remote_frame(self, frame):
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.remote_view.setPixmap(pixmap)


class VideoStreamTrack1(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Failed to read frame")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return frame


class AudioStreamTrack(AudioStreamTrack):
    def __init__(self):
        super().__init__()
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        frame = self.stream.read(1024)
        return frame


async def run(pc, signaling, video_widget):
    video_track = VideoStreamTrack1()
    audio_track = AudioStreamTrack()
    pc.addTrack(video_track)
    pc.addTrack(audio_track)

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            @track.on("frame")
            def on_frame(frame):
                video_widget.update_remote_frame(frame)

    await signaling.connect()
    await signaling.send(pc.localDescription)

    while True:
        obj = await signaling.receive()
        if isinstance(obj, RTCSessionDescription):
            await pc.setRemoteDescription(obj)
        elif obj is BYE:
            break


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    video_widget = VideoWidget()
    video_widget.show()

    pc = RTCPeerConnection()
    signaling = TcpSocketSignaling("localhost", 1234)
    asyncio.run(run(pc, signaling, video_widget))

    sys.exit(app.exec())
