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
        elif base_value in [7, 8]:
            value = 2
        else:
            value = base_value

        country_grid[coords] = Hex(
            h.x, h.y, h.z,
            value=value,
            base=base_value
        )

    return country_grid

def cube_distance(a, b):
    return max(
        abs(a.x - b.x),
        abs(a.y - b.y),
        abs(a.z - b.z)
    )


import random

def can_place_volcano(center, grid):
    """
    Returns True if:
    - center.value == 6
    - there are 6 neighbours
    - at least one required pattern (0,2,4 or 1,3,5) is present among neighbours with value 7
    - no existing volcano tile (value == 8) is within 10 tiles of the center
    """
    if center.value != 6:
        return False

    neighbours = get_neighbours(center, grid)
    if len(neighbours) != 6:
        return False

    seven_indices = [i for i, n in enumerate(neighbours) if n.value == 7]

    # Required patterns (these indices must all be 7)
    required_patterns = [
        (0, 2, 4),
        (1, 3, 5)
    ]

    if not any(all(idx in seven_indices for idx in pattern) for pattern in required_patterns):
        return False

    # Distance rule: no existing volcano tile (value==8) within 10 tiles of the center
    for h in grid.values():
        if h.value == 8 and cube_distance(center, h) <= 10:
            return False

    return True


def add_volcanoes(grid, min_center_spacing=10, trigger_chance=0.1):
    """
    Scans grid for valid volcano centers and schedules conversions.
    Enforces:
    - Only convert center + the three neighbours matching the chosen pattern.
    - Extra 7s are allowed but not converted.
    - No overlapping scheduled groups.
    - Centers of scheduled volcanoes must be at least `min_center_spacing` tiles apart.
    """
    to_convert_groups = []
    scheduled_tile_ids = set()      # prevent overlapping groups
    scheduled_centers = []          # list of centers already scheduled (for spacing check)

    for center in grid.values():
        if not can_place_volcano(center, grid):
            continue

        neighbours = get_neighbours(center, grid)
        seven_indices = [i for i, n in enumerate(neighbours) if n.value == 7]

        # Determine which required patterns are contained
        patterns = []
        if all(i in seven_indices for i in (0, 2, 4)):
            patterns.append((0, 2, 4))
        if all(i in seven_indices for i in (1, 3, 5)):
            patterns.append((1, 3, 5))

        if not patterns:
            continue  # safety

        # If both patterns present, pick one (random or deterministic)
        chosen_pattern = random.choice(patterns)

        # Build the group: center + the three neighbours at chosen indices
        sevens = [neighbours[i] for i in chosen_pattern]
        group = [center] + sevens

        # Skip if any tile in this group is already scheduled (prevents overlap)
        if any(id(tile) in scheduled_tile_ids for tile in group):
            continue

        # Enforce spacing: center must be at least min_center_spacing from all scheduled centers
        too_close = False
        for scheduled_center in scheduled_centers:
            if cube_distance(center, scheduled_center) < min_center_spacing:
                too_close = True
                break
        if too_close:
            continue

        # 25% chance to trigger full 4-tile volcano (configurable via trigger_chance)
        if random.random() < trigger_chance:
            to_convert_groups.append(group)
            scheduled_centers.append(center)
            for tile in group:
                scheduled_tile_ids.add(id(tile))

    # Apply changes after scanning to avoid mutation issues
    for group in to_convert_groups:
        for tile in group:
            tile.value = 8
