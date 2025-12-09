import time
from .animations import Animation, get_locations
import numpy as np
import utils
import queue
import logging
#from libcamera import Transform
import sys
import cv2 as cv
from . import mapping
import threading
sys.path.append("../movenet")
from picamera2 import Picamera2
Picamera2.set_logging(Picamera2.ERROR)
from movenet import movenet

picam2 = None
KEYPOINT_DICT = {
    'nose': 0,
    'left_eye': 1,
    'right_eye': 2,
    'left_ear': 3,
    'right_ear': 4,
    'left_shoulder': 5,
    'right_shoulder': 6,
    'left_elbow': 7,
    'right_elbow': 8,
    'left_wrist': 9,
    'right_wrist': 10,
    'left_hip': 11,
    'right_hip': 12,
    'left_knee': 13,
    'right_knee': 14,
    'left_ankle': 15,
    'right_ankle': 16
}

class Ball:
    def __init__(self, radius, brightness, fade_decay, loc_decay, threshold):
        self.radius = radius
        self.base_brightness = brightness
        self.brightness = 0
        self.fade_decay = fade_decay
        self.loc_decay = loc_decay
        self.threshold = threshold
        self.location = np.array([0,0])

    def update(self, xy, conf):
        if(conf < self.threshold):
            if(self.brightness > 0):
                self.brightness *= self.fade_decay
                if(self.brightness < 10):
                    self.brightness = 0
        else:
            if(self.brightness < self.base_brightness):
                self.brightness = min(self.base_brightness, self.brightness*(1+self.loc_decay))
            self.location = xy*self.loc_decay+(1-self.loc_decay)*self.location

class CamReader(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  cam, *args, **kwargs):
        super(CamReader, self).__init__(*args, **kwargs)
        self.cam = cam
        self.frame_times = []
        self.net = movenet.MoveNet("movenet/4.tflite")
        self._stop_event = threading.Event()
        self.q = queue.Queue()

    def stop(self):
        if(len(self.frame_times)<=5):
            logging.debug("Not enough fps data")
        else:
            frame_times = np.array(self.frame_times)
            bins = np.arange(np.ceil(frame_times[0]), np.floor(frame_times[-1]))
            fps, _ = np.histogram(frame_times, bins=bins)
            fps = fps[1:-1]
            logging.debug(f"Avg FPS: {np.mean(fps):.2f}, Max FPS: {np.max(fps):.2f}, Min FPS: {np.min(fps):.2f}")

        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
    
    def run(self):
        while(True):
            frame = self.cam.capture_array("main")
            self.frame_times.append(time.time())
            #crop
            d = frame.shape[1]//4
            frame = frame[:, d:d*3]
            image = self.net.prepare_input(frame)
            xy, conf = self.net.get_prediction(image)
            h, w = frame.shape[0], frame.shape[1]
            movenet.scale_keypoints(xy, h, w)
            if self.stopped():
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()
                except queue.Empty:
                    pass
            self.q.put((xy,conf))
            time.sleep(1./30)
    
    def read(self):
        return self.q.get()

class Video(Animation):
    instructions = {
        "settings": ["color", "brightness", "background", "back_brightness", "confidence", "decay", "radius", "angle"],
        "color": {
            "type": "color",
            "default": "255,0,0",
            "presets": ["rainbow"],
        },
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 150},
        "background": {
            "type": "color",
            "default": "0,0,0"
        },
        "back_brightness": {"type": "int", "min": 0, "max": 255, "default": 0},
        "confidence": {"type": "float", "min": 0, "max": 1, "step": 0.01, "default": 0.3},
        "decay": {"type": "float", "min": 0, "max": 1, "default": 0.7},
        "radius": {
            "type": "float",
            "min": 0,
            "max": 1,
            "default": 0.3
        },
        "angle": {"type": "int", "min": 0, "max": 360, "default": 150}
    }

    def setup(self, **kwargs):
        self.num_leds = len(get_locations())
        self.confidence_threshold = kwargs.get("confidence", 0.3)
        self.decay = kwargs.get("decay", 0.7)
        self.radius = kwargs.get("radius", 33)
        c = kwargs.get("color", "255,0,0")
        self.brightness = max(0,min(255,kwargs.get("brightness", 255)))
        self.color = utils.parse_color_mode(c, brightness=self.brightness)
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}
        
        if(c != "rainbow"):
            self.background = utils.parse_color_mode(kwargs.get("background", "255,0,0"),
                                    brightness=max(0,min(255,kwargs.get("back_brightness", 255))))
        else:
            self.background = utils.parse_color_mode(c,
                                    brightness=max(0,min(255,kwargs.get("back_brightness", 255))))
        
        self._is_setup = True
        locs = get_locations()
        alpha = kwargs.get("angle", 0)%360
        alpha *= np.pi/180
        P = np.array([[np.cos(alpha), -np.sin(alpha)],[np.sin(alpha), np.cos(alpha)]])
        locs_2d = np.stack((locs[:,:2]@P.T[:,0], locs[:,2]), axis=1)

        indices, hull, edges = mapping.convex_hull(locs_2d, edges=True)
        self.projections = mapping.project(locs_2d,indices, edges)
        logging.debug("Projection X min/max: "+ f"{np.min(self.projections[:,0])}/{np.max(self.projections[:,0])}")
        logging.debug("Projection Y min/max: "+ f"{np.min(self.projections[:,1])}/{np.max(self.projections[:,1])}")
        
        picam2 = Picamera2(1)
        config = picam2.create_video_configuration(main={"size": (384,288), "format":"RGB888"})
        picam2.align_configuration(config)
        picam2.configure(config)
        Picamera2.set_logging(Picamera2.ERROR)
        self.picam2 = picam2
        self.reader = CamReader(self.picam2)
        return {"success": True}

    def human_identification(self, xy, conf):
        return np.sum(conf>self.confidence_threshold)>5

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        self.picam2.start()
        self.reader.start()
        iA, iB = 0, 0
        human_counter = 0
        width, height = 288, 384
        circles = {key: Ball(self.radius, self.brightness, 0.9, self.decay, self.confidence_threshold)
                   for key in ["nose", "left_wrist", "right_wrist", "left_hip", "right_hip"]}
        print(circles)
        counterA = 0
        counterB = 50
        while not self._stop_event.is_set():
            xy, conf = self.reader.read()
            xy[:,0] = (xy[:,0]/width)*2-1
            xy[:,1] = (xy[:,1]/height)*2-1
            # first check if there's a human present
            if(self.human_identification(xy, conf)):
                human_counter += 1
                print("Human counter: ", human_counter)
            else:
                human_counter = 0
            # then run the animation
            if(human_counter > 5):
                for key in circles:
                    i = KEYPOINT_DICT[key]
                    circles[key].update(xy[i], conf[i])

            color = self.background(counterA, 100, iA)
            for idx in range(self.num_leds):
                self.strip.setPixelColor(int(idx), color)
            color = self.color(counterB, 100, iB)
            for name in circles:
                circle = circles[name]
                dists = np.sum(np.square(self.projections-np.expand_dims(circle.location,axis=0)),axis=1)
                for idx in np.where(dists<self.radius)[0]:
                    self.strip.setPixelColor(int(idx), color)

            self.strip.show()
            counterA += 1
            if(counterA > 100):
                counterA = 0
                iA += 1
            counterB += 1
            if(counterB > 100):
                counterB = 0
                iB += 1
            time.sleep(1./30)
        self.reader.stop()
        self.reader.join()
        self.picam2.close()