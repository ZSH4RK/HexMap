import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from hex import Hex
from grid_utils import generate_grid
from terrain import assign_values_mrv, fix_isolated_values, build_country_grid

from rendering import draw_hex_grid_side_by_side


# Deep Water, Water, Sand, Grass, Tree, Mountain, Peaks
# 100 = impassable
TAX = [100, 100, 2, 1, 2, 6, 9]
VALUE = [0, 0, 5, 10, 15, 5, 1]

BASE_ENERGY = 10
WATER_BASES = {1, 2}

def country_spread_steps(country_grid, num_countries=3):
    import random
    import math
    from collections import deque
    from grid_utils import get_neighbours

    land_tiles = [coords for coords, h in country_grid.items() if h.value == 1]

    if len(land_tiles) < num_countries:
        raise ValueError("Not enough land tiles.")

    starts_coords = random.sample(land_tiles, num_countries)
    country_ids = list(range(3, 3 + num_countries))

    starts = []
    for cid, start_coords in zip(country_ids, starts_coords):
        hex_tile = country_grid[start_coords]
        hex_tile.value = cid
        starts.append(hex_tile)
        yield country_grid  # show initial placement

    changed = True
    while changed:
        changed = False

        for cid in country_ids:

            owned_tiles = [h for h in country_grid.values() if h.value == cid]
            if not owned_tiles:
                continue

            energy = BASE_ENERGY + math.sqrt(len(owned_tiles))

            # ---- Coast detection ----
            coast_tiles = []
            for tile in owned_tiles:
                for n in get_neighbours(tile, country_grid):
                    if n.base in WATER_BASES:
                        coast_tiles.append(tile)
                        break

            ship_range = int(math.sqrt(len(coast_tiles))) if coast_tiles else 0

            while energy > 0:

                # ---------------- LAND OPTIONS ----------------
                land_frontier = []
                for tile in owned_tiles:
                    for n in get_neighbours(tile, country_grid):
                        if n.value == 1 and TAX[n.base - 1] <= energy:
                            land_frontier.append(n)

                best_land = None
                if land_frontier:
                    best_land = max(
                        land_frontier,
                        key=lambda n: VALUE[n.base - 1]
                    )

                # ---------------- NAVAL OPTIONS ----------------
                best_naval = None

                if ship_range > 0:
                    visited = set()
                    queue = deque()

                    for coast in coast_tiles:
                        for n in get_neighbours(coast, country_grid):
                            if n.base in WATER_BASES:
                                queue.append((n, 1))
                                visited.add(n)

                    while queue:
                        tile, dist = queue.popleft()
                        if dist > ship_range:
                            continue

                        for n in get_neighbours(tile, country_grid):
                            if n.value == 1 and TAX[n.base - 1] <= energy:
                                best_naval = n
                                queue.clear()
                                break

                            if n.base in WATER_BASES and n not in visited:
                                visited.add(n)
                                queue.append((n, dist + 1))

                        if best_naval:
                            break

                # ---------------- Decide ----------------
                candidates = [t for t in (best_land, best_naval) if t]

                if not candidates:
                    break

                best_tile = max(
                    candidates,
                    key=lambda n: VALUE[n.base - 1]
                )

                cost = TAX[best_tile.base - 1]

                energy -= cost
                best_tile.value = cid
                owned_tiles.append(best_tile)

                changed = True

                yield country_grid  # 🔥 animate each conquest

    return starts



def surround_pressure_steps(country_grid, country_ids, num_passes, starting_tiles):
    import random
    from grid_utils import get_neighbours

    protected = set(starting_tiles)

    for _ in range(num_passes):

        to_convert = []

        for tile in country_grid.values():

            if tile.value not in country_ids:
                continue

            if tile in protected:
                continue

            neighbours = get_neighbours(tile, country_grid)

            neighbour_countries = [
                n.value for n in neighbours
                if n.value in country_ids and n.value != tile.value
            ]

            if not neighbour_countries:
                continue

            # Count per country
            counts = {}
            for cid in neighbour_countries:
                counts[cid] = counts.get(cid, 0) + 1

            # Evaluate strongest pressure
            strongest = max(counts.items(), key=lambda x: x[1])
            cid, count = strongest

            if count < 4:
                continue

            if count == 4:
                chance = 0.25
            elif count == 5:
                chance = 0.5
            else:
                chance = 1.0

            if random.random() < chance:
                to_convert.append((tile, cid))

        # Apply simultaneously
        for tile, new_cid in to_convert:
            tile.value = new_cid
            yield country_grid  # 🔥 animate each conversion



COUNTRY_COLOURS = [
    'orange', 'purple', 'red', 'cyan',
    'magenta', 'yellow', 'lime', 'pink'
]

def print_country_summary(country_grid, country_ids):
    """
    Prints a formatted table of countries with their color, area, and total value,
    sorted by area (largest first).
    """

    results = []

    for index, cid in enumerate(country_ids):
        owned_tiles = [h for h in country_grid.values() if h.value == cid]

        area = len(owned_tiles)
        total_value = sum(VALUE[h.base - 1] for h in owned_tiles)

        colour = COUNTRY_COLOURS[index % len(COUNTRY_COLOURS)]

        results.append((colour, area, total_value))

    # Sort by area descending
    results.sort(key=lambda x: x[1], reverse=True)

    # Print formatted table
    print("\nCountry Summary (by Area)")
    print("-" * 40)
    print(f"{'Country':<12} | {'Area':<6} | {'Value':<6}")
    print("-" * 40)

    for colour, area, total_value in results:
        print(f"{colour:<12} | {area:<6} | {total_value:<6}")

    print("-" * 40)


def initialise_countries(country_grid, num_countries):
    import random

    land_tiles = [coords for coords, h in country_grid.items() if h.value == 1]

    starts_coords = random.sample(land_tiles, num_countries)
    country_ids = list(range(3, 3 + num_countries))

    starts = []
    for cid, start_coords in zip(country_ids, starts_coords):
        hex_tile = country_grid[start_coords]
        hex_tile.value = cid
        starts.append(hex_tile)

    return country_ids, starts


def country_simulation(country_grid, num_countries):
    """
    Unified generator that animates:
    1) Country expansion
    2) Surround pressure
    """

    # ---- Expansion Phase ----
    spread_gen = country_spread_steps(country_grid, num_countries)

    # Yield all expansion frames
    for frame in spread_gen:
        yield frame

    # ---- Surround Pressure Phase ----
    # Attempt to get starting tiles from spread generator (optional)
    starts = getattr(spread_gen, 'gi_frame', None)
    if starts and 'starts' in starts.f_locals:
        starts = starts.f_locals['starts']
    else:
        starts = []

    country_ids = list(range(3, 3 + num_countries))

    pressure_gen = surround_pressure_steps(
        country_grid,
        country_ids,
        num_countries,
        starts
    )

    for frame in pressure_gen:
        yield frame


def main():
    radius = 30

    # ---- Terrain Generation ----
    grid_list = generate_grid(radius, Hex)
    grid = {(h.x, h.y, h.z): h for h in grid_list}

    center_coords = (0, 0, 0)
    assign_values_mrv(grid, center_coords)
    fix_isolated_values(grid)

    # ---- Country Grid ----
    country_grid = build_country_grid(grid, Hex)
    num_countries = 8

    # ---- Animation Setup ----
    fig, axs = plt.subplots(1, 2, figsize=(24, 8))

    sim = country_simulation(country_grid, num_countries)

    def update(frame):
        draw_hex_grid_side_by_side(axs, grid, frame, [], size=1.0)
        return []

    ani = FuncAnimation(
        fig,
        update,
        frames=sim,
        interval=50,
        repeat=False,
        cache_frame_data=False  # best for generators
    )

    plt.tight_layout()

    # ---- Save as MP4 ----
    ani.save("country_simulation.gif", writer="pillow", fps=20)
    print("Saved animation as country_simulation.gif")


if __name__ == "__main__":
    main()
