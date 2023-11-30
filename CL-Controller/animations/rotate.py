from time import sleep
from animations.animations import Animation, get_locations
import numpy as np
import utils

class Rotate(Animation):
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
        """
        Get all the arguments supplied by the post request and make them usable in this class
        """
        duration = max(1,kwargs.get("duration", 3)) #duration of one loop in seconds

        #gets the locations of the leds (locations[i] is the 3D-location of the i-th led (i=0...99); location[7,1] is the y-coordinate of the 8th led.
        locations = get_locations() 
        invert = kwargs.get("invert", False) #play the animation back-to-front if true
        self.angles = np.arctan2(locations[:,1], locations[:,0])+np.pi #convert locations to angles in the xy-plane
        self.order = np.argsort(self.angles).astype(int) #get the order of the leds, from smallest angle to largest: 0->2pi

        #we want 30fp, travel up in [duration] number of seconds: step_size = distance/#steps
        self.step_size = 2*np.pi/(30*duration)
        
        self.color = utils.parseColorMode(kwargs.get("color", "255,0,0"), brightness=kwargs.get("brightness", 255), is_odd_black_constant=True) #get the color mode as a lambda, call with self.color(location, max_location, iteration)
        if(self.color is None):
            print("Invalid color!")
            return {"success": False, "message": "Invalid color"}

        if(invert):
            #start at the end
            self.init_loc = 2*np.pi
            self.step_size *= -1
            self.check = lambda z1, z2: z1 >= z2
            self.order = self.order[::-1] #sorts 2pi->0
        else:
            #start at the beginning
            self.init_loc = 0
            self.check = lambda z1, z2: z1 <= z2
        
        self.iteration = 0

        self.angles = self.angles[self.order] #sort the angles according to their order
        self._is_setup = True
        return {"success": True}

    def run(self):
        """
        Plays the animation until self.stop() is called
        """
        if not self._is_setup:
            print("Not setup!")
            return
        pi2 = np.pi*2 #just a helpful constant
        
        idx = 0 #current LED (goes to 99 max)
        loc = self.init_loc #current angle
        num_leds = len(self.angles)
        while not self._stop_event.is_set():
            loc += self.step_size
            changed = False #set to true if at least one led changed.
            while(idx<num_leds and self.check(self.angles[idx],loc)):
                #while the next led in the order is less than the current angle, activate that led
                self.strip.setPixelColor(int(self.order[idx]), self.color(loc, pi2, self.iteration))
                changed = True
                idx += 1
            if(changed):
                self.strip.show()
                
            if(0 <= loc < pi2):
                #continue with the next step
                sleep(1./30)
            else:
                #We reached the end of the animation, start the next iteration
                self.iteration += 1
                idx = 0 #reset back to the first led
                loc = self.init_loc #back to the start