#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2 as cv
from time import sleep
import queue, threading
import numpy as np
from math import ceil, floor
import requests
import argparse

show = True

rotation = 315
num_leds = 100

brightness = 50
saturation = 100
contrast = 50
#BGR
lower = np.array([100,100,100])
upper = np.array([255,255,255])

rest_url = "http://raspberrypi4.local/api"

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
    visited = np.zeros(x.shape, dtype=np.bool)
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
        if(r<2.5):
            continue
        circularity = cluster.shape[0]/(np.pi*(r**2))
        if(circularity>0.3):
            return c, r, binary
        else:
            if(circularity>best_circularity):
                best_circularity = circularity
                best = i
    if(best is not None):
        c, r = mean_enclosing_circle(clusters[best])
        return c, r, binary
    return None, None, binary

def turn_off():
    response = requests.post(rest_url+"/all/", json={"power": False})
    if(response.status_code!=200):
        print("Failed to turn off power...")

def all_on():
    response = requests.post(rest_url+"/all/", json={"power": True, "state": True, "color": "255,0,0", "brightness": 255})
    if(response.status_code!=200):
        print("Could not turn leds on", response.status_code)
        return
    input("Press enter to continue...")
    turn_off()

def main(**kwargs):
    if(kwargs["action"]=='all-on'):
        all_on()
    elif(kwargs["action"]=="auto"):
        loop(auto=True, delay=kwargs["delay"], do_analysis=kwargs["analyse"])

def toggle_led(id:int, state:bool):
    post_request = {"id": id, "color": "255,0,0", "state": state, "brightness": 255}
    count = 0
    while(count<5):
        count += 1
        print("sending ", post_request)
        response = requests.patch(rest_url+'/leds/', json=post_request) #turn on that led
        if(response.status_code==200):
            return True
        else:
            msg = ""
            try:
                msg = response.json()["message"]
            except ValueError:
                pass
            print("Received http code {:d}, trying again. ({:d}). Message: '{:s}'".format(response.status_code, count, msg))
    return False

def loop(auto:bool=False, delay:int=1000, do_analysis:bool=False):
    cam = cv.VideoCapture(0)
    reader = CamReader(cam)
    #t = threading.Thread(target=lambda: reader(cam))
    reader.daemon = True
    reader.start()

    cv.namedWindow("cam-raw", cv.WINDOW_AUTOSIZE)
    if(do_analysis):
        cv.namedWindow("cam-processed", cv.WINDOW_AUTOSIZE)
    #10 -> brightness
    #11 -> contrast
    #12 -> saturation
    print(f"Brightness {brightness:d}; saturation {saturation:d}; contrast {contrast:d}")
    cam.set(10, brightness)
    cam.set(11, contrast)
    cam.set(12, saturation)
    
    #first, turn all leds off
    response = requests.post(rest_url+"/all/", json={"power": True})
    if(response.status_code!=200):
        print("Failed to turn on power...")
        return
    response = requests.post(rest_url+"/all/", json={"state": False})
    if(response.status_code!=200):
        print("Failed to turn off all leds...")
        return
    
    def show_led(i:int):
        if(toggle_led(i, True)):
            #response == OK, so the led should be on right now. But for safety, wait 0.2s
            sleep(.2)
            img = reader.read() #read image from webcam
            w = img.shape[1]
            img = img[:, w//4:w//4*3, :]
            copy = img.copy()

            cv.imshow("cam-raw", img)
            if(do_analysis):
                c, r, binary = process_image(img) #extract the largest roughly circular cluster
                if(c is not None and r is not None):
                    cv.circle(copy, (int(c[1]), int(c[0])), int(r), (200,21,5), 2) #draw a circle around the led
                binary[binary>0] = 255
                cv.imshow("cam-processed", copy)
            if(not toggle_led(i, False)):
                return False
            return True
        return False

    if(auto):
        for i in range(num_leds):
            sleep(delay/1000)
            show_led(i)
            if(cv.waitKey(1)==27):
                break
    else:
        s = ""
        while(s.lower() not in ["quit", "q", "exit"]):
            try:
                if(len(s)>0):
                    i = int(s)
                    if(0<=i<100):
                        show_led(i)
                        if(cv.waitKey(1)==27):
                            break
                s = input("Enter ID:")
            except ValueError:
                print("That is not a valid integer. Type 'quit' to exit.")
    
    if(do_analysis):
        cv.destroyWindow("cam-processed")
    cv.destroyWindow("cam-raw")
    reader.stop()
    reader.join()
    cam.release()
    turn_off()
    
if __name__=="__main__":
    parser = argparse.ArgumentParser(description="Tool to check if all the LEDs are visible and positioned correctly")
    parser.add_argument("action", help="Action to perform", choices=["all-on", "auto", "manual"])
    parser.add_argument("--delay", help="Delay for auto looping in milliseconds", type=int, default=1000)
    parser.add_argument("--analyse", help="Perform the location finding analysis", action='store_true')
    args = vars(parser.parse_args())
    main(**args)