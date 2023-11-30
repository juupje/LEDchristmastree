from time import sleep
from animations.animations import Animation, get_locations
import numpy as np
import utils

class Fade(Animation):
    instructions = {
        "settings": ["duration", "brightness"],
        "duration": {
            "type": "float",
            "min": 1.5,
            "max": 15,
            "default": 3,
        },
        "brightness": {"type": "int", "min": 0, "max": 255, "default": 255}
    }

    def setup(self, **kwargs):
        self.num_leds = len(get_locations())
        duration = max(1.5, kwargs.get("duration", 3))
        self.step = 255/(duration*30)
        self.brightness = min(255, max(0, kwargs.get("brightness", 255)))
    
        self._is_setup = True
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        
        i = 0
        while not self._stop_event.is_set():
            i += self.step
            color = utils.wheel(int(i%255), brightness=self.brightness)
            for idx in range(self.num_leds):
                self.strip.setPixelColor(idx, color)
            self.strip.show()
            sleep(1./30)