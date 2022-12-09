from animations.animations import Animation, get_locations
import numpy as np
import utils
from time import sleep

height = 425
vert_step = 1.8

def spiral(phase, radius=50, base_radius=95, height=height):
    z = phase/(2*np.pi)*vert_step*radius
    x = (height-z)/height
    r = base_radius*np.sqrt(max(0,x)) #(z-height)/(-height/base_radius)
    return (r*np.cos(phase),r*np.sin(phase), z)

class Spiral(Animation):
    instructions = {
        "settings": ["color", "background", "duration", "brightness", "back_brightness", "radius", "inclination", "invert"],
        "color": {
            "type": "color",
            "default": "255,0,0",
            "presets": ["fixed", "rainbow"],
        },
        "background": {
            "type": "color",
            "default": "255,0,0",
            "presets": ["fixed", "rainbow", "chase"],
        },
        "duration": {
            "type": "float",
            "min": 1,
            "max": 15,
            "default": 3,
        },
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255},
        "back_brightness": {"type": "int", "min": 0, "max": 255, "default": 255},
        "radius": {"type": "int", "min": 10, "max": 100, "default": 50},
        "inclination": {"type": "float", "min": 0.25, "max": 3, "default": 1.75},
        "invert": {"type": "bool", "default": False}
    }

    def setup(self, **kwargs):
        global vert_step
        duration = max(kwargs.get("duration", 3),1)
        self.invert = kwargs.get("invert", False)
        vert_step = kwargs.get("inclination", 1.75)
        self.locations = get_locations()

        if("background" in kwargs and kwargs["background"]=="chase"):
            if(kwargs.get("color", "fixed") not in ["fixed", "rainbow"]):
                return {"success": False,"message": "Cannot play chase animation with static color."}
            self.background = "chase"
            self.phase = np.arctan2(self.locations[:,1], self.locations[:,0])
        else:
            self.background = utils.parseColor(kwargs.get("background", "0,0,0"), kwargs.get("back_brightness", 255))
        self.radius = kwargs.get("radius", 50)
        
        self.color = utils.parseColorMode(kwargs.get("color", "fixed"), kwargs.get("brightness", 255))
        if(self.color is None):
            print("Invalid color")
            return {"success": False, "message": "Invalid color"}

        self.max_z = np.max(self.locations[:,2])
        self.max_phi = (self.max_z/(vert_step*self.radius))*np.pi*2
        #we want 30fp, travel up in [duration] number of seconds: step_size = distance/#steps
        self.step_size = self.max_phi/(30*duration)        

        if(self.invert):
            self.init_phi = self.max_phi
            self.step_size *= -1
        else:
            self.init_phi = 0
        
        self.iteration = 0

        self._is_setup = True
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup")
            return
        
        phi = 0
        num_leds = len(self.locations)
        if(self.background == "chase"):
            while not self._stop_event.is_set():
                phi += self.step_size
                loc = spiral(phi, radius=self.radius)
                color = self.color(phi, self.max_phi, self.iteration)
                for i in range(num_leds):
                    d = np.linalg.norm(loc-self.locations[i])
                    if(d < self.radius):
                        self.strip.setPixelColor(i, color)
                self.strip.show()
                if(phi<self.max_phi):# and loc[2]<self.max_z):
                    sleep(1./30)
                else:
                    self.iteration += 1
                    phi = self.init_phi #back to the top
        else:
            while not self._stop_event.is_set():
                phi += self.step_size
                loc = spiral(phi, radius=self.radius)
                color = self.color(phi, self.max_phi, self.iteration)
                for i in range(num_leds):
                    d = np.linalg.norm(loc-self.locations[i])
                    if(d>self.radius*1.5):
                        self.strip.setPixelColor(i, self.background)
                    elif(d < self.radius*0.5):
                        self.strip.setPixelColor(i, color)
                    else:
                        self.strip.setPixelColor(i, utils.adjustBrightness(color, 255*(1.5-d/self.radius)))

                self.strip.show()
                if(phi<self.max_phi):# and loc[2]<self.max_z):
                    sleep(1./30)
                else:
                    self.iteration += 1
                    phi = self.init_phi #back to the top
