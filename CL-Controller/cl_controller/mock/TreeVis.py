from typing import Tuple, List, Optional
from .PixelStrip import PixelStrip
from cl_controller.utils import color_to_rgb
from multiprocessing import Process, Queue
import queue as _queue
import numpy as np

class TreeVis:
    def __init__(self, pixels: PixelStrip, locations: List[Tuple[int, int, int]]):
        self.pixels = pixels
        self.locations = locations

        # Inter-process queue that holds at most one latest state
        self._queue: Queue = Queue(maxsize=1)

        # Start visualiser in a separate process (matplotlib will run in that process's main thread)
        self._proc = Process(target=self._run_visualizer_process, args=(self._queue, self.locations), daemon=True)
        self._proc.start()

        # Intercept PixelStrip.show to push new states into the visualizer
        self.pixels.add_show_callback(self.update_visualization)

    def update_visualization(self, leds: List[int]):
        # Non-blocking: try to put the latest state, if full drop the old and replace
        try:
            self._queue.put_nowait(list(leds))
        except _queue.Full:
            try:
                # remove old value, then put the new one
                self._queue.get_nowait()
                self._queue.put_nowait(list(leds))
            except Exception:
                # best-effort: ignore if queue operations fail
                pass

    @staticmethod
    def _run_visualizer_process(q: Queue, locations: np.ndarray):
        try:
            import logging
            logging.basicConfig(level=logging.ERROR)
            import matplotlib.pyplot as plt
        except Exception:
            print("TreeVis: matplotlib not available in visualizer process, exiting")
            return

        try:
            plt.ion()
            fig = plt.figure(figsize=(6, 8))
            ax = fig.add_subplot(111, projection="3d")

            xs = locations[ :,0]
            ys = locations[ :,1]
            zs = locations[ :,2]

            init_colors = [[0, 0, 0] for _ in locations]
            scat = ax.scatter(xs, ys, zs, c=init_colors, s=80, depthshade=True)  # type: ignore

            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_zlabel("Z (height)")
            margin = 1
            ax.set_xlim(min(xs, default=0) - margin, max(xs, default=0) + margin)
            ax.set_ylim(min(ys, default=0) - margin, max(ys, default=0) + margin)
            ax.set_zlim(min(zs, default=0) - margin, max(zs, default=0) + margin)
            ax.view_init(elev=2, azim=-60)

            fig.canvas.draw()
            plt.pause(0.001)

            last_displayed: Optional[List[int]] = None

            while True:
                try:
                    current = q.get(timeout=0.1)
                except _queue.Empty:
                    current = None

                if current is not None and current != last_displayed:
                    try:
                        colors = [[c / 255 for c in color_to_rgb(led)] for led in current]
                    except Exception:
                        colors = [[0, 0, 0] for _ in locations]

                    try:
                        scat.set_facecolor(colors)  # type: ignore
                        scat.set_edgecolor(colors)  # type: ignore
                    except Exception:
                        pass

                    fig.canvas.draw_idle()
                    last_displayed = current

                # keep GUI responsive
                plt.pause(0.05)
        except Exception:
            print("TreeVis: visualizer process exiting due to an error")
            return