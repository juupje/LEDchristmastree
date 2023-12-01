#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 20 17:07:46 2021

@author: joep
"""
import cv2 as cv
import queue, threading
from time import sleep

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

def simple():
    cam = cv.VideoCapture(0)
    reader = CamReader(cam)
    reader.daemon = True
    reader.start()
    cv.namedWindow("cam-raw", cv.WINDOW_AUTOSIZE)
    while(True):
        sleep(1./30)
        img = reader.read()
        h, w,_= img.shape
        img = cv.line(img, (w//2,0), (w//2, h), (0,0,255), thickness=2)
        
        cv.imshow("cam-raw", img)
        if(cv.waitKey(1)==27 or cv.waitKey(1)==13):
            break
    reader.stop()
    cv.destroyWindow("cam-raw")
    reader.join()
    cam.release()
    
simple()
