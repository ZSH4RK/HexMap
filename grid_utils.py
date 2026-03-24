import math
import numpy as np
import random
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from hex import Hex
from plate import Plate
from opensimplex import OpenSimplex

class Grid:
    def __init__(self, radius: int, start_value: int):
        self.radius = radius
        self.start_value = start_value
        self.grid = self.generate_grid()
        self.grid_dict = {(h.x, h.y, h.z): h for h in self.grid}
        self.noise = OpenSimplex(seed=42)
        

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

    def fractal_noise(self, x, z, octaves=5, persistence=0.5, lacunarity=2.0):
        value = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_amp = 0.0

        for _ in range(octaves):
            n = self.noise.noise2(
                x * frequency,
                z * frequency
            )

            value += n * amplitude
            max_amp += amplitude

            amplitude *= persistence
            frequency *= lacunarity

        return value / (max_amp + 1e-6)
    def generate_base_heightmap(self, scale=0.05, octaves=5):
        for h in self.grid:
            n = self.fractal_noise(
                h.x * scale,
                h.z * scale,
                octaves=octaves
            )

            # --- softer continent falloff ---
            distance = math.sqrt(h.x ** 2 + h.z ** 2) / self.radius
            falloff = max(0, 1 - distance ** 2)  # smoother, less harsh

            # blend noise + continent shape
            h.height = n * 0.8 + falloff * 0.2

        # --- normalize to -1 → 1 ---
        heights = [h.height for h in self.grid]
        min_h, max_h = min(heights), max(heights)

        for h in self.grid:
            h.height = (h.height - min_h) / (max_h - min_h + 1e-6)
            h.height = h.height * 2 - 1

    def simulate_plates(self, steps=10):
        plate_vectors = {
            plate.id: plate.vector
            for plate in self.plates
        }

        directions = [
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (-1, 1, 0), (-1, 0, 1), (0, -1, 1)
        ]

        # --- initialise heights ---


        # =========================
        # MAIN TIME LOOP
        # =========================
        for step in range(steps):
            # --- accumulate changes separately (important!) ---
            height_delta = {h: 0.0 for h in self.grid}

            for h in self.grid:
                for dx, dy, dz in directions:
                    neighbor_coords = (h.x + dx, h.y + dy, h.z + dz)

                    if neighbor_coords not in self.grid_dict:
                        continue

                    n = self.grid_dict[neighbor_coords]

                    if h.plate_id == n.plate_id:
                        continue

                    v1 = plate_vectors[h.plate_id]
                    v2 = plate_vectors[n.plate_id]

                    relative = (v1[0] - v2[0], v1[1] - v2[1])

                    dx_world = n.x - h.x
                    dz_world = n.z - h.z

                    length = math.sqrt(dx_world ** 2 + dz_world ** 2)
                    if length == 0:
                        continue

                    normal = (dx_world / length, dz_world / length)

                    collision_strength = (
                            relative[0] * normal[0] +
                            relative[1] * normal[1]
                    )

                    plate1 = self.plates[h.plate_id]
                    plate2 = self.plates[n.plate_id]

                    # --- base effect ---
                    if collision_strength > 0:
                        height_delta[h] += collision_strength * 0.3
                    else:
                        height_delta[h] += collision_strength

                    # --- plate type effects ---
                    if collision_strength > 0:
                        if plate1.plate_type == "continental" and plate2.plate_type == "continental":
                            height_delta[h] += collision_strength * 0.5

                        elif plate1.plate_type == "oceanic":
                            height_delta[h] -= collision_strength * 0.2

            # --- apply accumulated changes ---
            for h in self.grid:
                h.height += height_delta[h]

            # =========================
            # SMOOTH EACH STEP
            # =========================
            new_heights = {}

            for h in self.grid:
                total = h.height
                count = 1

                for dx, dy, dz in directions:
                    coords = (h.x + dx, h.y + dy, h.z + dz)
                    if coords in self.grid_dict:
                        total += self.grid_dict[coords].height
                        count += 1

                new_heights[h] = total / count

            for h in self.grid:
                h.height = new_heights[h]

            print(step)

        # =========================
        # NORMALIZE ONCE AT END
        # =========================
        heights = [h.height for h in self.grid]
        min_h, max_h = min(heights), max(heights)

        for h in self.grid:
            h.height = (h.height - min_h) / (max_h - min_h + 1e-6)
            h.height = h.height * 2 - 1

    def draw_fractal_noise(self, size=1, scale=0.05, octaves=5):
        fig, ax = plt.subplots()

        hexes_array = np.array([[h.x, h.y, h.z] for h in self.grid])
        cx, cy = self.cube_to_pixel(hexes_array, size)

        angles = np.radians(np.arange(0, 360, 60) - 30)
        corner_offsets = np.stack(
            [np.cos(angles), np.sin(angles)],
            axis=1
        ) * size

        centers = np.stack([cx, cy], axis=1)
        polygons = (np.expand_dims(centers, 1) + corner_offsets).tolist()

        # --- fractal noise ---
        values = np.array([
            self.fractal_noise(h.x * scale, h.z * scale, octaves=octaves)
            for h in self.grid
        ])

        # Normalize 0–1
        min_v = values.min()
        max_v = values.max()
        norm_values = (values - min_v) / (max_v - min_v + 1e-6)

        # Grayscale colormap
        cmap = plt.get_cmap("gray")
        facecolors = cmap(norm_values)

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

        fig.savefig("fractalnoise.png", bbox_inches="tight", dpi=900)
        return ax

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
        fig, ax = plt.subplots()

        # Convert hexes to numpy array
        hexes_array = np.array([[h.x, h.y, h.z] for h in self.grid])
        cx, cy = self.cube_to_pixel(hexes_array, size)

        # Hex corner offsets
        angles = np.radians(np.arange(0, 360, 60) - 30)
        corner_offsets = np.stack(
            [np.cos(angles), np.sin(angles)],
            axis=1
        ) * size

        # Build polygons
        centers = np.stack([cx, cy], axis=1)
        polygons = (np.expand_dims(centers, 1) + corner_offsets).tolist()

        # --- HEIGHT → COLOUR ---
        heights = np.array([h.height for h in self.grid])

        # Normalize to 0–1 for colormap
        min_h = heights.min()
        max_h = heights.max()
        norm_heights = (heights - min_h) / (max_h - min_h + 1e-6)
        norm_heights **= 1.2

        cmap = plt.get_cmap(colormap)
        facecolors = cmap(norm_heights)

        # Create collection
        collection = PolyCollection(
            polygons,
            edgecolors="black",
            facecolors=facecolors,
            linewidths=0.1
        )

        ax.add_collection(collection)

        # Set bounds
        limit = size * (self.radius + 1) * 2
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.set_aspect("equal")
        ax.axis("off")

        # Optional: colorbar (very useful for debugging)
        sm = plt.cm.ScalarMappable(cmap=cmap)
        sm.set_array(norm_heights)
        plt.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)

        fig.savefig("heightmap.png", bbox_inches="tight", dpi=900)
        return ax