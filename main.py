from hex import Hex
from grid_utils import Grid
import matplotlib

matplotlib.use("Agg")

grid = Grid(radius=300, start_value=0)
grid.draw_hex_grid()

