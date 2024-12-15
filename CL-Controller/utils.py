#!/usr/bin/python3
from re import search
import numpy as np

regex = r"^\d{1,3},\d{1,3},\d{1,3}$"

def Color(r, g, b):
    #interchange red and green
    return (b << 16) | (r << 8) | g

def Color_array(r,g,b):
    b = np.left_shift(b.astype(int), 16)
    r = np.left_shift(r.astype(int), 8)
    g = g.astype(int)
    return np.bitwise_or(np.bitwise_or(b, r), g)

def color_brightness(r,g,b,brightness=255):
    #maximize brightness first, then scale it
    f = max(r,g,b)
    if(f == 0):
        return 0
    f = brightness/f
    return Color(int(r*f), int(g*f), int(b*f))

def colorToRGB(color):
    return (color >> 8 & 0xff, color & 0xff, color >> 16)

def parseColor(color, brightness=255):
    if(search(regex, color)):
        colors = color.split(',')
        r = clamp(int(colors[0]), 0, 255)
        b = clamp(int(colors[1]), 0, 255)
        g = clamp(int(colors[2]), 0, 255)
        return color_brightness(r, g, b, brightness)
    return Color(0,0,0)

def to_double_digit_hex(i):
    s = hex(i)[2:].rstrip("L")
    if(len(s)==1):
        return "0"+s
    elif(len(s)==0):
        return "00"
    return s

def rgb_to_hex(color):
    if(search(regex, color)):
        colors = color.split(",")
        r = clamp(int(colors[0]), 0, 255)
        g = clamp(int(colors[1]), 0, 255)
        b = clamp(int(colors[2]), 0, 255)
        return "#"+to_double_digit_hex(r) + to_double_digit_hex(g) + to_double_digit_hex(b)
    return "#000000"

def adjustBrightness(color, brightness):
    brightness = clamp(brightness, 0, 255)
    r,g,b = colorToRGB(color)
    f = brightness/255
    return Color(min(255,int(r*f)), min(255, int(g*f)), min(255, int(b*f)))

def parseColorMode(mode, brightness=255, is_odd_black=False, is_odd_black_constant=False):
    if(mode=="rainbow"):
        if(is_odd_black):
            return lambda x, max_x, i: wheel(int(x/max_x*100+i*100)%255, brightness) if i%2==0 else 0
        return lambda x, max_x, i: wheel(int(x/max_x*100+i*100)%255, brightness)
    elif(mode=="fixed"):
        if(is_odd_black):
            return lambda x, max_x, i: wheel(((i+1)*40)%255, brightness) if i%2==0 else 0
        return lambda x, max_x, i: wheel(((i+1)*40)%255, brightness)
    elif(parseColor(mode)>0):
        color = parseColor(mode, brightness)
        if(is_odd_black_constant):
            return lambda x, max_x, i: color if i%2==0 else 0
        return lambda x, max_x, i: color
    else:
        return None

def hsv_to_rgb(h, s, v):
    """
    h: hue, in degrees
    s: saturation, from 0 to 1
    v: value, from 0 to 1
    """
    if(s <= 0):
        return v, v, v
    if(h >= 360):
        h = 0
    h /= 60.
    i = int(h)
    f = h-i
    v *= 255
    p = int(v*(1-s))
    q = int(v*(1-s*f))
    t = int(v*(1-s*(1-f)))
    v = int(v)
    if(i==0):
        return v, t, p
    elif(i==1):
        return q, v, p
    elif(i==2):
        return p, v, t
    elif(i==3):
        return p, q, v
    elif(i==4):
        return t, p, v
    else:
        return v, p, q

def rgb_to_hsv(r, g, b):
    r /= 255
    g /= 255
    b /= 255
    min_value = min(r, g, b)
    max_value = max(r, g, b)
    h, s = 0
    v = max_value
    delta = value_max - value_min
    if(delta < 1e-5):
        return h, s, v
    if(max_value > 0):
        s = delta/max_value
    else:
        return h, s, v
    
    if(r >= max_value):
        h = (g-b)/delta
    elif(g >= max_value):
        h = 2+(b-r)/delta
    else:
        h = 4+(r-g)/delta
    h *= 60
    if(h < 0):
        h += 360
    return h, s, v


def wheel(pos, brightness=255):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return color_brightness(pos * 3, 255 - pos * 3, 0, brightness)
    elif pos < 170:
        pos -= 85
        return color_brightness(255 - pos * 3, 0, pos * 3, brightness)
    else:
        pos -= 170
        return color_brightness(0, pos * 3, 255 - pos * 3, brightness)


def clamp(x, lower, upper):
    return min(max(x, lower), upper)

def is_raspberrypi():
    try:
        with open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False