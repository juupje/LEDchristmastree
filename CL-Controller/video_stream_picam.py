from picamera2 import Picamera2
from libcamera import Transform
import time, io
from flask import Response, render_template
from threading import Condition
import numpy as np
import logging
import cv2 as cv
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

def generate(usb=False):
    from movenet import movenet
    """Video streaming generator function."""
    if(usb):
        picam2 = Picamera2(1)
        config = picam2.create_video_configuration(main={"size": (384,288), "format":"RGB888"})
        picam2.align_configuration(config)
        picam2.configure(config)
        Picamera2.set_logging(Picamera2.ERROR)
    else:
        picam2 = Picamera2()
        Picamera2.set_logging(Picamera2.ERROR)
        config = picam2.create_video_configuration(transform=Transform(vflip=True, hflip=True),
                                                main={"size":(320,240),"format":"RGB888"},
                                                sensor={'output_size': (1640,1232)},
                                                raw={'format': 'SRGGB8'}, encode='main')
        picam2.align_configuration(config)
        logging.debug("chosen config:", config)
        picam2.configure(config)
        picam2.set_controls({"FrameRate": 10})
        logging.debug(picam2.camera_configuration()['sensor'])
    logging.debug(picam2.stream_configuration("main"))
    #output = StreamingOutput()
    #picam2.start_recording(JpegEncoder(), FileOutput(output))
    frame_times = []
    net = movenet.MoveNet("movenet/4.tflite")
    picam2.start()
    try:
        while True:
            #with output.condition:
            #    output.condition.wait()
            #    frame = output.frame
            #frame_times.append(time.time())
            frame = picam2.capture_array("main")
            #crop!
            d = frame.shape[1]//4
            print(frame.shape)
            frame = frame[:,d:d*3]
            frame_times.append(time.time())
            image = net.prepare_input(frame)
            xy, conf = net.get_prediction(image)
            if(np.sum(conf>0.3)>5):    
                h, w = frame.shape[0], frame.shape[1]
                movenet.scale_keypoints(xy, h, w)
                frame = movenet.overlay_graph(frame, *movenet.construct_graph(xy, conf, h, w, keypoint_threshold=0.3))
            frame = cv.imencode(".jpeg", frame)[1].tobytes()
            yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
    finally:
        logging.info("Seems like the stream crashed or stopped!")
        picam2.stop_recording()
        picam2.close()
        if(len(frame_times)<=5):
            logging.debug("Not enough fps data")
        else:
            frame_times = np.array(frame_times)
            bins = np.arange(np.ceil(frame_times[0]), np.floor(frame_times[-1]))
            fps, _ = np.histogram(frame_times, bins=bins)
            fps = fps[1:-1]
            logging.debug(f"Avg FPS: {np.mean(fps):.2f}, Max FPS: {np.max(fps):.2f}, Min FPS: {np.min(fps):.2f}")

def render_video():
    return Response(generate(usb=True),mimetype='multipart/x-mixed-replace; boundary=frame')

def render_webpage():
    return render_template(VIDEO_TEMPLATE)