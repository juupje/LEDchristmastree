#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Nov 20 17:07:46 2021

@author: joep
"""
import cv2 as cv
import queue, threading
from time import sleep
import numpy as np
from math import floor, ceil

lower = np.array([100,100,100])
upper = np.array([255,255,255])

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

def _collect_cluster(i, j, x, visited, r=1.45):
    cluster = [[i,j]]
    visited[i,j] = True
    r2 = r**2
    for k in range(ceil(max(i-r,0)), floor(min(i+r+1, x.shape[0]))):
        for l in range(ceil(max(j-r,0)), floor(min(j+r+1, x.shape[1]))):
            if(visited[k,l]): continue
            if(x[k,l]):
                if((i-k)**2+(j-l)**2<r2):
                    cluster += _collect_cluster(k, l, x, visited, r)
                    visited[k,l] = True
    return cluster

def find_clusters(x):
    clusters = []
    visited = np.zeros(x.shape, dtype=bool)
    for i in range(x.shape[0]):
        for j in range(x.shape[1]):
            if(visited[i,j]): continue
            if(x[i,j]):
                clusters.append(np.array(_collect_cluster(i,j, x, visited)))
    return clusters

def min_enclosing_circle(x):
    c = np.mean(x, axis=0)
    deviation = x-c #distance to center
    d = deviation[:,0]**2+deviation[:,1]**2
    return c, np.sqrt(np.max(d))
    
def mean_enclosing_circle(x):
    c = np.mean(x,axis=0)
    d = np.std(x,axis=0)
    return c, np.max(d)*1.5

def process_image(img):
    filtered = cv.bitwise_and(img, img, mask=cv.inRange(img, lower, upper))
    filtered = filtered.max(axis=2)
    binary = (filtered>200).astype(np.uint8)
    clusters = find_clusters(binary)
    sizes = [cluster.shape[0] for cluster in clusters]
    best = None
    best_circularity = 0
    for i in np.argsort(sizes)[::-1]:
        cluster = clusters[i]
        c, r = min_enclosing_circle(cluster)
        if(r<1):
            continue
        circularity = cluster.shape[0]/(np.pi*(r**2))
        if(circularity>0.3):
            return c, r, binary
        else:
            if(circularity>best_circularity):
                best_circularity = circularity
                best = i
    if(best is not None):
        c, r = mean_enclosing_circle(clusters[i])
        return c, r, binary
    return None, None, binary


def simple():
    cam = cv.VideoCapture(0)
    reader = CamReader(cam)
    reader.daemon = True
    reader.start()
    cv.namedWindow("cam-raw", cv.WINDOW_AUTOSIZE)
    while(True):
        sleep(.5)
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

def processed():
    cam = cv.VideoCapture(0)
    reader = CamReader(cam)
    reader.daemon = True
    reader.start()
    cv.namedWindow("cam-processed", cv.WINDOW_AUTOSIZE)
    while(True):
        sleep(.5)
        img = reader.read()
        img = img[:,img.shape[1]//4:(img.shape[1]*3)//4]
        h, w,_= img.shape
        img = cv.line(img, (w//2,0), (w//2, h), (0,0,255), thickness=2)
        c, r, _ = process_image(img)
        if(c is not None):
            cv.circle(img, (int(c[1]), int(c[0])), int(r), (255,255,0), 2) #draw a circle around the led
        cv.imshow("cam-processed", img)
        if(cv.waitKey(1)==27 or cv.waitKey(1)==13):
            break
    reader.stop()
    cv.destroyWindow("cam-processed")
    reader.join()
    cam.release()
    
simple()
