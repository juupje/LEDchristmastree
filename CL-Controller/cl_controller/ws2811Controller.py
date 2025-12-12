import time, random
from . import utils
import multiprocessing
if utils.is_raspberrypi():
    from rpi_ws281x import PixelStrip  # pyright: ignore[reportMissingImports]
    import RPi.GPIO as GPIO  # pyright: ignore[reportMissingModuleSource]
    GPIO.setmode(GPIO.BCM)
else:
    print("Using mock GPIO!")
    from .mock import PixelStrip
    from .mock import GPIO
    
Color = utils.Color

class ws2811Controller:
    _instance = None
    _lock = multiprocessing.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None: 
            cls._lock.acquire()
            # Another thread could have created the instance
            # before we acquired the lock. So check that the
            # instance is still nonexistent.
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance.initialize(*args, **kwargs)
            cls._lock.release()
        return cls._instance

    def initialize(self, num_leds, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel, switch_pin):
        self.switch_pin = switch_pin
        GPIO.setup(switch_pin, GPIO.OUT)
        self.on = False
        self.animation = None
        GPIO.output(switch_pin, GPIO.LOW)
        self.nonce = random.randint(0,2**15-1)
        self.has_begun = False
        self.trigger_times = {}
        self.leds = [{"id": i, "color": "255,255,255", "state": False, "brightness": 255} for i in range(num_leds)]
        self.strip = PixelStrip(num_leds, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel)
        if not utils.is_raspberrypi():
            import numpy as np
            from .mock import TreeVis
            self.vis = TreeVis(self.strip, np.load("cl_controller/animations/locations.npy"))  # type: ignore
    
    def setup_trigger(self, pin, callback, interval=2):
        #shutdown trigger
        def trigger_func(channel=None):
            state = GPIO.input(pin)
            print("Triggered", state)
            time.sleep(0.1)
            newstate = GPIO.input(pin)
            if(state == newstate == 0):
                currTime = time.time()
                if(currTime - self.trigger_times.get(pin, 0) <= interval):
                    print("Trigger accepted -> second time")
                    self.trigger_times[pin] = 0
                    callback()
                else:
                    print("Trigger accepted -> first time")
                    self.trigger_times[pin] = currTime
            else:
                print("Trigger rejected", newstate)

        self.shutdown_pin = pin
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.FALLING, callback=trigger_func, bouncetime=300)

    def stop(self):
        print("Ending ws2811Controller")
        self.stop_animation()
        GPIO.output(self.switch_pin, GPIO.LOW)
        GPIO.setup(self.switch_pin, GPIO.IN)
        GPIO.cleanup()

    def __del__(self):
        self.stop()

    def get(self, led_id):
        for led in self.leds:
            if(led["id"]==led_id):
                return led

    def turn_on(self):
        GPIO.output(self.switch_pin, GPIO.HIGH)
        self.on = True

    def turn_off(self):
        self.stop_animation()
        GPIO.output(self.switch_pin, GPIO.LOW)
        self.on = False

    def update_all(self, instructions, show=False):
        self.stop_animation()
        succ = True
        if(isinstance(instructions, (list,tuple))):
            for instruction in instructions:
                if not self.update(instruction, False):
                    succ = False
                    break
        elif(isinstance(instructions, dict)):
            #apply this instruction to every led
            for led in self.leds:
                led.update(instructions)
                if not self.update(led, False):
                    succ = False
                    break
        if(show):
            self.show()
        return succ

    def update(self, instruction, show=False):
        self.stop_animation()
        led_id = instruction["id"]
        if(instruction["state"]):
            led = self.get(led_id)
            if led is not None: led.update(instruction)
            color = utils.parse_color(instruction["color"], instruction["brightness"])
            self.strip.setPixelColor(led_id, color)
        else:
            led = self.get(led_id)
            if led is not None: led.update({"state": False, "color": "0,0,0", "brightness": 0})
            self.strip.setPixelColor(led_id, utils.Color(0,0,0))
        if(show):
            self.show()
        return True

    def uniform_color(self, color: list | tuple | str | int):
        if not self.on:
            self.turn_on()
        self.stop_animation()
        if(isinstance(color, (list, tuple))):
            if(len(color)==3):
                color = Color(*color)
            else:
                raise ValueError("Invalid color: ", color)
        elif(type(color)==str):
            color = utils.parse_color(color, 255)
        elif(type(color) is not int):
            raise ValueError("Invalid color", color)

        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
            self.leds[i].update({"color": "0,0,0"})
        self.show()

    def begin(self):
        if(self.has_begun): return False
        if not self.on:
            self.turn_on()
        self.strip.begin()

        self.uniform_color(Color(0,0,0))
        
        colors = [Color(255,0,0), Color(0,255,0), Color(0,0,255)]
        N = self.strip.numPixels()
        
        
        for i in range(3):
            self.strip.setPixelColor(i, colors[i])
            self.show()
            time.sleep(0.04)

        for i in range(3, N):
            self.strip.setPixelColor(i, colors[i%3])
            self.strip.setPixelColor(i-3, 0)
            self.show()
            time.sleep(0.04)

        for i in range(N, N+3):
            self.strip.setPixelColor(i-3, 0)
            self.show()
            time.sleep(0.04)
        
        print("Startup complete!")
        for led in self.leds:
            self.update(led)
        self.show()
        self.turn_off()
        self.has_begun = True
        return True

    def led_count(self):
        return self.strip.numPixels()

    def stop_animation(self):
        if(self.animation is not None):
            print(str(self), "Stopping running animation", self.animation)
            self.animation.stop()
            self.animation = None

    def play_animation(self, animation):
        print(str(self), "Starting new animation", animation, self.animation)
        """
        Will start playing the given animation.
        The animation can be stopped by calling stop_animation()
        or by performing any kind of update.
        """
        if(self.animation is not None):
            self.stop_animation()
        if(not self.on):
            self.turn_on()
        self.animation = animation
        self.animation.play(self.strip)

    def show(self):
        #print("Showing!")
        self.strip.show()

    def __str__(self):
        return f"ws2811Controller [{self.nonce}]"
