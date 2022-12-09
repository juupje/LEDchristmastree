import time
import numpy as np
import pyaudio
import dancypi.config as config

class Microphone:
    def __init__(self, callback):
        self.callback = callback
        self._stop = False
        self.is_running = False
        self.p = pyaudio.PyAudio()

    def stop(self):
        self._stop = True

    def start_stream(self):
        if(self.is_running):
            print("There is already a stream running!")
            return False
        self.is_running = True
        self._stop = False
        frames_per_buffer = int(config.MIC_RATE / config.FPS)
        self.stream = self.p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=config.MIC_RATE,
                        input=True,
                        frames_per_buffer=frames_per_buffer)
        overflows = 0
        prev_ovf_time = time.time()
        while not self._stop:
            try:
                y = np.fromstring(self.stream.read(frames_per_buffer, exception_on_overflow=False), dtype=np.int16)
                y = y.astype(np.float32)
                self.stream.read(self.stream.get_read_available(), exception_on_overflow=False)
                self.callback(y)
            except IOError:
                overflows += 1
                if time.time() > prev_ovf_time + 1:
                    prev_ovf_time = time.time()
                    print('Audio buffer has overflowed {} times'.format(overflows))
        self.__stop()
    
    def __stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        self.is_running = False
        print("Mic stream stopped")
    
    def __del__(self):
        self.__stop()
