from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput
import time, io
from flask import Response, render_template
from threading import Condition

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
    global picam2
    """Video streaming generator function."""
    picam2 = picam2 or Picamera2()
    picam2.configure(picam2.create_video_configuration(main={"size": (960, 720)}))
    output = StreamingOutput()
    picam2.start_recording(JpegEncoder(), FileOutput(output))
    try:
        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
    finally:
        print("Seems like the stream crashed or stopped!")
        picam2.stop_recording()
    '''for _ in picam.capture_file(stream, "jpeg"):
        stream.seek(0)
        frame = stream.read()
        
        time.sleep(0.2)
        stream.seek(0)
        stream.truncate()
    '''
def render_video():
    return Response(generate(),mimetype='multipart/x-mixed-replace; boundary=frame')

def render_webpage():
    return render_template(VIDEO_TEMPLATE)