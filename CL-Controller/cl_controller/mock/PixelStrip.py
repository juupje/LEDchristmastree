import logging
from typing import List, Callable
logger = logging.getLogger("PixelStrip")

class PixelStrip:
    def __init__(self, n_pixels:int = 100, *args, **kwargs):
        logger.debug(f"Initializing PixelStrip with args {args} and kwargs {kwargs}")
        self.leds: List[int] = [0 for _ in range(n_pixels)]
        self.begun = False
        self.show_callbacks: List[Callable[[List[int]], None]] = []

    def add_show_callback(self, callback: Callable[[List[int]], None]):
        logger.debug("Setting show callback")
        self.show_callbacks.append(callback)

    def remove_show_callback(self, callback: Callable[[List[int]], None]):
        logger.debug("Removing show callback")
        self.show_callbacks.remove(callback)

    def setPixelColor(self, pixel: int, color: int):
        logger.debug(f"Setting pixel {pixel} to color {color}")
        self.leds[pixel] = color

    def getPixelColor(self, pixel: int) -> int:
        logger.debug(f"Getting color of pixel {pixel}")
        return self.leds[pixel]

    def numPixels(self):
        return 100
    
    def show(self):
        if self.begun:
            logger.debug("Showing pixels")
            for callback in self.show_callbacks:
                callback(self.leds)
        else:
            raise Exception("PixelStrip not begun. Call begin() before show().")

    def begin(self):
        self.begun = True
        logger.debug("Beginning PixelStrip")