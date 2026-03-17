from hex import Hex
from grid_utils import Grid
from terrain import assign_values_with_retry, add_volcanoes_np
import matplotlib
import numpy as np

matplotlib.use("Agg")


seeds = [((90, -90, 0), 1),
         ((-50, 100, -50), 7),
         ((0, 0, 0), 5)]

grid = Grid(radius=100, start_value=7)
print('Grid!!!!!!!!!')
assign_values_with_retry(grid, seeds=seeds)
print('Values!!!!!!!!!')



# Add volcanoes with spacing and random chance
add_volcanoes_np(grid, min_center_spacing=20, trigger_chance=0.25)
print('Volcanoes!!!!!!!!!')

# Check assigned values
for h in grid.grid:
    print((h.x, h.y, h.z), h.value)

grid.draw_hex_grid()
print('TADA!!!!!!')

