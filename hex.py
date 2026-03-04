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


