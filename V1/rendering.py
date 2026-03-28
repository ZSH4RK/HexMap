import matplotlib.pyplot as plt
from grid_utils import cube_to_pixel, hex_corners

COLOURS = ['darkblue', 'blue', 'olivedrab', 'green', 'darkgreen', 'grey', 'white', 'brown']


def original_mapper(hex):
    if hex.value > 0:
        return COLOURS[hex.value - 1], str(hex.value)
    return 'white', '0'


def special_mapper(hex):
    if hex.value == 0:
        return 'blue', ''
    elif hex.value == 1:
        return 'white', ''
    elif hex.value == 2:
        return 'grey', ''
    elif hex.value >= 3:
        colors = ['orange', 'purple', 'red', 'cyan',
                  'magenta', 'yellow', 'lime', 'pink']
        index = (hex.value - 3) % len(colors)
        return colors[index], ''
    return 'white', ''


def draw_hex_grid(grid, size=1, value_mapper=None, ax=None, title=None):

    if ax is None:
        fig, ax = plt.subplots()

    iterable = grid.values() if isinstance(grid, dict) else grid

    for hex in iterable:
        cx, cy = cube_to_pixel(hex, size)
        corners = hex_corners(cx, cy, size)

        if value_mapper is None:
            color = COLOURS[hex.value - 1] if hex.value > 0 else 'white'
            label = str(hex.value)
        else:
            color, label = value_mapper(hex)

        polygon = plt.Polygon(corners, closed=True, edgecolor='black', facecolor=color)
        ax.add_patch(polygon)
        ax.text(cx, cy, label, ha='center', va='center', fontsize=10)

    ax.set_aspect('equal')
    ax.autoscale_view()
    ax.axis('off')

    if title:
        ax.set_title(title)

    return ax


def draw_hex_grid_side_by_side(axs, grid, country_grid, starts, size=1):

    # Clear both axes
    axs[0].clear()
    axs[1].clear()

    # --- Left: Original terrain ---
    draw_hex_grid(
        grid,
        size=size,
        value_mapper=original_mapper,
        ax=axs[0],
        title="Original Grid"
    )

    # --- Right: Countries ---
    ax_countries = axs[1]
    draw_hex_grid(
        country_grid,
        size=size,
        value_mapper=special_mapper,
        ax=ax_countries,
        title="Countries"
    )

    # Draw capital dots
    for hex in starts:
        cx, cy = cube_to_pixel(hex, size)
        ax_countries.plot(cx, cy, 'ko', markersize=8)



