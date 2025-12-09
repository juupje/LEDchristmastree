from flask import render_template
import subprocess
import cl_controller.utils as utils
from cl_controller.animations import animations as anim
import json, html

animdata = None
result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE)
IP = result.stdout.decode("utf-8").split(" ")[0]
MAIN_TEMPLATE = "index.html"
ANIM_TEMPLATE = "animation.html"

class Element:
    def __init__(self, name, url):
        self.items = []
        self.names = []
        self.name = name
        self.url = url

    def add_button(self, display_name, name, callback):
        button = f"<tr><td colspan=3 class='center-cell'><button id='{name:s}' class='table-btn' onclick='{callback:s}'>{display_name:s}</button></td></tr>"
        self.items.append(button)

    def add_slider(self, display_name, name, min, max, val, step=1):
        slider = f"<tr><td>{display_name:s}</td>"
        slider += f"<td class='slider-cell'><input type='range' name='{name:s}' min='{min}' max='{max}' value='{val}' step='{step}' onchange='slider_update(\"{name:s}\")' class='slider' id='{name:s}'></td>"
        slider += f"<td class='output' id='{name:s}_output'>{val}</td></tr>"
        self.items.append(slider)
        self.names.append(name)

    def add_toggle(self, display_name, name, default):
        toggle = f"<tr><td>{display_name:s}</td>"
        toggle += f"<td><input id='{name:s}' class='toggle-switch' type='checkbox' name='{name:s}'" + (" checked" if default else "") +f"><label class='toggle-switch-label' for='{name:s}'>Toggle</label></td>"
        toggle += f"<td></td></tr>"
        self.items.append(toggle)
        self.names.append(name)

    def add_color(self, display_name, name, default, presets=None):
        color = f"<tr><td>{display_name:s}</td><td>"
        if(presets):
            presets = presets.copy()
            presets.append("other")
            if(default[0] == "#"):
                def_color = default
                default = "other"
            else:
                def_color = "#ff0000"
            color += self._create_dropdown(name, presets, default, onclick='color_preset_changed')
        else:
            def_color = default
        color += f"<input type='color' id='{name:s}' name='{name:s}' value='{def_color:s}' onchange='color_update(\"{name:s}\")'"
        if(default != def_color and default != "other"):
            color += " style='display:none'"
        color += "></td>"
        color += f"<td class='output' id='{name:s}_output'>{def_color:s}</td></tr>"
        self.items.append(color)
        self.names.append(name)

    def _create_dropdown(self, name, options, default, onclick=None):
        dd = f"""<form class='drop-down_container'><ul class='drop-down'>\n
                    <li><input class='drop-down_close' type='radio' name='drop-down_{name:s}' id='{name:s}-close' value=''/><span class='drop-down_label drop-down_placeholder'>Select option</span></li>\n
                    <li class='drop-down_items'>\n
                        <input class='drop-down_expand' type='radio' name='drop-down_{name:s}' id='{name:s}_open'/><label class='drop-down_close_label' for='{name:s}_close'></label>\n
                        <ul class='drop-down_options'>\n
                    """
        for option in options:
            dd += f"<li class='drop-down_option'>\n"
            dd += f"<input class='drop-down_input'" + (f" onclick='{onclick:s}(\"{name:s}\", \"{option:s}\")'" if onclick else "") \
                    +f" type='radio' name='drop-down_{name:s}' value='{option:s}' id='{name:s}-{option:s}' " \
                    + ("checked" if option==default else "")+"/>\n"
            dd += f"<label class='drop-down_label' for='{name:s}-{option:s}'>{option:s}</label>\n"
            dd += "</li>\n"
        dd += f"</ul><label class='drop-down_expand_label' for='{name:s}_open'></label>\n"
        dd += "</li></ul></form>"
        return dd

    def add_list(self, display_name, name, options, default=None):
        if(default is None):
            default = options[0]
        select = f"<tr><td>{display_name:s}</td>\n"
        select += f"<td>"+self._create_dropdown(name,options,default)+"</td><td></td></tr>\n"
        self.items.append(select)
        self.names.append(name)
    
    def add_hidden(self, name, value):
        hidden = f"<input type='hidden' name='{name:s}' id='{name:s}' value='{value}'>"
        self.items.append(hidden)
        self.names.append(name)

    def _create_button(self):
        return f"<tr><td colspan=3 class='center-cell'><button id='{self.name:s}_btn' class='table-btn' onclick='send_{self.name:s}()'>Send</button></td></tr>\n"

    def create_table(self):
        s = f"<table id='{self.name:s}'>\n"
        for i in range(len(self.items)):
            s += self.items[i] +"\n"
        s += self._create_button()
        s += "</table>\n"
        return s
    
    def get_script(self):
        script  = f"function parse_data()" + "{\n"
        script += f"    return collect_values(\"{self.name:s}\",[\"" +"\",\"".join(self.names) +"\"]);\n"
        script +=  "}\n"
        script += f"function send_{self.name:s}()" + "{\n"
        script += f"    send_data('POST', '{self.url:s}', parse_data());\n"
        script +=  "}\n"
        return script

def create_tables():
    table_leds = Element("led_table", "/api/all/")
    table_leds.add_toggle("Power", "power", True)
    table_leds.add_toggle("State", "state", True)
    table_leds.add_color("Color", "color", utils.rgb_to_hex("255,0,0"))
    table_leds.add_slider("Brightness", "brightness", min=0, max=255, val=200, step=1)
    table_leds_html = table_leds.create_table()
    script = "<script>\n" + table_leds.get_script() + "</script>\n"

    table_animation = "<h4 style='text-align:center'><a onclick='stop_animation()' href=''>Stop animation</a></h4>"
    table_animation += "<ul id='anim_list'>"
    #get animations info
    if(animdata):
        for animation in animdata.names:
            info = animdata.info[animation]
            table_animation += f"<li onclick='window.location.href=\"home?animation={html.escape(animation):s}\";'><span class='anim_name'>{html.escape(info['name']):s}</span><br/>{html.escape(info['description']):s}</li>\n"
    table_animation += "</ul>\n"

    table_controller = "<div class='controller'><p><button id='shutdown' onclick='rpi_command(\"option\", \"shutdown\", \"/api/rpi/\");'>Shutdown</button></p>\n"
    table_controller += "<p><button id='restart' onclick='rpi_command(\"option\",\"restart\", \"/api/rpi/\");'>Restart</button></p></div>\n"
    return dict(table_leds=table_leds_html, table_animaties=table_animation, table_controller=table_controller, script=script)

def create_animation_page(anim_name:str, preset: int | None = None):
    def calculate_step(low, high):
        d = high-low
        if (d < 1):
            step = 0.01
        elif (d < 10):
            step = 0.1
        elif (d < 50):
            step = 0.25
        elif (d < 150):
            step = 0.5
        else:
            step = 1.0
        if(low != 0 and abs(low) < step):
            return abs(step)*(-1 if low<0 else 1)
        return step

    def create_setting(name, setting):
        display_name = name[0].upper() + name[1:].replace("_", " ")
        if(setting["type"]=="bool"):
            settings.add_toggle(display_name, name, setting["default"])
        elif(setting["type"]=="color"):
            if("presets" in setting):
                settings.add_color(display_name, name,
                    default=utils.rgb_to_hex(setting["default"]) if "," in setting["default"] else setting["default"],
                    presets=setting["presets"])
            else:
                settings.add_color(display_name, name, default=utils.rgb_to_hex(setting["default"]))
        elif(setting["type"]=="float"):
            step = setting.get("step", calculate_step(setting["min"], setting["max"]))
            settings.add_slider(display_name, name, min=setting["min"], max=setting["max"], val=setting["default"], step=step)
        elif(setting["type"]=="int"):
            settings.add_slider(display_name, name, min=int(setting["min"]), max=int(setting["max"]), val=int(setting["default"]), step=1)
        elif(setting["type"]=="list"):
            settings.add_list(display_name, name, options=setting["options"], default=setting["default"])
    
    animation = animdata.get(anim_name) if animdata is not None else None
    if(animation is None or animdata is None):
        return dict(animation_name="Unknown animation. <a href='/home'>Go back</a>", script="", settings="")
    settings = Element("settings_table", "/api/anim/")
    settings.add_hidden("name", value=anim_name)
    settings.add_button("Presets", "presets", f"toggle_preset_dialog(\"{anim_name}\")")
    instructions = animation.instructions

    #load the preset
    preset_result = None
    if preset is not None:
        try:
            preset = int(preset)
            from preset_handler import ThreadedDatabaseHandler, DATABASE_PATH
            handler = ThreadedDatabaseHandler(DATABASE_PATH)
            preset_result, _ = handler.execute("SELECT id, name, animation, created_on, json FROM presets WHERE id=(:id)", args=dict(id=preset), one=True)  # type: ignore
            print("Loading preset:", preset_result)
            if preset_result is None:
                print(f"Could not find preset with ID {preset}!")
                raise Exception("Preset not found")
            if preset_result["animation"] != anim_name:
                print(f"Preset for {preset_result['animation']} does not match the animation ({anim_name})!")
                preset_result = None
        except Exception as e:
            print("Something went wrong...")
            print(e)

    if(preset_result):
        if type(preset_result["json"]) is str:
            preset_result["json"] = json.loads(preset_result["json"])
        for key in preset_result["json"]:
            if key in animation.settings:
                instructions[key]["default"] = preset_result["json"][key]

    for key in animation.settings:
        setting = instructions[key]
        create_setting(key,setting)
    settings.add_button("Save preset", "save_preset", f"save_preset(null, \"{anim_name}\", parse_data());")
    return dict(animation_name=animdata.info[anim_name]["name"], script="<script>\n"+settings.get_script()+"</script>\n", settings=settings.create_table())

def render_webpage(animation: str | None = None, preset: int | None = None):
    global animdata
    if animdata is None:
        animdata = anim.AnimData()
    if(animation is None):
        return render_template(MAIN_TEMPLATE, **create_tables())
    else:
        return render_template(ANIM_TEMPLATE, **create_animation_page(animation, preset))

