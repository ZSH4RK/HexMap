import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from hex import Hex  # your Hex class

class Grid:
    def __init__(self, radius: int, start_value: int):
        self.radius = radius
        self.start_value = start_value
        self.grid = self.generate_grid()
        self.grid_dict = {(h.x, h.y, h.z): h for h in self.grid}

    def generate_grid(self):
        r = self.radius
        return [
            Hex(x, y, -x - y)
            for x in range(-r, r + 1)
            for y in range(max(-r, -x - r), min(r, -x + r) + 1)
        ]

    def cube_to_pixel(self, hexes, size):
        # hexes: Nx3 array [[x, y, z], ...]
        x, y, z = hexes[:,0], hexes[:,1], hexes[:,2]
        px = size * np.sqrt(3) * (x + z / 2)
        py = size * 3/2 * z
        return px, py

    def draw_hex_grid(self, size=1):
        fig, ax = plt.subplots()

        # Convert hexes to numpy array
        hexes_array = np.array([[h.x, h.y, h.z] for h in self.grid])
        cx, cy = self.cube_to_pixel(hexes_array, size)

        # Precompute corner offsets
        angles = np.radians(np.arange(0, 360, 60) - 30)
        corner_offsets = np.stack(
            [np.cos(angles), np.sin(angles)],
            axis=1
        ) * size

        # Build polygons
        centers = np.stack([cx, cy], axis=1)
        polygons = (np.expand_dims(centers, 1) + corner_offsets).tolist()

        # -------- NEW PART: colour per hex --------
        VALUE_TO_COLOUR = [
            "darkblue",
            "blue",
            '#EED9A0',
            "olivedrab",
            "green",
            "darkgreen",
            '#556B2F',
            "grey",
            'darkgrey',
            "white",
            "maroon"
        ]

        facecolors = [
            VALUE_TO_COLOUR[h.value-1]   
            for h in self.grid
        ]
        

        collection = PolyCollection(
            polygons,
            edgecolors="black",
            facecolors=facecolors,  
            linewidths=0.1
        )

        ax.add_collection(collection)

        limit = size * (self.radius + 1) * 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal")
        ax.axis("off")

        fig.savefig("grid_vectorized.png", bbox_inches="tight", dpi=900)
        return ax