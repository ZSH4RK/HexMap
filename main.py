import matplotlib.pyplot as plt
from hex import Hex
from grid_utils import generate_grid
from terrain import assign_values_mrv, fix_isolated_values, build_country_grid
from countries import country_spread
from rendering import draw_hex_grid_side_by_side

def main():
    radius = 30

    grid_list = generate_grid(radius, Hex)
    grid = {(h.x, h.y, h.z): h for h in grid_list}

    center_coords = (0, 0, 0)
    # After grid creation
    assign_values_mrv(grid, center_coords)
    fix_isolated_values(grid)


    country_grid = build_country_grid(grid, Hex)

    num_countries = 8
    country_grid, starts = country_spread(country_grid, num_countries)

    draw_hex_grid_side_by_side(grid, country_grid, starts, size=1.0)




if __name__ == "__main__":
    main()
