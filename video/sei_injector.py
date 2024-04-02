import platform
import subprocess

plat = platform.system().lower()


class SEIInjector:
    command = ['video/ffmpeg_sei_insert.exe' if plat == 'windows' else 'video/ffmpeg_sei_insert']

    def __init__(self, rtsp_url, rtmp_url):
        self.pipe = subprocess.Popen(self.command + [rtsp_url, rtmp_url], shell=False, stdout=subprocess.DEVNULL)

    def release(self):
        if self.pipe:
            self.pipe.terminate()
