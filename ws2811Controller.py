#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
from rpi_ws281x import PixelStrip
import utils
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

Color = utils.Color

SWITCH_PIN = 25 #GPIO in BCM channel

# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChase(strip, color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)


def rainbow(strip, wait_ms=20, iterations=1):
    """Draw rainbow that fades across all pixels at once."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, utils.wheel((i + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def rainbowCycle(strip, wait_ms=20, iterations=5):
    """Draw rainbow that uniformly distributes itself across all pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, utils.wheel(
                (int(i * 256 / strip.numPixels()) + j) & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChaseRainbow(strip, wait_ms=50):
    """Rainbow movie theater light style chaser animation."""
    for j in range(256):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, utils.wheel((i + j) % 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                strip.setPixelColor(i + q, 0)

class Controller:
    def __init__(self, num_leds, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel):
        print("INIT")
        GPIO.setup(SWITCH_PIN, GPIO.OUT)
        self.on = False
        self.animation = None
        GPIO.output(SWITCH_PIN, GPIO.LOW)
        #self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        self.strip = PixelStrip(num_leds, led_pin, led_freq, led_dma, led_invert, led_brightness, led_channel)       

    def __del__(self):
        self.stop_animation()
        GPIO.output(SWITCH_PIN, GPIO.LOW)
        GPIO.setup(SWITCH_PIN, GPIO.IN)
        GPIO.cleanup()

    def turn_on(self):
        GPIO.output(SWITCH_PIN, GPIO.HIGH)
        self.on = True

    def turn_off(self):
        self.stop_animation()
        GPIO.output(SWITCH_PIN, GPIO.LOW)
        self.on = False

    def update_all(self, instructions, show=False):
        self.stop_animation()
        print("Update all: ")
        succ = True
        for instruction in instructions:
            if not self.update(instruction, False):
                succ = False
                break
        if(show):
            self.show()
        return succ

    def update(self, instruction, show=False):
        self.stop_animation()
        led_id = instruction["id"]
        print(f"UPDATE led {led_id:d}: ", instruction)
        if(instruction["state"]):
            color = utils.parseColor(instruction["color"], instruction["brightness"])
            print("Set color to: ", color)
            self.strip.setPixelColor(led_id, color)
        else:
            self.strip.setPixelColor(led_id, utils.Color(0,0,0))
        if(show):
            self.show()
        return True

    def uniform_color(self, color):
        self.stop_animation()
        if(isinstance(color, (list, type))):
            if(len(color)==3):
                color = Color(*color)
            else:
                raise ValueError("Invalid color: ", color)
        elif(type(color)==str):
            color = utils.parseColor(color, 255)
        elif(type(color) is not int):
            raise ValueError("Invalid color", color)

        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
        self.show()

    def begin(self, data):
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

        for led in data:
            self.update(led)
        self.show()

    def led_count(self):
        return self.strip.numPixels()

    def stop_animation(self):
        if(self.animation is not None):
            self.animation.stop()
            self.animation = None

    def play_animation(self, animation):
        """
        Will start playing the given animation.
        The animation can be stopped by calling stop_animation()
        or by performing any kind of update.
        """
        if(self.animation is not None):
            self.stop_animation()
        self.animation = animation
        self.animation.play(self.strip)

    def show(self):
        print("Showing!")
        self.strip.show()