from animations.animations import Animation, get_locations
from time import time
from dancypi.visualization import Visualizer
import dancypi.config as config
import numpy as np
import utils

options = ["scroll", "energy", "spectrum"]
class Music(Animation):
    instructions = {
        "settings": ["bins", "mode", "scale", "direction", "brightness"],
        "mode": {
            "type": "list",
            "options": options,
            "default": "energy"
        },
        "scale": {"type": "float", "min": 0.8, "max": 1.3, "default": 1.0},
        "direction": {
            "type": "list",
            "options": ["disks", "stripes"],
            "default": "disks"
        },
        "bins": {
            "type": "int",
            "min": 6,
            "max": 40,
            "default": 10
        },
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255}
    }

    def setup(self, **kwargs):
        locations = get_locations()
        self.bins = kwargs.get("bins", 10)
        self.scale = kwargs.get("scale", 1.0)
        self.sections = [[] for i in range(self.bins)]
        print(kwargs["direction"])
        if(kwargs.get("direction", "disks")=="disks"):
            z = locations[:,2]
            z = (z-np.min(z))/(np.max(z)-np.min(z))*self.bins #normalized to [0,N]
            z[z==self.bins] = self.bins-0.5
            print(np.min(z), np.max(z))
            for i in range(len(z)):
                self.sections[int(z[i])].append(i)
        else:
            angles = np.arctan2(locations[:,1], locations[:,0])+np.pi #convert locations to angles in the xy-plane
            angles = angles*self.bins/(2*np.pi) #angles are normalized on [0,N]
            angles = np.roll(angles, angles.shape[0]//2) #rotate 180 degrees
            angles[angles==self.bins] = self.bins-0.5
            for i in range(len(angles)):
                self.sections[int(angles[i])].append(i)

        self.mode = kwargs.get("mode", "energy")
        assert(self.mode in options)
        self._is_setup = True
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        self.last_update = time()
        def callback(colors):
            for i, section in enumerate(self.sections):
                for idx in section:
                    self.strip.setPixelColor(idx, int(colors[i]))
            self.strip.show()
            self.last_update = time()
        self.vis = Visualizer(self.mode, self.scale, self.bins)

        #start microphone stream
        self.vis.start(callback)
    
    def stop(self):
        Animation.stop(self)
        self.vis.stop()

    def __del__(self):
        if(hasattr(self, "vis")):
            self.vis.stop()