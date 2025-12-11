from time import sleep
from .animations import Animation, get_locations
import numpy as np
from hashlib import sha1
import utils, os
from random import randint

def calculate_geodesic_dists(X, kth:int):
    cache_file = f"animations/geodesic_dists-{kth}.npz"
    if os.path.exists(cache_file):
        data = np.load(cache_file)
        if data['h']==sha1(X).digest():
            print("Using cache file!")
            return data['G']
        else:
            print("Geodesic cache file is outdated")
    print("Calculating geodesic distances!")
    #the cache file doesn't exist or was calculated using a different X
    X2 = np.sum(X*X, axis=1, keepdims=True) #(N,1)
    D = X2-2*X@X.T+X2.T
    del X2
    #construct adjacency matrix
    epsilon = np.mean(np.partition(D,kth,axis=1)[:,kth]) #average distance to k-th nearest neighbor 
    E = D<epsilon #binary matrix connecting nodes with distance < epsilon
    
    #Now, find the shortest path from every LED to every LED through using the edges in E
    G = np.full_like(D, np.inf)
    P = np.full(D.shape,-1,dtype=np.int16)
    n = G.shape[0]
    for k in range(n):
        #Run Dijkstra's algorithm for k
        G[k,k] = 0
        P[k,k] = 1
        T = list(range(n))
        while len(T)>0:
            i = T[np.argmin([G[k,i] for i in T])]
            T.remove(i)
            for j in [j for j in T if E[i,j]==1]:
                if G[k,i]+D[i,j] < G[k,j]:
                    G[k,j] = G[k,i] + D[i,j]
                    P[k,j] = i
    assert np.allclose(G.T,G)
    h = sha1(X).digest()
    np.savez(cache_file, G=G, P=P, h=h)
    return G

class Geodesic(Animation):
    instructions = {
        "color": {
            "type": "color",
            "default": "fixed",
            "presets": ["fixed", "rainbow"],
        },
        "duration": {
            "type": "float",
            "min": 1,
            "max": 15,
            "default": 3,
        },
        "k-parameter": {"type": "int", "min": 6, "max": 20, "default": 8},
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255}
    }
    settings = list(instructions.keys())

    def setup(self, **kwargs):
        """
        Get all the arguments supplied by the post request and make them usable in this class
        """
        self.duration = max(1,kwargs.get("duration", 3)) #duration of one loop in seconds
        self.invert = kwargs.get("invert", False) #play the animation back-to-front if true
        self.color = utils.parse_color_mode(kwargs.get("color", "255,0,0"), brightness=kwargs.get("brightness", 255), is_odd_black_constant=True) #get the color mode as a lambda, call with self.color(location, max_location, iteration)
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}

        #get the geodesic distances
        try:
            self.D = calculate_geodesic_dists(get_locations(), kth=kwargs.get("k-parameter", 8))
        except Exception as e:
            print(e)
            return {"success": False, "message": str(e)}
        
        self.iteration = 0
        self._is_setup = True
        return {"success": True}

    def run(self):
        """
        Plays the animation until self.stop() is called
        """
        if not self._is_setup:
            print("Not setup!")
            return
        
        num_leds = self.D.shape[0]
        def initialize():
            start_loc = randint(0,num_leds-1)
            dists = self.D[start_loc]
            order = np.argsort(dists)
            max_dist = np.max(dists[dists<np.inf])
            step_size = max_dist/(30*self.duration)
            current_dist = 0
            return current_dist, dists[order], max_dist, step_size, order
        
        current_dist, dists, max_dist, step_size, order = initialize()
        idx = 0
        while not self._stop_event.is_set():
            current_dist += step_size
            changed = False #set to true if at least one led changed.
            while(idx<num_leds and dists[idx] <= current_dist):
                #while the next led in the order is less than the current angle, activate that led
                self.strip.setPixelColor(int(order[idx]), self.color(current_dist, max_dist, self.iteration)) # type: ignore
                changed = True
                idx += 1
            if(changed):
                self.strip.show()
                
            if(current_dist < max_dist):
                #continue with the next step
                sleep(1./30)
            else:
                #We reached the end of the animation, start the next iteration
                sleep(0.3)
                self.iteration += 1
                current_dist, dists, max_dist, step_size, order = initialize()
                idx = 0 #reset back to the first led
                