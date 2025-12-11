from time import sleep
from animations.animations import Animation, get_locations
import numpy as np
import utils

class Disks(Animation):
    instructions = {
        "config": {
            "type": "list",
            "options": ["rings", "stripes"],
            "default": "rings"
        },
        "number": {
            "type": "int",
            "min": 4,
            "max":24,
            "default":8
        },
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255},
    }
    settings = list(instructions.keys())

    def setup(self, **kwargs):
        """
        Get all the arguments supplied by the post request and make them usable in this class
        """
        #gets the locations of the leds (locations[i] is the 3D-location of the i-th led (i=0...99); location[7,1] is the y-coordinate of the 8th led.
        locations = get_locations()
        self.N = kwargs.get("number", 8)
        self.sections = [[] for i in range(self.N)]
        if(kwargs.get("config", "rings")=="rings"):
            z = locations[:,2]
            z = (z-np.min(z))/(np.max(z)-np.min(z))*self.N #normalized to [0,N]
            z[z==self.N] = self.N-0.5
            print(np.min(z), np.max(z))
            for i in range(len(z)):
                self.sections[int(z[i])].append(i)
        else:
            angles = np.arctan2(locations[:,1], locations[:,0])+np.pi #convert locations to angles in the xy-plane
            angles = angles*self.N/(2*np.pi) #angles are normalized on [0,N]
            angles[angles==self.N] = self.N-0.5
            for i in range(len(angles)):
                self.sections[int(angles[i])].append(i)

        self._is_setup = True
        return {"success": True}

    def run(self):
        """
        Plays the animation until self.stop() is called
        """
        if not self._is_setup:
            print("Not setup!")
            return
        print(", ".join([str(len(section)) for section in self.sections]))
        for i, section in enumerate(self.sections):
            color = utils.wheel(int(i/self.N*255))
            for idx in section:
                self.strip.setPixelColor(idx, color)
        self.strip.show()
        
