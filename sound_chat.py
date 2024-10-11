import pyaudio
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack


class MicStreamTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=48000,
                                      input=True,
                                      frames_per_buffer=1024)

    async def recv(self):
        frame = await asyncio.get_event_loop().run_in_executor(None, self.stream.read, 1024)
        return frame


class SpeakerStreamTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=48000,
                                      output=True,
                                      frames_per_buffer=1024)

    async def recv(self):
        frame = await super().recv()
        audio_data = frame.to_ndarray()
        self.stream.write(audio_data)
        return frame


async def main():
    pc = RTCPeerConnection()

    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            speaker_track = SpeakerStreamTrack()
            pc.addTrack(speaker_track)

    mic_track = MicStreamTrack()
    pc.addTrack(mic_track)

    # 假设我们已经有一个远程描述
    remote_description = RTCSessionDescription(sdp="some_sdp", type="offer")
    await pc.setRemoteDescription(remote_description)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # 保持连接
    await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
