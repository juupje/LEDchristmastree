# -*- coding: utf-8 -*-
import werkzeug
from flask import Flask, render_template, request
from flask_restx import Api, Resource, fields
from ws2811Controller import Controller
from animations import animations as anim
import subprocess
import os
import io
import webcontroller
import importlib

# LED strip configuration:
LED_COUNT = 100        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

controller = Controller(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

api = Api(app, version="1.0", title="CL-Controller", description="A RESTful API to control a christmas tree's lighting",
          doc="/docs")

ns_leds = api.namespace('leds', description="LED related operations")
ns_all = api.namespace('all', description="Global LED operations")
ns_anim = api.namespace('anim', description="Animation related operations")
ns_rpi = api.namespace('rpi', description="Raspberry Pi related operations")

leds_model = api.model('leds', {
    'id': fields.Integer(readonly=True, description="The LED's number"),
    'color': fields.String(required=True, description="Sets the LED's color"),
    'state': fields.Boolean(required=True, description="Turns the LED on/off"),
    'brightness': fields.Integer(required=True, description="Sets the LED's brightness")
})

all_model = api.model('all', {
    'power': fields.String(required=False, description="Turn power to the pixels on/off"),
    'color': fields.String(required=False, description="Sets the LEDs' color"),
    'state': fields.Boolean(required=False, description="Turns the LEDs' on/off"),
    'brightness': fields.Integer(required=False, description="Sets the LEDs' brightness")
})

class LEDUtil(object):
    def __init__(self):
        self.leds = [{"id": i, "color": "255,255,255", "state": False, "brightness": 255} for i in range(controller.led_count())]
    
    def get(self, led_id):
        for led in self.leds:
            if(led["id"]==led_id):
                return led
    
    def update_all(self, data):
        print("Received update for all", data)
        if("power" in data):
            if(data["power"]):
                controller.turn_on()
                controller.update_all(self.leds, show=True)
            else:
                controller.turn_off()
        
        for led in self.leds:
            led.update(data)

        if(controller.update_all(self.leds, show=True)):
            return {"success": True, **data}
        return {"success": False, "message": ""}

    def update(self, data, led_id=None):
        print("Received update" + (f" on id {led_id:d}" if led_id is not None else ""), data)
        if(led_id is None):
            if("id" not in data):
                return {"success": False, "message": "No ID given"}
            led_id = int(data["id"])
        if("id" in data):
            del data["id"]
        led = self.get(led_id)
        if(led is None):
            return {"success": False, "message": f"Could not find LED with ID {led_id:d}"}
        backup = led.copy()
        led.update(data)
        if(controller.update(led, show=True)):
            return {"success": True, **led}
        else:
            led = backup
            return {"success": False, "message": ""}
            
@app.route("/home", strict_slashes=False)
def webpage():
    importlib.reload(webcontroller)
    return webcontroller.render_webpage(animation=request.args.get("animation", default=None, type=str))

@ns_all.route("/")
class ApplyAll(Resource):
    @ns_all.marshal_list_with(leds_model)
    def get(self):
        print("Got get request! /all/")
        return led_util.leds
    
    @ns_all.expect(all_model)
    def post(self):
        return led_util.update_all(api.payload)

@ns_leds.route("/")
class LedList(Resource):
    @ns_leds.marshal_list_with(leds_model)
    def get(self):
        return led_util.leds
    
    @ns_leds.expect(leds_model)
    def patch(self):
        return led_util.update(api.payload)
    
@ns_leds.route("/<int:led_id>")
@ns_leds.response(404, 'LED not found')
@ns_leds.param('led_id', 'The LED identifier')
class LED(Resource):
    
    @ns_leds.marshal_with(leds_model)
    def get(self, led_id):
        return led_util.get(led_id)
        
    @ns_leds.expect(leds_model)
    def patch(self, led_id):
        """
        Partial update of a given led
        """
        return led_util.update(api.payload, led_id)

@ns_anim.route("/")
class AnimList(Resource):
    def get(self):
        return {"animations": anim.names, "information": anim.info}

    def post(self):
        data = api.payload
        #print(data)
        if("name" in data):
            animation = anim.get(data["name"])
            if(animation is not None):
                animation = animation()
                result = animation.setup(**data)
                if(result["success"]):
                    controller.play_animation(animation)
                else:
                    del animation
                return result
            else:
                return {"success": False, "message": "Could not find animation '" + data["name"] +"'."}
        elif("stop" in data):
            controller.stop_animation()
            return {"success": True}
        else:
            return {"success": False, "message": "No animation name specified."}

@ns_anim.route("/<string:name>")
@ns_anim.response(404, "animation not found")
@ns_anim.param("name", "The name of the animation")
class AnimInformation(Resource):
    def get(self, name):
        print(f"Retrieving info for '{name:s}'")
        animation = anim.get(name)
        if(animation is not None):
            return {"success": True, **animation.instructions}
        return {"success": False, "message": "Unknown animation name"}

@ns_rpi.route("/")
class RPIInformation(Resource):
    def post(self):
        data = api.payload
        if("option" in data):
            cwd = os.getcwd()
            option = data["option"]
            if(option in ["kill", "reboot", "shutdown"]):
                cmd = ["bash", f"{cwd:s}/shutdown", option]
                with open("output.txt", "w+") as file:
                    subprocess.run(cmd, stdout=file)         
                    print("Executed command '" + " ".join(cmd));#
                    file.seek(io.SEEK_SET)
                    last_line = ""
                    output = ""
                    for line in file:
                        output += line
                        last_line = line.strip()
                    print("Got response '" + last_line +"'")
                    if(last_line == option):
                        return {"success": True}
                    else:
                        return {"success": False, "message": output}
        return {"success": False, "message": "Unknown option"}

led_util = LEDUtil()
controller.begin(led_util.leds)

if __name__=="__main__":
    app.run("0.0.0.0")