from typing import Tuple


class Hex:

    def __init__(self, x, y, z, value=0, base=None):
        if x + y + z != 0:
            raise ValueError("x + y + z must equal 0")
        self.x = x
        self.y = y
        self.z = z
        self.value = value
        self.base = base if base is not None else value
        # Strart from the most left then clockwise
        self.neighbour_directions = [   (-1, 0, 1), (0, -1, 1),
                                        (1, -1, 0), (1, 0, -1),
                                        (0, 1, -1), (-1, 1, 0)]
    
    def __eq__(self, other):
        return isinstance(other, Hex) and (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def get_neighbour(self, direction: Tuple[int, int, int]):
        dx, dy, dz = direction
        return Hex(self.x + dx, self.y + dy, self.z + dz)
    
    def get_all_neighbours(self, grid_dict):
        """
        Returns all neighbours that exist in grid_dict (fast lookup).
        
        Parameters:
            grid_dict (dict): {(x, y, z): Hex}
        """
        neighbours = []
        for dx, dy, dz in self.neighbour_directions:
            coord = (self.x + dx, self.y + dy, self.z + dz)
            neighbour = grid_dict.get(coord)  # O(1) lookup
            if neighbour:
                neighbours.append(neighbour)
        return neighbours

    # Coordinate changes
    def cube_to_axial(self):
        q = self.x
        r = self.y
        return (q,r)
    
    def axial_to_cube(self, a_coords: Tuple[int, int]):
        q, r = a_coords
        x = q
        y = r
        z = -q-r
        return (x, y, z)
    


# Calculate distances
def cube_subtract(a: Hex, b: Hex):
    return (a.x-b.x, a.y-b.y, a.z-b.z)

def cube_distance(a: Hex, b: Hex):
    vec = cube_subtract(a, b)
    return (abs(vec[0]) + abs(vec[1]) + abs(vec[2])) // 2    

#Range
def movement_range(a: Hex, distance: int, grid):
    results = []
    for tile in grid:
        if cube_distance(a, tile) <= distance:
            results.append(tile)
    return results
