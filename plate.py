import random
import math
from collections import deque

class Plate:
    def __init__(self, id, type, start_coords):
        self.id = id
        # oceanic / continental
        self.plate_type = type
        self.start_coords = start_coords
        self.hexes = []

        self.direction = random.random() * 2 * math.pi
        self.magnitude = random.random()

        self.vector = (
            self.magnitude * math.cos(self.direction),
            self.magnitude * math.sin(self.direction)
        )