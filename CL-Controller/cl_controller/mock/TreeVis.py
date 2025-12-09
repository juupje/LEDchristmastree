from typing import Tuple, List
from .PixelStrip import PixelStrip
from cl_controller.utils import color_to_rgb

class TreeVis:
    def __init__(self, pixels: PixelStrip, locations: List[Tuple[int, int, int]]):
        self.pixels = pixels
        self.locations = locations
        self.pixels.add_show_callback(self.update_visualization)
    
    def update_visualization(self, leds: List[Tuple[int]]):
        try:
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D
        except Exception:
            # Fallback to simple textual output if matplotlib isn't available
            print("Updating tree visualization (matplotlib not available)")
            return

        # Convert LED colors from 0-255 to 0-1 RGBA tuples
        colors = [utils.int_to_rgba(led) for led in leds]

        # Initialize a non-blocking 3D window on first call
        if not hasattr(self, "_tv_initialized"):
            plt.ion()
            self._fig = plt.figure(figsize=(6, 8))
            self._ax = self._fig.add_subplot(111, projection="3d")

            # Interpret each location tuple (x, y) as (x, z) on the tree and place y=0
            # (Change this mapping if your locations mean something else.)
            xs = [loc[0] for loc in self.locations]
            ys = [0 for _ in self.locations]
            zs = [loc[1] for loc in self.locations]

            # Create scatter plot for LEDs
            self._scat = self._ax.scatter(xs, ys, zs, c=colors, s=80, depthshade=True)

            # Make the display nicer
            self._ax.set_xlabel("X")
            self._ax.set_ylabel("Y")
            self._ax.set_zlabel("Z (height)")
            margin = 1
            self._ax.set_xlim(min(xs, default=0) - margin, max(xs, default=0) + margin)
            self._ax.set_ylim(-1, 1)  # Y is thin for a tree visualization
            self._ax.set_zlim(min(zs, default=0) - margin, max(zs, default=0) + margin)
            self._ax.view_init(elev=30, azim=-60)

            self._fig.canvas.draw()
            plt.pause(0.001)
            self._tv_initialized = True
            return

        # Update colors on subsequent calls
        try:
            # matplotlib's 3D Path3DCollection uses _facecolor3d/_edgecolor3d internally
            # set_facecolor works for recent versions
            self._scat.set_facecolor(colors)
            self._scat.set_edgecolor(colors)
        except Exception:
            # best-effort update if the above fails
            self._scat._facecolor3d = colors
            self._scat._edgecolor3d = colors

        # Redraw the figure non-blocking
        self._fig.canvas.draw_idle()
        plt.pause(0.001)