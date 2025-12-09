from animations.animations import Animation, get_locations
import numpy as np
import utils
from time import sleep

class Sweep(Animation):
    def _setup(self, locations: np.ndarray, **kwargs):
        self.duration = max(kwargs.get("duration", 3),1)
        invert = kwargs.get("invert", False)
        self.order = np.argsort(locations).astype(int) #sorts small->big (or rising z)
        self.max_loc, min_loc = locations[self.order[-1]], locations[self.order[0]]

        #we want 30fp, travel up in [duration] number of seconds: step_size = distance/#steps
        self.step_size = (self.max_loc-min_loc)/(30*self.duration)
        
        self.color = utils.parse_color_mode(kwargs.get("color", "255,0,0"), brightness=kwargs.get("brightness", 255), is_odd_black_constant=True)
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}

        if(invert):
            self.init_loc = min_loc
            self.step_size *= -1
            self.check = lambda z1, z2: z1 <= z2
        else:
            self.order = self.order[::-1] #sorts big->small (falling z)
            self.init_loc = self.max_loc
            self.check = lambda z1, z2: z1 >= z2
        
        self.iteration = 0

        self.locs = locations[self.order]
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        idx = 0
        loc = self.init_loc
        changed = False
        num_leds = len(self.locs)
        while not self._stop_event.is_set():
            loc -= self.step_size
            changed = False
            while(idx<num_leds and self.check(self.locs[idx],loc)): #todo take invert into account
                self.strip.setPixelColor(int(self.order[idx]), self.color(loc, self.max_loc, self.iteration))  # type: ignore
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

class Sweep_Vertical(Sweep):
    instructions = {
        "settings": ["color", "duration", "brightness", "invert"],
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
    def setup(self, **kwargs):
        super()._setup(get_locations()[:, 2], **kwargs)
        self._is_setup = True
        return {"success": True}

class Sweep_Horizontal(Sweep):
    instructions = {
        "settings": ["color", "duration", "brightness", "invert", "angle"],
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
        "angle": {
            "type": "int",
            "presets": ["x", "y"],
            "min": 0,
            "max": 360,
            "default": 0
        }
    }
    def setup(self, **kwargs):
        angle = kwargs.get("angle", "x")
        if(angle == "x"):
            angle = 0
        elif(angle == "y"):
            angle = 90
        else:
            try:
                angle = int(angle)%360
            except ValueError:
                return {"success": False, "message": f"Unknown angle {angle}"}
        locs = get_locations()[:, :2]
        #project locs onto a vector in the xy plane with a given angle
        # to the x-axis 
        angle *= np.pi/180
        mat = np.array([[np.cos(angle)], [np.sin(angle)]])
        locs = locs@mat
        locs = locs.reshape(locs.shape[0])
        super()._setup(locs, **kwargs)
        self._is_setup = True
        return {"success": True}

class SweepX(Sweep):
    def setup(self, **kwargs):
        super()._setup(get_locations()[:, 0], **kwargs)
        self._is_setup = True
        return {"success": True}