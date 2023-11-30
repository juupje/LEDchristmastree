from animations.animations import Animation, get_locations
import numpy as np
import utils
from time import sleep

max_z = 400
base_radius = 100

class Node:
    def __init__(self, location : np.ndarray, led_id : int):
        self.location = location
        self.led_id = led_id
        self.edges = []
    
    def set_connections(self, nodes, weights):
        assert(nodes.shape==weights.shape)
        self.neighbours = nodes
        self.weights = weights
    
    def unit_to(self, other : 'Node'):
        vec = other.location-self.location
        return vec/np.sum(vec)

class LEDState:
    def __init__(self, color=0, fade=0):
        self.set_color(color, fade)
    
    def set_color(self, color, fade=0):
        (self.r, self.g, self.b) = utils.colorToRGB(color)
        self.fade = fade
        self.time = 0
        self.fading = fade>0

    def update(self, dt):
        if not self.fading:
            return
        self.time += dt
        if(self.time>self.fade):
            self.fading = False
            self.r = 0
            self.g = 0
            self.b = 0
        else:
            f = 1-dt/self.fade
            self.r = int(self.r*f)
            self.g = int(self.g*f)
            self.b = int(self.b*f)

class Snowball:
    def __init__(self, idx :int, radius : float, node : Node, mass : float, speed : float, fade):
        self.idx = idx
        self.radius2 = radius*radius
        self.node = node
        self.mass = mass
        self.fade = fade
        self.speed = speed
        #find the nearest neighbor and make the velocity points that way
        nn = self.node.neighbours[np.argmax(self.node.weights)]
        self.velocity = self.node.unit_to(nn)*self.speed
        self.location = node.location

    def find_next(self):
        weights = self.node.weights
        #construct unit vectors
        

    #locs = (r, phi, theta)
    def update(self, states, locs, color):
        self.z -= self.speed
        x = (max_z-self.z)/max_z
        self.r = base_radius*np.sqrt(max(0,x)) #(z-height)/(-height/base_radius)
        #self.r = base_radius-self.z*self.a

        x,y = to_cartesian(self.r, self.phi)
        #for i in np.where(locs[0]*locs[0]+self.r*self.r-2*self.r*locs[0]*(self.sintheta*np.sin(locs[2])*np.cos(locs[1]-self.phi)+self.costheta*np.cos(locs[2]))<self.radius2)[0]:
        for i in np.where((x-locs[:,0])**2+(y-locs[:,1])**2+(self.z-locs[:,2])**2<self.radius2)[0]:
            states[i].set_color(color(self.z, max_z, self.idx), fade=self.fade)

    def __str__(self):
        return "Ball {:d}: (r, z, phi): ({:.1f}, {:d}, {:.1f})".format(self.idx, self.r, int(self.z), self.phi)

def to_cartesian(r, phi):
    return r*np.cos(phi), r*np.sin(phi)

class Crawl(Animation):
    instructions = {
        "settings": ["color", "mass", "brightness", "background", "back_brightness", "speed", "speed_std", "radius", "randomness", "amount", "fade"],
        "color": {
            "type": "color",
            "default": "255,255,255",
            "presets": ["fixed", "rainbow"],
        },
        "mass": {"type": "float", "min": 0.1, "max": 2, "default": 0.5},
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 150},
        "background": {
            "type": "color",
            "default": "0,0,0"
        },
        "back_brightness": {"type": "int", "min": 0, "max": 255, "default": 0},
        "speed": {
            "type": "int",
            "min": 1,
            "max": 25,
            "default": 6
        },
        "speed_std": {
            "type": "int",
            "min": 0,
            "max": 8,
            "default": 3
        },
        "radius": {
            "type": "int",
            "min": 5,
            "max": 60,
            "default": 33
        },
        "randomness": {
            "type": "int",
            "min": 0,
            "max": 20,
            "default": 6
        },
        "amount": {
            "type": "int",
            "min": 1,
            "max": 15,
            "default": 5
        },
        "fade": {
            "type": "float",
            "min": 0,
            "max": 1,
            "default": 0.2
        }
    }

    def setup(self, **kwargs):
        global max_z
        self.speed = max(kwargs.get("speed", 10),1)
        self.speed_std = max(kwargs.get("speed_std", 5), 0)
        self.radius = max(kwargs.get("radius", 20),5)
        self.randomness = max(kwargs.get("randomness", 6), 3)
        self.max_n_balls = max(kwargs.get("amount", 5), 1)
        self.fade = max(kwargs.get("fade", 0.2), 0)
        self.locs = get_locations()
        
        self.nodes = [Node(self.locs[i], i) for i in range(len(self.locs))]
        #build neighborhoods
        # calculate distance matrix
        X = self.locs #(N,3)
        X2 = np.sum(X*X, axis=1, keepdims=True) #(N,1)
        D = X2-2*np.matmul(X,X.T)+X2.T

        # get k-nearest-neighbors
        idx = np.argsort(D, axis=1)[:, :-10:-1]

        # add create edges and add them to this node
        for i in range(len(self.nodes)):
            nearest_neighbors = idx[i,:]
            weights = D[i, nearest_neighbors]
            weights = weights/np.sum(weights)
            self.nodes[i].set_connections(nearest_neighbors, weights)
        
        self.color = utils.parseColorMode(kwargs.get("color", "255,0,0"), brightness=kwargs.get("brightness", 255))
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}

        self.background = utils.parseColor(kwargs.get("background", "255,0,0"), brightness=kwargs.get("back_brightness", 255))
        self._is_setup = True
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        balls = []
        pi2 = np.pi*2
        theta = np.arctan(95/400)
        idx = 0
        n_leds = len(self.locs)
        states = [LEDState(self.background, fade=0) for i in range(len(self.locs))]
        while not self._stop_event.is_set():
            if(len(balls)<self.max_n_balls):
                balls.append(Snowball(idx, max(5,np.random.normal(self.radius, self.randomness)), self.top, np.random.rand()*pi2, theta, max(1,np.random.normal(self.speed, self.speed_std)), self.fade))
                idx += 1
                if(idx>1000): #prevent ridiculously large numbers
                    idx = 0
            #for i in range(n_leds):
            #    self.strip.setPixelColor(i, self.background)

            #for ball in balls:
            #    ball.update(self.strip, self.color, self.locs)
                #print(ball)
            #    if(ball.z < self.bottom):
            #        balls.remove(ball)
            for ball in balls:
                ball.update(states, self.locs, self.color)
                if(ball.z < self.bottom):
                    balls.remove(ball)
            for i, state in enumerate(states):
                state.update(1./30)
                self.strip.setPixelColor(i, utils.Color(state.r, state.g, state.b))
            self.strip.show()
            sleep(1./30)
