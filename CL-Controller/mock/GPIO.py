import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("GPIO")
OUT = 0
IN = 1
LOW = 0
HIGH = 1

PUD_DOWN = 21
PUD_UP = 22

RISING = 31
FALLING = 32

pins = {}

def setup(pin, mode, pull_up_down=None, initial=LOW):
    logger.debug(f"Setting up pin {pin} in mode {mode}")
    if mode==IN and pull_up_down is not None:
        logger.debug(f"Setting pull up/down to {pull_up_down}")
        pins[pin] = {"mode":mode, "pud":pull_up_down, "state": HIGH if pull_up_down==PUD_UP else LOW}
    elif mode==IN:
        pins[pin] = {"mode":mode, "state": None}
    elif mode==OUT:
        pins[pin] = {"mode":mode, "state": initial}

def output(pin, state):
    if pins[pin]["mode"] != OUT:
        logger.debug(f"Pin {pin} is not set to output mode")
        return
    logger.debug(f"Setting pin {pin} to state {state}")
    pins[pin]["state"] = state

def input(pin):
    if pins[pin]["mode"] != IN:
        logger.debug(f"Pin {pin} is not set to input mode")
        return
    logger.debug(f"Reading pin {pin}")
    return pins[pin]["state"]

def add_event_detect(pin, *args, **kwargs):
    logger.debug(f"Adding event detect for pin {pin}")
    
def cleanup():
    print("Cleaning up GPIO")