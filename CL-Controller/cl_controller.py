# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect
from flask_restx import Api, Resource, fields
from ws2811Controller import ws2811Controller
from animations import animations as anim
import subprocess
import os
import io
import webcontroller
import importlib
import multiprocessing
import threading
import requests
import time

# LED strip configuration:
LED_COUNT = 100        # Number of LED pixels.
LED_PIN = 18          # GPIO pin connected to the pixels (18 uses PWM!).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

SHUTDOWN_PIN = 23

class LEDUtil():
    def __init__(self, *args, **kwargs):
        self.controller = ws2811Controller(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        print(str(self.controller))
        self.controller.begin()

    def get_controller(self):
        return self.controller

    def get(self, led_id):
        return self.controller.get(led_id)
    
    def update_all(self, data):
        print("Received update for all", data)
        print("Using controller", str(self.controller), multiprocessing.current_process())
        if("power" in data):
            if(data["power"]):
                self.controller.turn_on()
            else:
                self.controller.turn_off()
            del data["power"]

        if(self.controller.update_all(data, show=True)):
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
        if(self.controller.update(led, show=True)):
            return {"success": True, **led}
        else:
            led.update(backup)
            return {"success": False, "message": ""}

def create_app(**kwargs):
    print("Starting")
    animdata = anim.AnimData(**kwargs)
    led_util = LEDUtil()
    app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

    @app.route('/')
    def home():
        return redirect("home", code=302)

    api = Api(app, version="1.0", title="CL-Controller", description="A RESTful API to control a christmas tree's lighting",
            doc="/docs/")

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

    @app.route("/home")
    def webpage():
        importlib.reload(webcontroller)
        return webcontroller.render_webpage(animation=request.args.get("animation", default=None, type=str), animdata=animdata)

    try:
        import video_stream
        @app.route("/video")
        def video_webpage():
            return video_stream.render_webpage()

        @app.route("/video_feed", strict_slashes=False)
        def video_feed():
            importlib.reload(video_stream)
            """Video streaming route. Put this in the src attribute of an img tag."""
            return video_stream.render_video()
    except Exception as e:
        print(e)

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
            return {"animations": animdata.names, "information": animdata.info}

        def post(self):
            data = api.payload
            #print(data)
            if("name" in data):
                animation = animdata.get(data["name"])
                if(animation is not None):
                    animation = animation()
                    result = animation.setup(**data)
                    if(result["success"]):
                        led_util.controller.play_animation(animation)
                    else:
                        del animation
                    return result
                else:
                    return {"success": False, "message": "Could not find animation '" + data["name"] +"'."}
            elif("stop" in data):
                led_util.controller.stop_animation()
                return {"success": True}
            else:
                return {"success": False, "message": "No animation name specified."}

    @ns_anim.route("/<string:name>")
    @ns_anim.response(404, "animation not found")
    @ns_anim.param("name", "The name of the animation")
    class AnimInformation(Resource):
        def get(self, name):
            print(f"Retrieving info for '{name:s}'")
            animation = animdata.get(name)
            if(animation is not None):
                return {"success": True, **animation.instructions}
            return {"success": False, "message": "Unknown animation name"}

    @ns_rpi.route("/")
    class RPIInformation(Resource):
        def post(self):
            data = api.payload
            if("option" in data):
                option = data["option"]
                if(option in ["kill", "reboot", "shutdown"]):
                    response, output = shutdown(option)
                    print("Got response '" + response +"'")
                    if(response == option):
                        return {"success": True}
                    else:
                        return {"success": False, "message": output}
            return {"success": False, "message": "Unknown option"}
    try:
        from preset_handler import preset_api as ns_preset, close_database
        api.add_namespace(ns_preset)
        app.teardown_appcontext(close_database)
    except Exception as e:
        print("Error when loading preset_handler", e)

    from bluetooth_handler import bluetooth_api
    api.add_namespace(bluetooth_api, path="/bluetooth")

    #register shutdown stuff
    def shutdown(option="shutdown"):
        print("Thread:", threading.current_thread())
        print("Process:", multiprocessing.current_process())
        print("SHUTDOWN FUNCTION CALLED", option)
        #return "shutdown", "TEST"
        cwd = os.getcwd()
        cmd = ["bash", f"{cwd:s}/shutdown", option]
        with open("output.txt", "w+") as file:
            subprocess.run(cmd, stdout=file)         
            print("Executed command '" + " ".join(cmd))
            file.seek(io.SEEK_SET)
            last_line = ""
            output = ""
            for line in file:
                output += line
                last_line = line.strip()
        return last_line, output
    def button_shutdown(option="shutdown"):
        requests.post("http://localhost/rpi", json={"option": "shutdown"})
        time.sleep(3)
    
    led_util.get_controller().setup_trigger(SHUTDOWN_PIN, button_shutdown)
    return app

if __name__=="__main__":
    app = create_app()
    app.run("0.0.0.0")
