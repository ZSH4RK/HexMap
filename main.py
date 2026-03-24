from hex import Hex
from grid_utils import Grid
from terrain import assign_values_with_retry, add_volcanoes_np
import matplotlib
import numpy as np

matplotlib.use("Agg")

# Check assigned values

grid = Grid(radius=60, start_value=1)

grid.generate_plates(num_plates=15)
grid.draw_plates(size=1)

grid.simulate_plates(steps=100, uplift_rate=0.03, rift_rate=0.03, smoothing=0.3, ocean_base=-0.3, continental_base=0.3)
grid.draw_heightmap(size=1)
print('TADA!!!!!!')

