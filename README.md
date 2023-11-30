# LED Christmas tree
Made by me. Nothing is guaranteed. If you follow these steps, your tree (probably) won't spontaneously ignite.

## Hardware Requirements
- Raspberry Pi (works on zero 2w)
- LED string, for example, [ws2811](https://www.amazon.de/dp/B06XN66ZY6/ref=pe_27091401_487027711_TE_SCE_dp_1). Make sure you get enough LEDs. On a tree that is 90cm tall, I used 100 LEDs. You can get a string that works on 5V or 12V (see more below).
- A power supply unit. 5V lights can usually be powered from a phone charger or similar (NOT through the Raspberry Pi's pins!). If you decide on a 12V string, I'd recommend a dual 5V and 12V PSU. That way, you can connect the Pi and the LEDs to the same PSU (with a common ground). I used a Mean Well RD-65A.
- Cables to connect everything. Most jumper wires will do just fine, though you might need longer wires depending on your setup.
- A relay (unless you want your lights to be on all the time. Note that the LEDs will draw a significant amount of power even when off).
- A SN74AHCT125. For controlling the 5V data line of the LED string with a 3.3V GPIO pin. This is not strictly necessary, but reduces flickering.
- A 120Ω resistor
- Patience for debugging.
- A computer with a webcam/camera.

## Other requirements
### Raspberry pi
- A setup python environment (see below).
- Configured SSH access. I am assuming the Pi's username is `pi`, and its network name `raspberrypi.local`. You can also use its IP instead.
- WiFi access (Ethernet works too, but then you'll have an extra cable)

### Computer
- A setup python environment (see below)
- Configured SSH access to the Raspberry Pi

## Setup
### The hardware

1. Put the LEDs in the tree. Make sure they are distributed evenly!
2. Connect all the components according to this schematic. The component on the very left is the PSU, the one in the top middle is the relay.
![circuit](circuit.svg)

### The rest
Now comes the fun part.

#### 1. Connecting to the Raspberry Pi
1. Turn on the Pi (I will call it controller from now on). Open a terminal and start an SSH connection (`ssh raspberrypi.local`, or better, set up an ssh-key ([windows](https://pimylifeup.com/raspberry-pi-ssh-keys/)/[linux](https://www.geekyhacker.com/configure-ssh-key-based-authentication-on-raspberry-pi/))).

2. Copy the [CL-Controller](CL-Controller/) folder to the Documents folder (or wherever you want it, I don't care. Just make sure to edit the necessary paths in the service files).
3. Edit the [CL-Controller/run](CL-Controller/run) script. Change the paths in the third line and activate the correct python environment in the second line.
4. Copy [cl-server.service](cl-server.service) to `/lib/systemd/system`.
5. Activate the service through `systemd enable cl-server.service`
6. Lights turn on?

#### 2. Calibrating the LEDs
Get a wooden board or piece of paper. Draw a circle on it that is approximately the same size as the stand of the Christmas Tree. Indicate a spot on the circle and draw further spots separated by 45 degrees (or 22.5 degrees if you've got too much time on your hands and would like better precision of the animations later on).

Position the tree in the middle of a dark room (you can keep the lights on for now) on top of the board or paper. Make sure it is nicely centered on the circle. Rotate the tree such that something on it (perhaps one of its feet) points to the 0-degree mark on the circle. Point the webcam at it. 

Run the `cam_alignment.py`: open a terminal, activate the python environment, and run 
```bash
python3 cam_alignment.py
```
A window with a vertical bar in the middle should pop up. Make sure the center of the tree lines up with the red line. Position the webcam such that the tree covers nearly the whole picture. Don't put the tree too close to the camera to prevent fish-eye and parallax effects.

Now, turn off the lights (and dim the PC screen if necessary to reduce reflecting light and to protect your eyes). Run

```bash
python3 led_iterator.py 0
```
and wait for it to be done. Then turn the tree to the next mark (45 degrees) and run
```bash
python3 led_iterator.py 45
```
Continue doing this until you're back at the start (don't do the 360 degrees. That is just confusing and might lead to errors in the calculation). Finally, run
```bash
python3 loc_finder.py
```
This will calculate the 3D coordinates of all LEDs based on the webcam input of the previous steps. This step might require a substantial amount of fine-tuning (see the sections marked for hardcoding in the script.). Play with it until you are satisfied.

Now you're done with the calibration and can upload the resulting file `locations.npy` to the controller. You can run this command on the computer:
```bash
scp locations.npy pi@raspberrypi.local:~/Documents/CL-Controller/animations/locations.npy
```
Restart the Raspberry Pi (`sudo reboot`).

## Usage
See documentation.md for the REST API. You can use the accompanying Android app or simply go to `http:raspberrypi.local/home` on any browser. From there, you can figure out the details by playing.

## Notes
### 5V vs 12V
You can get a WS2811 string suitable for 5V or 12V. The advantage of 5V is that you can power the string and the Raspberry Pi using the same power supply. That power supply can be a simple phone charger with a spliced USB cable (though it should be a powerful one, depending on the number of LEDs). However, as the LEDs get only 5V, they will draw much more current, meaning that you should use thicker cables. (Pay attention to the max current rating of the cables!). Also, note that you cannot power the LEDs from a GPIO pin on the Pi!

Using a 12V string will reduce the current draw significantly, allowing you to use thinner cables (and also a longer LED string). However, this does mean that you need a separate power supply for the Raspberry Pi and the string, with a common ground (such as a dual 12V/5V PSU).

### Animation based on music
This is waayyyy too finicky. Just don't try this. I'm not going to explain the intricacies of how I got this to work (sometimes).
Also requires the `pyaudio` package.

### Animation based on camera
This functionality used Google's MoveNet to infer the position of 17 keypoints of a body in the view of the camera. It then uses a custom trained neural network to identify hands and their position. Using this information an animiation is created.

This is still in development and should not be used. It also required the `tflite` package.

## Python environments
### On the Raspberry Pi
The following packages are required.
1. `flask` and `flask_restx`
2. `gunicorn`
3. `numpy`
4. `RPi.GPIO`
5. `rpi_ws281x`

Note that `rpi_ws281x`, `RPi.GPIO` and `flask_restx` should be installed with pip, not with conda/mamba.

### On the computer
1. `numpy`
2. `requests`
3. `opencv2`
4. `matplotlib` (only for `validation.py`)



