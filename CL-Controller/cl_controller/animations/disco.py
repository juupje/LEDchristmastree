from time import sleep
from .animations import Animation, get_locations
import numpy as np
import utils

class Disco(Animation):
    instructions = {
        "color": {
            "type": "list",
            "options": ["fixed", "random"],
            "default": "random"
        },
        "duration": {
            "type": "float",
            "min": 0.5,
            "max": 15,
            "default": 5,
        },
        "min_brightness": {"type": "int", "min": 0, "max": 255, "default": 0},
        "max_brightness": {"type": "int", "min": 0, "max": 255, "default": 255}
    }
    settings = list(instructions.keys())

    def setup(self, **kwargs):
        self.num_leds = len(get_locations())
        interval = 1./30 #30 fps
        mean = interval/(max(0.5,kwargs.get("duration", 5))/self.num_leds)
        self.dist = lambda: np.random.poisson(lam=mean)
        self.brightness_min = max(0, kwargs.get("min_brightness", 0))
        self.brightness_max = min(255, kwargs.get("max_brightness", 255))
        self.fixed = kwargs.get("color", "random")=="fixed"
        print(kwargs.get("color", "random"))
        print("Fixed", self.fixed)

        if(self.brightness_max<self.brightness_min):
            return {"success": False, "message": "Max brightness smaller than min brightness"}

        self._is_setup = True
        return {"success": True}

    def run(self):
        if not self._is_setup:
            print("Not setup!")
            return
        
        if(self.fixed):
            i = 0
            idx = 0
            order = np.random.choice(self.num_leds, size=self.num_leds, replace=False)
            color = utils.wheel(((i+1)*40)%255, self.brightness_max)
            while not self._stop_event.is_set():
                n = self.dist()
                for _ in range(n):
                    idx += 1
                    if(idx>self.num_leds-1): break
                    self.strip.setPixelColor(int(order[idx]), color)
                else:
                    self.strip.show()
                    sleep(1./30)
                    continue #the while loop
                
                #we reached the end of the order
                i += 1
                idx = 0
                order = np.random.choice(self.num_leds, size=self.num_leds, replace=False)
                color = utils.wheel(((i+1)*40)%255, self.brightness_max)
                sleep(1./30)

        else:
            while not self._stop_event.is_set():
                n = self.dist()
                idx = np.random.randint(low=0, high=self.num_leds, size=(n))
                color = utils.Color(*utils.hsv_to_rgb(np.random.randint(0,255), 1, np.random.randint(self.brightness_min,self.brightness_max)/255))
                for i in idx:
                    self.strip.setPixelColor(int(i), color)
                self.strip.show()
                sleep(1./30)