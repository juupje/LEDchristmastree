from .animations import Animation, get_locations
import numpy as np
import cl_controller.utils as utils
from time import sleep

height = 425
vert_step = 1.8

def spiral(phase, radius=50, base_radius=95, height=height):
    z = phase/(2*np.pi)*vert_step*radius
    x = (height-z)/height
    r = base_radius*np.sqrt(max(0,x)) #(z-height)/(-height/base_radius)
    return (r*np.cos(phase),r*np.sin(phase), z)

class Spiral:
    def __init__(self, idx, phi, color, radius):
        self.phi = phi
        self.idx = idx
        self.color = color
        self.radius = radius

    def update(self, strip, step, max_phi, locs):
        self.phi += step
        loc = spiral(self.phi, radius=self.radius)
        color = self.color(self.phi, max_phi, self.idx)
        for i in np.where(np.linalg.norm(loc-locs, axis=1)<self.radius)[0]:
            strip.setPixelColor(int(i), color)

class Snake(Animation):
    instructions = {
        "color": {
            "type": "color",
            "default": "255,0,0",
            "presets": ["fixed", "rainbow"],
        },
        "duration": {
            "type": "float",
            "min": 1,
            "max": 15,
            "default": 3,
        },
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255},
        "radius": {"type": "int", "min": 10, "max": 100, "default": 50},
        "inclination": {"type": "float", "min": 0.25, "max": 3, "default": 1.75},
        "amount": {"type": "int", "min": 1, "max": 10, "default": 4}
    }
    settings = list(instructions.keys())

    def setup(self, **kwargs):
        global vert_step
        duration = max(kwargs.get("duration", 3),1)
        vert_step = kwargs.get("inclination", 1.75)
        self.amount = kwargs.get("amount", 4)
        self.locations = get_locations()

        if("background" in kwargs and kwargs["background"]=="chase"):
            if(kwargs.get("color", "fixed") not in ["fixed", "rainbow"]):
                return {"success": False,"message": "Cannot play chase animation with static color."}
            self.background = "chase"
            self.phase = np.arctan2(self.locations[:,1], self.locations[:,0])
        else:
            self.background = utils.parse_color(kwargs.get("background", "0,0,0"), kwargs.get("back_brightness", 255))
        self.radius = kwargs.get("radius", 50)
        
        self.color = utils.parse_color_mode("fixed", kwargs.get("brightness", 255))

        self.max_z = np.max(self.locations[:,2])
        self.max_phi = (self.max_z/(vert_step*self.radius))*np.pi*2
        #we want 30fp, travel up in [duration] number of seconds: step_size = distance/#steps
        self.step_size = self.max_phi/(30*duration)        

        self.start_new_point = self.max_phi/self.amount
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
        
        snakes = [Spiral(self.iteration, self.init_phi, self.color, self.radius)]

        while not self._stop_event.is_set():
            if(snakes[-1].phi>self.start_new_point and len(snakes)<self.amount):
                self.iteration += 1
                snakes.append(Spiral(self.iteration, self.init_phi, self.color, self.radius))
                if(self.iteration>1000):
                    self.iteration = 0
            for snake in snakes:
                snake.update(self.strip, self.step_size, self.max_phi, self.locations)
                if(snake.phi > self.max_phi):
                    snakes.remove(snake)

            self.strip.show()
            sleep(1./30)