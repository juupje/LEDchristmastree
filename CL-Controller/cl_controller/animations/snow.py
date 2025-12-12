from .animations import Animation, get_locations
import numpy as np
import cl_controller.utils as utils
from time import sleep

max_z = 400
base_radius = 100

class LEDState:
    def __init__(self, color=0, fade=0):
        self.set_color(color, fade)
    
    def set_color(self, color, fade=0):
        (self.r, self.g, self.b) = utils.color_to_rgb(color)
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
    def __init__(self, idx, radius, z, phi, theta, speed, fade):
        self.idx = idx
        self.radius2 = radius*radius
        self.phi = phi
        self.z = z
        self.speed = speed
        self.sintheta = np.sin(theta)
        self.costheta = np.cos(theta)
        self.a = self.sintheta/self.costheta
        self.r = 0
        self.fade = fade

    #locs = (r, phi, theta)
    def update(self, states, locs, color):
        self.z -= self.speed
        x = (max_z-self.z)/max_z
        self.r = base_radius*np.sqrt(max(0,x)) #(z-height)/(-height/base_radius)
        #self.r = base_radius-self.z*self.a

        x,y = to_cartesian(self.r, self.phi)
        #for i in np.where(locs[0]*locs[0]+self.r*self.r-2*self.r*locs[0]*(self.sintheta*np.sin(locs[2])*np.cos(locs[1]-self.phi)+self.costheta*np.cos(locs[2]))<self.radius2)[0]:
        for i in np.where((x-locs[:,0])**2+(y-locs[:,1])**2+(self.z-locs[:,2])**2<self.radius2)[0]:
            #print(i, color(self.z, max_z, self.idx), type(color(self.z, max_z, self.idx)))
            #strip.setPixelColor(int(i), color(self.z, max_z, self.idx))
            states[i].set_color(color(self.z, max_z, self.idx), fade=self.fade)

    def __str__(self):
        return "Ball {:d}: (r, z, phi): ({:.1f}, {:d}, {:.1f})".format(self.idx, self.r, int(self.z), self.phi)

def to_cartesian(r, phi):
    return r*np.cos(phi), r*np.sin(phi)

class Snow(Animation):
    instructions = {
        "color": {
            "type": "color",
            "default": "255,255,255",
            "presets": ["fixed", "rainbow"],
        },
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
    settings = list(instructions.keys())

    def setup(self, **kwargs):
        global max_z
        self.speed = max(kwargs.get("speed", 10),1)
        self.speed_std = max(kwargs.get("speed_std", 5), 0)
        self.radius = max(kwargs.get("radius", 20),5)
        self.randomness = max(kwargs.get("randomness", 6), 3)
        self.max_n_balls = max(kwargs.get("amount", 5), 1)
        self.fade = max(kwargs.get("fade", 0.2), 0)
        self.locs = get_locations()
        z = self.locs[:,2]
        phi = np.arctan2(self.locs[:,1], self.locs[:,0])+np.pi #convert locations to angles in the xy-plane
        r = np.sqrt(self.locs[:,1]**2+self.locs[:,0]**2)

        max_z = self.top = np.max(z)+self.radius+self.randomness
        self.bottom = np.min(z)-2*self.radius
        #we want 30fp, travel up in [duration] number of seconds: step_size = distance/#steps
        
        self.color = utils.parse_color_mode(kwargs.get("color", "255,0,0"), brightness=kwargs.get("brightness", 255))
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}

        self.background = utils.parse_color(kwargs.get("background", "255,0,0"), brightness=kwargs.get("back_brightness", 255))

        #self.locs = (z, phi, r)
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
