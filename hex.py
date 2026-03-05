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

    def get_neighbour(self, direction: Tuple[int, int, int]):
        return Hex(direction)
    
    def cube_to_axial(self):
        q = self.x
        r = self.r
        return (q,r)
    
    def axial_to_cube(self, a_coords: Tuple[int, int]):
        q, r = a_cords
        x = q
        y = r
        z = -q-r
        return (x, y, z)
    


# Calculate distances
def cube_subtract(a: Hex, b: Hex):
    return (a.x-b.x, a.y-b.y, a.z-b.z)

def cube_distance(a, b):
    vec = cube_subtract(a, b)
    return (abs(vec[1]), abs(vec[2]), abs(vec[3])) / 2
    


