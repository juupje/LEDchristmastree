import threading
import numpy as np

names = ["fade", "sweep_horiz", "sweep_vert", "rotate", "spiral", "sphere", "snow", "snake", "disco", "music", "disks"]
info = {
    "fade": {
        "name": "Fade",
        "description": "Slowly fade all leds into different colors around the color wheel."
    },
    "sweep_horiz": {
        "name": "Sweep Horizontal",
        "description": "Changes colors on a plane oriented parallel, and moving perpendicular to the Z-axis."
    },
    "sweep_vert": {
        "name": "Sweep Vertical",
        "description": "Changes colors on a plane oriented and moving perpendicular to the Z-axis."
    },
    "rotate": {
        "name": "Rotate",
        "description": "Changes colors on a plane rotating around the vertical axis."
    },
    "spiral": {
        "name": "Spiral",
        "description": "Changes colors inside a ball moving along a spiral."
    },
    "sphere": {
        "name": "Sphere",
        "description": "Changes colors on a sphere centered in the middle of the tree."
    },
    "snow": {
        "name": "Snow",
        "description": "Animates falling snowflakes over the surface of the tree."
    },
    "snake": {
        "name": "Snake",
        "description": "Multiple spiralling balls moving over the tree."
    },
    "disco": {
        "name": "Disco",
        "description": "Randomly change color!"
    },
    "music": {
        "name": "Music",
        "description": "Play some music (through spotify) and see the lights move!"
    },
    "disks": {
        "name": "Disks",
        "description": "Divide the tree into disks or stripes."
    }
}

locations = None
def get_locations():
    global locations
    if(locations is None):
        locations = np.load("animations/locations.npy")
    return locations

def get(name):
    if(name=="sweep_vert"):
        from animations import sweep
        return sweep.Sweep_Vertical
    elif(name=="sweep_horiz"):
        from animations import sweep
        return sweep.Sweep_Horizontal
    elif(name=="rotate"):
        from animations import rotate
        return rotate.Rotate
    elif(name=="spiral"):
        from animations import spiral
        return spiral.Spiral
    elif(name=="sphere"):
        from animations import sphere
        return sphere.Sphere
    elif(name=="snow"):
        from animations import snow
        return snow.Snow
    elif(name=="snake"):
        from animations import snake
        return snake.Snake
    elif(name=="disco"):
        from animations import disco
        return disco.Disco
    elif(name=="fade"):
        from animations import fade
        return fade.Fade
    elif(name=="disks"):
        from animations import disks
        return disks.Disks
    elif(name=="music"):
        from animations import music
        return music.Music
    else:
        return None

class Animation(threading.Thread):
    def __init__(self):
        super(Animation, self).__init__()
        self.daemon = True
        self._is_setup = False
        self._stop_event = threading.Event()
    
    def setup(self):
        self._is_setup = True

    #should not be overriden
    def play(self,strip):
        print("Starting animation!")
        self.strip = strip
        self.start()
    
    def stop(self):
        print("Stopping animation...")
        self._stop_event.set()

    def run(self):
        pass