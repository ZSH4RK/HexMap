import random
from grid_utils import get_neighbours


VALUES = [1, 2, 3, 4, 5, 6, 7]


def allowed_values(hex, grid):
    neighbours = get_neighbours(hex, grid)
    assigned = [n.value for n in neighbours if n.value != 0]

    if not assigned:
        return VALUES

    possible = []
    for candidate in VALUES:
        if all(abs(candidate - v) <= 1 for v in assigned):
            possible.append(candidate)

    return possible


def weighted_choice(hex, grid, possible_values):
    neighbours = get_neighbours(hex, grid)
    weights = []

    for value in possible_values:
        count = sum(1 for n in neighbours if n.value == value)
        weights.append(count * 0.5 + 1)

    return random.choices(possible_values, weights=weights)[0]


def assign_values_mrv(grid, center_coords):
    grid[center_coords].value = 5

    while True:
        unassigned = [h for h in grid.values() if h.value == 0]
        if not unassigned:
            break

        best_tile = None
        best_options = None
        smallest_option_count = float('inf')

        for tile in unassigned:
            options = allowed_values(tile, grid)
            if len(options) == 0:
                raise Exception("No valid assignment possible")

            if len(options) < smallest_option_count:
                smallest_option_count = len(options)
                best_tile = tile
                best_options = options

        chosen_value = weighted_choice(best_tile, grid, best_options)
        best_tile.value = chosen_value


def fix_isolated_values(grid):

    def get_connected_group(start_hex, value, visited):
        stack = [start_hex]
        group = []

        while stack:
            h = stack.pop()
            if h in visited:
                continue
            visited.add(h)
            if h.value == value:
                group.append(h)
                for n in get_neighbours(h, grid):
                    if n not in visited and n.value == value:
                        stack.append(n)
        return group

    visited = set()
    to_change = []

    for h in grid.values():
        if h.value in [1, 2] and h not in visited:
            group = get_connected_group(h, h.value, visited)
            if len(group) <= 2:
                new_value = 2 if h.value == 1 else 3
                to_change.extend([(g, new_value) for g in group])

    for h, new_value in to_change:
        h.value = new_value


def build_country_grid(grid, Hex):
    country_grid = {}

    for coords, h in grid.items():
        base_value = h.value

        if base_value in [1, 2]:
            value = 0
        elif 3 <= base_value <= 6:
            value = 1
        elif base_value in [7]:
            value = 2
        else:
            value = base_value

        country_grid[coords] = Hex(
            h.x, h.y, h.z,
            value=value,
            base=base_value
        )

    return country_grid

