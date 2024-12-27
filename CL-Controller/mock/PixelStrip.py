import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("PixelStrip")

class PixelStrip:
    def __init__(self, *args, **kwargs):
        logger.debug(f"Initializing PixelStrip with args {args} and kwargs {kwargs}")

    def setPixelColor(self, pixel, color):
        logger.debug(f"Setting pixel {pixel} to color {color}")

    def numPixels(self):
        return 100
    
    def show(self):
        logger.debug("Showing pixels")

    def begin(self):
        logger.debug("Beginning PixelStrip")