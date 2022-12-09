import time
import numpy as np
from scipy.ndimage.filters import gaussian_filter1d
import dancypi.config as config
import dancypi.microphone as microphone
import dancypi.dsp as dsp

import utils
#scroll_divisor_config = 4 if sys.argv[1] == "scroll_quad" else 2
scroll_divisor_config = 2

def frames_per_second():
    """Return the estimated frames per second

    Returns the current estimate for frames-per-second (FPS).
    FPS is estimated by measured the amount of time that has elapsed since
    this function was previously called. The FPS estimate is low-pass filtered
    to reduce noise.

    This function is intended to be called one time for every iteration of
    the program's main loop.

    Returns
    -------
    fps : float
        Estimated frames-per-second. This value is low-pass filtered
        to reduce noise.
    """
    global _time_prev, _fps
    time_now = time.time() * 1000.0
    dt = time_now - _time_prev
    _time_prev = time_now
    if dt == 0.0:
        return _fps.value
    return _fps.update(1000.0 / dt), dt


def memoize(function):
    """Provides a decorator for memoizing functions"""
    from functools import wraps
    memo = {}

    @wraps(function)
    def wrapper(*args):
        if args in memo:
            return memo[args]
        else:
            rv = function(*args)
            memo[args] = rv
            return rv
    return wrapper


@memoize
def _normalized_linspace(size):
    return np.linspace(0, 1, size)

def clamp(x):
    if(x>=p.shape[1]):
        return p.shape[1]-1
    #if(x < 0):
    #    return 0
    return x

def interpolate(y, new_length):
    """Intelligently resizes the array by linearly interpolating the values

    Parameters
    ----------
    y : np.array
        Array that should be resized

    new_length : int
        The length of the new interpolated array

    Returns
    -------
    z : np.array
        New array with length of new_length that contains the interpolated
        values of y.
    """
    if len(y) == new_length:
        return y
    x_old = _normalized_linspace(len(y))
    x_new = _normalized_linspace(new_length)
    z = np.interp(x_new, x_old, y)
    return z

def visualize_scroll(y, scale=None):
    """Effect that originates in the center and scrolls outwards"""
    global p
    y = y**2.0
    gain.update(y)
    y /= gain.value
    y *= 255.0
    r = int(np.max(y[:len(y) // 3]))
    g = int(np.max(y[len(y) // 3: 2 * len(y) // 3]))
    b = int(np.max(y[2 * len(y) // 3:]))
    # Scrolling effect window
    p[:, 1:] = p[:, :-1]
    p *= 0.98
    p = gaussian_filter1d(p, sigma=0.2)
    # Create new color originating at the center
    p[0, 0] = r
    p[1, 0] = g
    p[2, 0] = b
    # Update the LED strip
    return np.concatenate((p[:, ::-1], p), axis=1)

def visualize_energy(y, scale=1.0):
    """Effect that expands from the center with increasing sound energy"""
    global p
    y = np.copy(y)
    gain.update(y)
    y /= gain.value
    # Scale by the width of the LED strip
    y *= float((config.N_PIXELS // 2) - 1)
    # Map color channels according to energy in the different freq bands
    piece = len(y) // 9
    r = clamp(int(np.mean(y[:piece*4]**scale)))
    g = clamp(int(np.mean(y[piece*4: piece*6]**scale)))
    b = clamp(int(np.mean(y[piece*6:]**scale)))
    # Assign color to different frequency regions
    p[0, :r] = 255.0
    p[0, r:] = 0.0
    p[1, :g] = 255.0
    p[1, g:] = 0.0
    p[2, :b] = 255.0
    p[2, b:] = 0.0
    #we need to bring out the right color

    p_filt.update(p)
    p = np.round(p_filt.value)
    # Apply substantial blur to smooth the edges
    p[0, :] = gaussian_filter1d(p[0, :], sigma=4.0)
    p[1, :] = gaussian_filter1d(p[1, :], sigma=4.0)
    p[2, :] = gaussian_filter1d(p[2, :], sigma=4.0)
    # Set the new pixel value
    return np.concatenate((p[:, ::-1], p), axis=1)

def visualize_spectrum(y, scale=None):
    """Effect that maps the Mel filterbank frequencies onto the LED strip"""
    global _prev_spectrum
    y = np.copy(interpolate(y, config.N_PIXELS // 2))
    common_mode.update(y)
    diff = y - _prev_spectrum
    _prev_spectrum = np.copy(y)
    # Color channel mappings
    r = r_filt.update(y - common_mode.value)
    g = np.abs(diff)
    b = b_filt.update(np.copy(y))
    # Mirror the color channels for symmetric output
    r = np.concatenate((r[::-1], r))
    g = np.concatenate((g[::-1], g))
    b = np.concatenate((b[::-1], b))
    output = np.array([r, g,b]) * 255
    return output

def initialize_filters():
    global r_filt, g_filt, b_filt, common_mode, p_filt, p, gain
    r_filt = dsp.ExpFilter(np.tile(0.01, config.N_PIXELS // 2),
                       alpha_decay=0.2, alpha_rise=0.99)
    g_filt = dsp.ExpFilter(np.tile(0.01, config.N_PIXELS // 2),
                        alpha_decay=0.05, alpha_rise=0.3)
    b_filt = dsp.ExpFilter(np.tile(0.01, config.N_PIXELS // 2),
                        alpha_decay=0.1, alpha_rise=0.5)
    common_mode = dsp.ExpFilter(np.tile(0.01, config.N_PIXELS // 2),
                        alpha_decay=0.99, alpha_rise=0.01)
    p_filt = dsp.ExpFilter(np.tile(1, (3, config.N_PIXELS // 2)),
                        alpha_decay=0.1, alpha_rise=0.99)
    # scroll_divisor_config config is set to 2 if scroll_quad is sent in the arg
    p = np.tile(1.0, (3, config.N_PIXELS // scroll_divisor_config))
    gain = dsp.ExpFilter(np.tile(0.01, config.N_FFT_BINS),
                        alpha_decay=0.01, alpha_rise=0.99)


def initialize_fps():
    global _time_prev, _fps
    _time_prev = time.time() * 1000.0
    """The previous time that the frames_per_second() function was called"""

    _fps = dsp.ExpFilter(val=config.FPS, alpha_decay=0.2, alpha_rise=0.2)

def initialize():
    global fft_plot_filter, mel_gain, mel_smoothing, volume, fft_window, samples_per_frame, _gamma, _prev_spectrum
    fft_plot_filter = dsp.ExpFilter(np.tile(1e-1, config.N_FFT_BINS),
                            alpha_decay=0.5, alpha_rise=0.99)
    mel_gain = dsp.ExpFilter(np.tile(1e-1, config.N_FFT_BINS),
                            alpha_decay=0.01, alpha_rise=0.99)
    mel_smoothing = dsp.ExpFilter(np.tile(1e-1, config.N_FFT_BINS),
                            alpha_decay=0.5, alpha_rise=0.99)
    volume = dsp.ExpFilter(config.MIN_VOLUME_THRESHOLD,
                        alpha_decay=0.02, alpha_rise=0.02)
    fft_window = np.hamming(int(config.MIC_RATE / config.FPS) * config.N_ROLLING_HISTORY)

    # Number of audio samples to read every time frame
    samples_per_frame = int(config.MIC_RATE / config.FPS)

    # Array containing the rolling audio sample window

    _gamma = np.load(config.GAMMA_TABLE_PATH)
    """Gamma lookup table used for nonlinear brightness correction"""

    _prev_spectrum = np.tile(0.01, config.N_PIXELS // 2)

    initialize_filters()
    initialize_fps()

class Visualizer:
    def __init__(self,name:str="energy", scale=1.0, bins=12):
        config.N_PIXELS = bins
        initialize()
        if name == "spectrum":
            self.visualization_type = visualize_spectrum
        elif name == "energy":
            self.visualization_type = visualize_energy
        elif name == "scroll":
            self.visualization_type = visualize_scroll
        else:
            raise ValueError("Visualizer " +str(name) +" unknown")

        """Pixel values that were most recently displayed on the LED strip"""
        self._prev_pixels = np.tile(253, (3, config.N_PIXELS))
        """Pixel values for the LED strip"""
        self.pixels = np.tile(1, (3, config.N_PIXELS))
        self.scale = scale
        self.count = 0
        self.y_roll = np.random.rand(config.N_ROLLING_HISTORY, samples_per_frame) / 1e16

    def microphone_update(self, audio_samples):
        # Normalize samples between 0 and 1
        y = audio_samples / 2.0**15
        # Construct a rolling window of audio samples
        self.y_roll[:-1] = self.y_roll[1:]
        self.y_roll[-1, :] = np.copy(y)
        y_data = np.concatenate(self.y_roll, axis=0).astype(np.float32)
        
        vol = np.max(np.abs(y_data))
        if vol < config.MIN_VOLUME_THRESHOLD:
            #print('No audio input. Volume below threshold. Volume:', vol)
            self.pixels = np.tile(0, (3, config.N_PIXELS))
            self._update()
        else:
            # Transform audio input into the frequency domain
            N = len(y_data)
            N_zeros = 2**int(np.ceil(np.log2(N))) - N
            # Pad with zeros until the next power of two
            y_data *= fft_window
            y_padded = np.pad(y_data, (0, N_zeros), mode='constant')
            YS = np.abs(np.fft.rfft(y_padded)[:N // 2])
            # Construct a Mel filterbank from the FFT data
            mel = np.atleast_2d(YS).T * dsp.mel_y.T
            # Scale data to values more suitable for visualization
            # mel = np.sum(mel, axis=0)
            mel = np.sum(mel, axis=0)
            mel = mel**2.0
            # Gain normalization
            mel_gain.update(np.max(gaussian_filter1d(mel, sigma=1.0)))
            mel /= mel_gain.value
            mel = mel_smoothing.update(mel)
            # Map filterbank output onto LED strip
            self.pixels = self.visualization_type(mel, self.scale)
            self._update()
            self.count += 1
            if(self.count % 100 == 0):
                print("State: ", p)

        if config.DISPLAY_FPS:
            fps, dt = frames_per_second()
            #remaining = 1/config.FPS-dt
            #if(remaining>0):
            #    time.sleep(1/config.FPS)
            if time.time() > self.prev_fps_update+2:
                self.prev_fps_update = time.time()
                print('FPS {:.0f} / {:.0f}'.format(fps, config.FPS))
    

    def _update(self):
        """Writes new LED values to the Raspberry Pi's LED strip

        Raspberry Pi uses the rpi_ws281x to control the LED strip directly.
        This function updates the LED strip with new values.
        """
        # Truncate values and cast to integer
        self.pixels = np.clip(self.pixels, 0, 255).astype(int)
        # Optional gamma correction
        p = _gamma[self.pixels] if config.SOFTWARE_GAMMA_CORRECTION else np.copy(self.pixels)
        self._prev_pixels = np.copy(p)
        self.callback(utils.Color_array(p[0,:], p[1,:], p[2,:]))


    def start(self, callback):
        self.callback = callback
        self.prev_fps_update = time.time()
        # Start listening to live audio stream
        self.mic = microphone.Microphone(self.microphone_update)
        self.mic.start_stream()
    
    def stop(self):
        print("Stopping microphone")
        self.mic.stop()

    def __del__(self):
        self.stop()