import time
from flask import Response, render_template
import numpy as np
import logging
import threading, queue
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

class CamReader(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  cam, *args, **kwargs):
        super(CamReader, self).__init__(*args, **kwargs)
        self.cam = cam
        self._stop_event = threading.Event()
        self.q = queue.Queue()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
    
    def run(self):
        while(True):
            ret, frame = self.cam.read()
            if not ret or self.stopped():
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put(frame)
    
    def read(self):
        return self.q.get()

def generate():
    import cv2 as cv
    from movenet import movenet
    """Video streaming generator function."""
    cam = cv.VideoCapture(0, cv.CAP_V4L)
    cam.set(cv.CAP_PROP_FPS, 10)
    reader = CamReader(cam)
    reader.daemon = True
    frame_times = []
    net = movenet.MoveNet("movenet/4.tflite")
    reader.start()
    try:
        while True:
            #with output.condition:
            #    output.condition.wait()
            #    frame = output.frame
            #frame_times.append(time.time())
            frame = reader.read()
            frame_times.append(time.time())
            print(frame_times[-1])
            image = net.prepare_input(frame)
            xy, conf = net.get_prediction(image)
            h, w = frame.shape[0], frame.shape[1]
            movenet.scale_keypoints(xy, h, w)
            frame = movenet.overlay_graph(frame, *movenet.construct_graph(xy, conf, h, w, keypoint_threshold=0.3))
            frame = cv.imencode(".jpeg", frame)[1].tobytes()
            yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
    finally:
        logging.info("Seems like the stream crashed or stopped!")
        reader.stop()
        reader.join()
        cam.release()
        if(len(frame_times)<=5):
            logging.debug("Not enough fps data")
        else:
            frame_times = np.array(frame_times)
            bins = np.arange(np.ceil(frame_times[0]), np.floor(frame_times[-1]))
            fps, _ = np.histogram(frame_times, bins=bins)
            fps = fps[1:-1]
            logging.debug(f"Avg FPS: {np.mean(fps):.2f}, Max FPS: {np.max(fps):.2f}, Min FPS: {np.min(fps):.2f}")

def render_video():
    return Response(generate(),mimetype='multipart/x-mixed-replace; boundary=frame')

def render_webpage():
    return render_template(VIDEO_TEMPLATE)