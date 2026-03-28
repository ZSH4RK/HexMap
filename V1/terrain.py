import random
from grid_utils import Grid
from hex import Hex
import numpy as np
from collections import deque

VALUES = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
NUM_VALUES = len(VALUES)

ALL_VALUES = np.arange(1, NUM_VALUES + 1)


def reset_grid_values(grid):
    """
    Reset grid values so generation can retry cleanly.
    """
    for h in grid.grid:
        h.value = 0


def assign_values_with_retry(grid, seeds=None, max_attempts=25, verbose=True):
    """
    Runs assign_values_with_seeds with automatic retries if
    a contradiction occurs.
    """
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            reset_grid_values(grid)

            if verbose:
                print(f"Generation attempt {attempt}/{max_attempts}")

            assign_values_with_seeds(grid, seeds)

            if verbose:
                print("Grid generation succeeded")

            return True

        except Exception as e:
            last_error = e
            if verbose:
                print(f"Retrying due to: {e}")

    raise last_error


def allowed_values_from_used(used):
    used = used[used != 0]

    if used.size == 0:
        return VALUES

    diff_ok = np.abs(VALUES[:, None] - used[None, :]) <= 1
    valid_mask = np.all(diff_ok, axis=1)

    return VALUES[valid_mask]


def weighted_choice_fast(options, neighbour_values):
    if options.size == 0:
        return None

    weights = np.array([
        np.sum(neighbour_values == v) * 0.5 + 1
        for v in options
    ])

    probabilities = weights / weights.sum()
    return np.random.choice(options, p=probabilities)


def build_indexed_grid(grid):
    hex_list = list(grid.grid_dict.values())

    index_of = {(h.x, h.y, h.z): i for i, h in enumerate(hex_list)}

    directions = [
        (1,-1,0),(1,0,-1),(0,1,-1),
        (-1,1,0),(-1,0,1),(0,-1,1)
    ]

    neighbours = []

    for h in hex_list:
        n_idx = []
        for dx,dy,dz in directions:
            key = (h.x+dx, h.y+dy, h.z+dz)
            if key in index_of:
                n_idx.append(index_of[key])
        neighbours.append(np.array(n_idx, dtype=np.int32))

    return hex_list, neighbours


def assign_values_with_seeds(grid, seeds=None):
    hex_list, neighbours = build_indexed_grid(grid)
    n = len(hex_list)

    domains = np.ones((n, NUM_VALUES), dtype=bool)
    values = np.zeros(n, dtype=np.int16)
    queue = deque()

    VALUES = np.arange(1, NUM_VALUES + 1)
    COMPAT = np.abs(VALUES[:, None] - VALUES[None, :]) <= 1


    def collapse_to_value(idx, value):
        value_index = value - 1
        domains[idx][:] = False
        domains[idx][value_index] = True
        values[idx] = value
        hex_list[idx].value = value
        queue.append(idx)


    def collapse(idx):
        options = np.where(domains[idx])[0]

        if options.size == 0:
            raise Exception("No valid assignment")

        neighbour_vals = values[neighbours[idx]]
        neighbour_vals = neighbour_vals[neighbour_vals != 0]

        if neighbour_vals.size == 0:
            chosen_index = np.random.choice(options)
        else:
            option_values = options + 1
            chosen_value = weighted_choice_fast(option_values, neighbour_vals)
            chosen_index = chosen_value - 1

        collapse_to_value(idx, chosen_index + 1)


    def propagate():
        while queue:
            src = queue.popleft()
            src_domain = domains[src]

            for nb in neighbours[src]:

                if values[nb] != 0:
                    continue

                before = domains[nb].copy()

                allowed = np.any(COMPAT[src_domain], axis=0)

                domains[nb] &= allowed

                if not np.any(domains[nb]):
                    raise Exception("No valid assignment")

                if not np.array_equal(before, domains[nb]):
                    queue.append(nb)


    frontiers = []

    if seeds is not None:
        coord_lookup = {(h.x, h.y, h.z): i for i, h in enumerate(hex_list)}

        for (x, y, z), value in seeds:
            idx = coord_lookup.get((x, y, z))
            if idx is not None:
                collapse_to_value(idx, value)
                frontiers.append(deque([idx]))


    while frontiers:
        for frontier in list(frontiers):

            if not frontier:
                frontiers.remove(frontier)
                continue

            src = frontier.popleft()

            for nb in neighbours[src]:

                if values[nb] != 0:
                    continue

                collapse(nb)
                propagate()

                frontier.append(nb)


    while True:

        unassigned = (values == 0)

        if not np.any(unassigned):
            break

        sizes = domains.sum(axis=1)
        sizes[~unassigned] = 9999

        # Random tie-breaking entropy (important improvement)
        min_size = np.min(sizes)
        candidates = np.where(sizes == min_size)[0]
        idx = np.random.choice(candidates)

        collapse(idx)
        propagate()


# -------------------------
# Fix isolated low-value clusters
# -------------------------
def fix_isolated_values_np(grid):

    hex_list = grid.grid
    values = np.array([h.value for h in hex_list])

    visited = np.zeros(len(hex_list), dtype=bool)
    to_change = []

    for i, h in enumerate(hex_list):

        if values[i] not in [1,2] or visited[i]:
            continue

        stack = [i]
        group_idx = []

        while stack:

            idx = stack.pop()

            if visited[idx]:
                continue

            visited[idx] = True

            if values[idx] == values[i]:

                group_idx.append(idx)

                for n in hex_list[idx].get_all_neighbours(grid.grid_dict):

                    n_idx = grid.grid.index(n)

                    if not visited[n_idx] and values[n_idx] == values[i]:
                        stack.append(n_idx)

        if len(group_idx) <= 2:

            new_val = 2 if values[i] == 1 else 3

            to_change.extend([(idx,new_val) for idx in group_idx])


    for idx,new_val in to_change:
        hex_list[idx].value = new_val
        values[idx] = new_val


# -------------------------
# Country map
# -------------------------
def build_country_grid_np(grid, Hex):

    hex_list = grid.grid
    values = np.array([h.value for h in hex_list])

    country_values = np.zeros_like(values)

    country_values[(values >=3)&(values<=6)] = 1
    country_values[values >=7] = 2

    country_grid = {}

    for i,h in enumerate(hex_list):

        country_grid[(h.x,h.y,h.z)] = Hex(
            h.x,
            h.y,
            h.z,
            value=int(country_values[i]),
            base=values[i]
        )

    return country_grid


# -------------------------
# Cube distance
# -------------------------
def cube_distance_np(a_coords,b_coords):
    return np.max(np.abs(a_coords - b_coords),axis=-1)


# -------------------------
# Volcano placement
# -------------------------
def can_place_volcano_np(center,grid,min_distance=10):

    if center.value != 6:
        return False

    neighbours = center.get_all_neighbours(grid.grid_dict)

    if len(neighbours) != 6:
        return False

    neighbour_values = np.array([n.value for n in neighbours])
    seven_indices = np.where(neighbour_values == 7)[0]

    patterns=[np.array([0,2,4]),np.array([1,3,5])]

    if not any(np.all(np.isin(pat,seven_indices)) for pat in patterns):
        return False

    center_coords=np.array([center.x,center.y,center.z])
    volcano_coords=np.array([[h.x,h.y,h.z] for h in grid.grid if h.value==8])

    if volcano_coords.size>0:
        distances=np.max(np.abs(volcano_coords-center_coords),axis=1)

        if np.any(distances<=min_distance):
            return False

    return True


def add_volcanoes_np(grid,min_center_spacing=10,trigger_chance=0.25):

    hex_list=grid.grid

    scheduled_ids=set()
    scheduled_centers=[]
    to_convert_groups=[]

    for idx,center in enumerate(hex_list):

        if center.value not in [8,9]:
            continue

        neighbours=np.array(center.get_all_neighbours(grid.grid_dict))

        if len(neighbours)!=6:
            continue

        neighbour_values=np.array([n.value for n in neighbours])

        seven_indices=np.where((neighbour_values==10)|(neighbour_values==9))[0]

        patterns=[]

        if set([0,2,4]).issubset(seven_indices):
            patterns.append((0,2,4))

        if set([1,3,5]).issubset(seven_indices):
            patterns.append((1,3,5))

        if not patterns:
            continue

        chosen_pattern=random.choice(patterns)

        group=[center]+[neighbours[i] for i in chosen_pattern]

        if any(id(h) in scheduled_ids for h in group):
            continue

        if scheduled_centers:

            center_coords=np.array([center.x,center.y,center.z])
            sched_coords=np.array([[c.x,c.y,c.z] for c in scheduled_centers])

            distances=cube_distance_np(sched_coords,center_coords)

            if np.any(distances<min_center_spacing):
                continue

        if random.random()<trigger_chance:

            to_convert_groups.append(group)
            scheduled_centers.append(center)

            for h in group:
                scheduled_ids.add(id(h))

    for group in to_convert_groups:
        for h in group:
            h.value=0