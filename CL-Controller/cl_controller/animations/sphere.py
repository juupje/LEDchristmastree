from time import sleep
from .animations import Animation, get_locations
import numpy as np
import cl_controller.utils as utils

class Sphere(Animation):
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
        "invert": {"type": "bool", "default": False},
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255},
    }
    settings = list(instructions.keys())

    def setup(self, **kwargs):
        duration = max(1,kwargs.get("duration", 3))
        locations = get_locations().copy()
        invert = kwargs.get("invert", False)
        
        #center the z-coordinates
        z_mean = (np.max(locations[:,2])+np.min(locations[:,2]))/2.
        locations[:,2] -= z_mean

        self.r = np.linalg.norm(locations, axis=1)
        self.order = np.argsort(self.r).astype(int) #sorts small to big

        r_min = self.r[self.order[0]]
        r_max = self.r[self.order[-1]]

        #we want 30fp, travel up in [duration] number of seconds: step_size = distance/#steps
        self.step_size = (r_max-r_min)/(30*duration)
        #print("Stepsize", self.step_size)
        
        self.color = utils.parse_color_mode(kwargs.get("color", "255,0,0"), brightness=kwargs.get("brightness", 255), is_odd_black_constant=True)
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}

        if(invert):
            self.init_loc = r_max
            self.step_size *= -1
            self.check = lambda z1, z2: z1 >= z2
            self.order = self.order[::-1] #sorts 2pi->0
        else:
            self.init_loc = r_min
            self.check = lambda z1, z2: z1 <= z2
        
        self.max_r = r_max
        self.iteration = 0
        #print(f"Min: {r_min:.1f}, Max: {r_max:.1f}")

        self.r = self.r[self.order]
        self._is_setup = True
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        
        idx = 0
        loc = self.init_loc
        changed = False
        num_leds = len(self.r)
        while not self._stop_event.is_set():
            loc += self.step_size
            changed = False
            while(idx<num_leds and self.check(self.r[idx],loc)):
                self.strip.setPixelColor(int(self.order[idx]), self.color(loc, self.max_r, self.iteration))  # type: ignore
                changed = True
                idx += 1
            if(changed):
                self.strip.show()
                
            if(idx<num_leds):
                #continue with the next step
                sleep(1./30)
            else:
                self.iteration += 1
                idx = 0
                loc = self.init_loc #back to the top
