from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput
from libcamera import Transform
import time, io
from flask import Response, render_template
from threading import Condition
import numpy as np


VIDEO_TEMPLATE = "video.html"

'''
How to get the camera to work:
install stuff with apt
sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-prctl libatlas-base-dev ffmpeg python3-pip
sudo apt install -y python3-pyqt5 python3-opengl #optional, if you want to use GUIs

#activate the conda environment
pip install picamera2

#create a symbolic link
ln -s /usr/lib/python3/dist-packages/libcamera $CONDA_PREFIX/lib/python3.xx/site-packages/libcamera
'''
picam2 = None

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

def generate():
    """Video streaming generator function."""
    picam2 = Picamera2()
    mode = picam2.sensor_modes[5]
    print(mode)
    config = picam2.create_video_configuration(transform=Transform(vflip=True), main={"size":(410,302)}, sensor={'output_size': (1640,1232)}, raw={'format': 'SRGGB8'}, encode='main')
    picam2.align_configuration(config)
    print(config)
    picam2.configure(config)
    picam2.set_controls({"FrameRate": 10})
    print(picam2.camera_configuration()['sensor'])
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))
    frame_times = []
    try:
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            frame_times.append(time.time())
            yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
    finally:
        print("Seems like the stream crashed or stopped!")
        picam2.stop_recording()
        picam2.close()
        frame_times = np.array(frame_times)
        bins = np.arange(np.ceil(frame_times[0]), np.floor(frame_times[-1]))
        fps, _ = np.histogram(frame_times, bins=bins)
        fps = fps[1:-1]
        print(f"Avg FPS: {np.mean(fps):.2f}, Max FPS: {np.max(fps):.2f}, Min FPS: {np.min(fps):.2f}")

def render_video():
    return Response(generate(),mimetype='multipart/x-mixed-replace; boundary=frame')

def render_webpage():
    return render_template(VIDEO_TEMPLATE)