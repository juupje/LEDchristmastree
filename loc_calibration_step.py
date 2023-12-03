#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import cv2 as cv
from time import sleep
import queue, threading
import numpy as np
from math import ceil, floor
import requests
import argparse
import os, shutil

num_leds = 100

brightness = 50
saturation = 100
contrast = 50
#BGR
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
        if(r<2):
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

def main(show:bool=True, rotation:int=0, leds:int=None):
    for x in ["raw", "filtered", "processed"]:
        os.makedirs(f"images/{x}/{rotation:d}", exist_ok=True)

    cam = cv.VideoCapture(0)
    reader = CamReader(cam)
    #t = threading.Thread(target=lambda: reader(cam))
    reader.daemon = True
    reader.start()

    if(show):
        cv.namedWindow("cam-binary", cv.WINDOW_AUTOSIZE)
        cv.namedWindow("cam-processed", cv.WINDOW_AUTOSIZE)
    #10 -> brightness
    #11 -> contrast
    #12 -> saturation
    print(f"Brightness {brightness:d}; saturation {saturation:d}; contrast {contrast:d}")
    cam.set(10, brightness)
    cam.set(11, contrast)
    cam.set(12, saturation)

    rest_url = "http://raspberrypi4.local:8080"
    
    #first, turn all leds off
    response = requests.post(rest_url+"/all/", json={"power": True})
    if(response.status_code!=200):
        print("Failed to turn on power...")
        return
    response = requests.post(rest_url+"/all/", json={"state": False})
    if(response.status_code!=200):
        print("Failed to turn off all leds...")
        return

    post_request = {"id": 0, "color": "255,0,0", "state": True, "brightness": 255}
    stop = False
    
    locs = np.full((num_leds,2), -1, dtype=np.int32)
    to_iter = leds or range(num_leds)
    for i in to_iter:
        post_request["id"] = i #select the next led
        post_request["state"] = True #turn it on
        count = 0
        while(count<5):
            count += 1
            print("sending ", post_request)
            response = requests.patch(rest_url+'/leds/', json=post_request) #turn on that led
            if(response.status_code==200):
                #response == OK, so the led should be on right now. But for safety, wait 0.5s
                sleep(.5)
                img = reader.read() #read image from webcam
                w = img.shape[1]
                img = img[:, w//4:w//4*3, :]
                copy = img.copy()
                c, r, binary = process_image(img) #extract the largest roughly circular cluster
                if(c is not None):
                    locs[i] = c
                    cv.circle(copy, (int(c[1]), int(c[0])), int(r), (200,21,5), 2) #draw a circle around the led
                binary[binary>0] = 255
                if(show):
                    cv.imshow("cam-processed", copy)
                    cv.imshow("cam-binary", binary)
                cv.imwrite(f"images/raw/{rotation:d}/{i:d}.jpg", img) #save the image to check
                cv.imwrite(f"images/filtered/{rotation:d}/{i:d}.jpg", binary) #save the image to check
                cv.imwrite(f"images/processed/{rotation:d}/{i:d}.jpg", copy) #save the image to check
                if(cv.waitKey(1)==27):
                    stop = True
                    break
                
                post_request["state"] = False #turn it off
                count2 = 0
                while(count2<5):
                    count2 += 1
                    response = requests.patch(rest_url +"/leds/", json=post_request)
                    if(response.status_code==200):
                        break
                    sleep(.1)
                else:
                    stop = True
                    break
                break
            else:
                msg = ""
                try:
                   msg = response.json()["message"]
                except ValueError:
                    pass
                print("Received http code {:d}, trying again. ({:d}). Message: '{:s}'".format(response.status_code, count, msg))
        else:
            stop = True
        if(stop):
            break
    file = f"locations/locations_{rotation:d}.npy"
    if(leds is None):
        np.save(file, locs)
    else:
        #overwrite the existing file
        if(os.path.exists(file)):
            shutil.copyfile(file, file.replace(".npy", "_old.npy"))
            old_locs = np.load(file)
            old_locs[leds,:] = locs[leds,:]
            print(old_locs)
            np.save(file, old_locs)
        else:
            np.save(file, locs)
    if(show):
        cv.destroyWindow("cam-processed")
        cv.destroyWindow("cam-binary")
    reader.stop()
    reader.join()
    cam.release()

    response = requests.post(rest_url+"/all/", json={"power": False})
    if(response.status_code!=200):
        print("Failed to turn off power...")
    
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("angle", help="Rotation angle of tree", type=int)
    parser.add_argument("--ids", "-i", help="ID of LED", type=int, nargs="+")
    parser.add_argument("--no-show", help="Do not show camera windows", action='store_true')
    args = vars(parser.parse_args())

    if not os.path.exists("locations"):
        os.mkdir("locations")
    
    main(show=not args["no_show"], rotation=args["angle"], leds=args["ids"])