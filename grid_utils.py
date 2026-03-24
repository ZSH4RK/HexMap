import math
import numpy as np
import random
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from hex import Hex
from plate import Plate

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

    def smooth_noise(self, x, z, scale=0.08):
        return (
            math.sin(x * scale)
            + math.sin(z * scale * 1.3)
            + math.sin((x + z) * scale * 0.7)
        ) / 3

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
    
    def is_boundary(self, hex):
        for n in hex.get_all_neighbours(self.grid_dict):
            if n.plate_id != hex.plate_id:
                return True
        return False
                
    def generate_plates(self, num_plates):
        import heapq
        from itertools import count

        self.plates = []

        seeds = random.sample(self.grid, num_plates)

        ownership = {}

        frontier = []

        unique = count()

        # create plates
        for i, seed in enumerate(seeds):
            plate_type = random.choices(["oceanic", "continental"], weights=[0.6, 0.4], k=1)
            plate = Plate(i, plate_type, (seed.x, seed.y, seed.z))

            plate.hexes.append(seed)
            self.plates.append(plate)

            ownership[(seed.x, seed.y, seed.z)] = i

            # (cost, tie_breaker, hex, plate_id)
            heapq.heappush(frontier, (0, next(unique), seed, i))

        directions = [
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (-1, 1, 0), (-1, 0, 1), (0, -1, 1)
        ]

        while frontier:
            cost, _, hex_cell, plate_id = heapq.heappop(frontier)

            for dx, dy, dz in directions:
                coords = (
                    hex_cell.x + dx,
                    hex_cell.y + dy,
                    hex_cell.z + dz
                )

                if coords not in self.grid_dict:
                    continue

                if coords in ownership:
                    continue

                neighbor = self.grid_dict[coords]

                ownership[coords] = plate_id
                self.plates[plate_id].hexes.append(neighbor)

                n = (
                    self.smooth_noise(neighbor.x * 0.5, neighbor.z * 0.5) * 0.5 +
                    self.smooth_noise(neighbor.x * 2.0, neighbor.z * 2.0) * 0.3 +
                    self.smooth_noise(neighbor.x * 5.0, neighbor.z * 5.0) * 0.2
                )


                plate_noise = hash((plate_id, neighbor.x, neighbor.z)) % 100 / 100.0

                growth_cost = cost + 1.0 + n * 1.5 + plate_noise * 0.8
                heapq.heappush(
                    frontier,
                    (growth_cost, next(unique), neighbor, plate_id)
                )

        # store plate ids
        for coords, pid in ownership.items():
            self.grid_dict[coords].plate_id = pid

    def boundary_type(self, h):
        my_plate = self.plates[h.plate_id]

        for n in self.neighbors(h):
            if n.plate_id != h.plate_id:
                other = self.plates[n.plate_id]

                relative_motion = np.dot(
                    my_plate.velocity - other.velocity,
                    self.direction_to(h, n)
                )

                if relative_motion > 0:
                    return "convergent"
                elif relative_motion < 0:
                    return "divergent"

        return "transform"
    
    def boundary_profile(d, peak=3, width=6):
        x = d / width
        return x * np.exp(-x)   # smooth bump curve

    def simulate_plates(self, steps=10, uplift_rate=0.05, rift_rate=0.02, smoothing=0.2,
                    ocean_base=-1, continental_base=0.0):

        from collections import deque

        # Step 1: assign random plate velocities
        for plate in self.plates:
            angle = random.uniform(0, 2*np.pi)
            speed = random.uniform(0.1, 0.5)
            plate.velocity = np.array([np.cos(angle) * speed, np.sin(angle) * speed])

        # Step 2: initialize heights
        for h in self.grid:
            plate = self.plates[h.plate_id]
            h.height = ocean_base if plate.plate_type == "oceanic" else continental_base

        directions = [
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (-1, 1, 0), (-1, 0, 1), (0, -1, 1)
        ]

        # -----------------------------
        # 🔥 NEW: find boundary hexes
        # -----------------------------
        boundary_hexes = [h for h in self.grid if self.is_boundary(h)]
        # -----------------------------
        # 🔥 NEW: distance from boundary (BFS)
        # -----------------------------
        from collections import deque

        distance = {h: float("inf") for h in self.grid}
        queue = deque()

        for h in boundary_hexes:
            distance[h] = 0
            queue.append(h)

        while queue:
            current = queue.popleft()

            for n in current.get_all_neighbours(self.grid_dict):
                if distance[n] > distance[current] + 1:
                    distance[n] = distance[current] + 1
                    queue.append(n)

        max_dist = max(distance.values()) + 1e-6

        # -----------------------------
        # Simulation loop
        # -----------------------------
        for h in self.grid:

            d = distance[h]

            if not np.isfinite(d):
                continue

            effect = self.boundary_profile(d)

            if effect < 0.001:
                continue

            btype = self.boundary_type(h)
            plate = self.plates[h.plate_id]

            # --- CONVERGENT ---
            if btype == "convergent":

                if plate.plate_type == "continental":
                    # mountain building inland
                    h.height += 2.5 * effect

                else:  # oceanic
                    # trench formation
                    h.height -= 2.0 * effect

            # --- DIVERGENT ---
            elif btype == "divergent":
                # spreading ridges / rifts
                h.height -= 1.2 * effect

            # --- TRANSFORM ---
            else:
                # small roughness only
                h.height += np.random.uniform(-0.1, 0.1) * effect
            # -----------------------------
            # Smooth terrain
            # -----------------------------
            smoothed_heights = {}
            for h in self.grid:
                total = h.height
                count = 1
                for dx, dy, dz in directions:
                    n_coords = (h.x + dx, h.y + dy, h.z + dz)
                    if n_coords in self.grid_dict:
                        total += self.grid_dict[n_coords].height
                        count += 1
                smoothed_heights[h] = total / count

            for h, h_smooth in smoothed_heights.items():
                h.height = h.height * (1 - smoothing) + h_smooth * smoothing

            # -----------------------------
            # 🔥 NEW: interior shaping
            # -----------------------------
            for h in self.grid:
                d = distance[h] / max_dist

                # nonlinear falloff = more natural
                d = d ** 1.5

                plate = self.plates[h.plate_id]

                if plate.plate_type == "oceanic":
                    h.height -= d * 0.6   # deeper ocean interiors
                else:
                    h.height += d * 0.3   # raised continental interiors

            # -----------------------------
            # 🔥 Fix global sea level
            # -----------------------------
            mean_height = np.mean([h.height for h in self.grid])
            for h in self.grid:
                h.height -= mean_height

            print(step)
        print("heights min/max:", min([h.height for h in self.grid]), max([h.height for h in self.grid]))

    def draw_plates(self, size=1):
        fig, ax = plt.subplots()

        hexes_array = np.array([[h.x, h.y, h.z] for h in self.grid])
        cx, cy = self.cube_to_pixel(hexes_array, size)

        # hex corner offsets
        angles = np.radians(np.arange(0, 360, 60) - 30)
        corner_offsets = np.stack(
            [np.cos(angles), np.sin(angles)],
            axis=1
        ) * size

        centers = np.stack([cx, cy], axis=1)
        polygons = (np.expand_dims(centers, 1) + corner_offsets).tolist()

        # --- generate colour per plate ---
        plate_colours = {
            plate.id: (
                random.random(),
                random.random(),
                random.random()
            )
            for plate in self.plates
        }

        facecolors = [
            plate_colours[getattr(h, "plate_id", 0)]
            for h in self.grid
        ]

        collection = PolyCollection(
            polygons,
            edgecolors="black",
            facecolors=facecolors,
            linewidths=0.15
        )

        ax.add_collection(collection)

        limit = size * (self.radius + 1) * 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal")
        ax.axis("off")

        fig.savefig("plates.png", bbox_inches="tight", dpi=900)
        return ax


 # extend your existing Grid class
    def draw_heightmap(self, size=1, colormap="terrain"):
        """
        Draw the hex grid colored by height values.
        """
        fig, ax = plt.subplots(figsize=(8, 8))

        # Convert hexes to numpy array
        hexes_array = np.array([[h.x, h.y, h.z] for h in self.grid])
        x, y = self.cube_to_pixel(hexes_array, size)

        # Precompute corner offsets
        angles = np.radians(np.arange(0, 360, 60) - 30)
        corner_offsets = np.stack([np.cos(angles), np.sin(angles)], axis=1) * size

        # Build polygons
        centers = np.stack([x, y], axis=1)
        polygons = (np.expand_dims(centers, 1) + corner_offsets).tolist()

        # --- Map height to color ---
        from matplotlib.colors import TwoSlopeNorm

        heights = np.array([h.height for h in self.grid])

        # Define sea level
        sea_level = 0

        norm = TwoSlopeNorm(
            vmin=heights.min(),
            vcenter=sea_level,
            vmax=heights.max()
        )

        import matplotlib.colors as mcolors

        cmap = mcolors.LinearSegmentedColormap.from_list(
            "terrain_with_blue_sea",
            [
                (0.0, "#0b1d51"),   # deep ocean
                (0.45, "#1f6fff"),  # shallow ocean
                (0.5, "#4ec5ff"),   # 🌊 sea level (exactly center)
                (0.55, "#3fa34d"),  # low land
                (0.7, "#8c6d31"),   # hills
                (1.0, "#ffffff")    # mountains
            ]
        )
        facecolors = [cmap(norm(h)) for h in heights]

        # Draw hex grid
        collection = PolyCollection(
            polygons,
            edgecolors="black",
            facecolors=facecolors,
            linewidths=0.1
        )
        ax.add_collection(collection)

        # Set limits
        limit = size * (self.radius + 1) * 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal")
        ax.axis("off")

        # optional: save to file
        fig.savefig("heightmap.png", bbox_inches="tight", dpi=900)
        return ax