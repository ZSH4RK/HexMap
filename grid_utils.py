import math

DIRECTIONS = [
    (1, -1, 0),
    (1, 0, -1),
    (0, 1, -1),
    (-1, 1, 0),
    (-1, 0, 1),
    (0, -1, 1),
]


def cube_to_pixel(hex, size):
    px = size * math.sqrt(3) * (hex.x + hex.z / 2)
    py = size * 3 / 2 * hex.z
    return px, py


def hex_corners(cx, cy, size):
    corners = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        x = cx + size * math.cos(angle)
        y = cy + size * math.sin(angle)
        corners.append((x, y))
    return corners


def generate_grid(radius, Hex):
    grid = []
    for x in range(-radius, radius + 1):
        for y in range(max(-radius, -x - radius),
                       min(radius, -x + radius) + 1):
            z = -x - y
            grid.append(Hex(x, y, z))
    return grid


def get_neighbours(hex, grid):
    neighbours = []
    for dx, dy, dz in DIRECTIONS:
        coords = (hex.x + dx, hex.y + dy, hex.z + dz)
        if coords in grid:
            neighbours.append(grid[coords])
    return neighbours
