import numpy as np
import matplotlib.pyplot as plt

# -----------------------------
# Perlin Noise Core
# -----------------------------

def fade(t):
    """Smooth interpolation curve."""
    return 6*t**5 - 15*t**4 + 10*t**3

def lerp(a, b, t):
    """Linear interpolation."""
    return a + t * (b - a)

def gradient(h, x, y):
    """Convert hash to gradient direction."""
    vectors = np.array([[0,1],[0,-1],[1,0],[-1,0]])
    g = vectors[h % 4]
    return g[...,0]*x + g[...,1]*y



# Permutation table
p = np.arange(256, dtype=int)
np.random.shuffle(p)
p = np.stack([p, p]).flatten()

def perlin(x, y):
    """2D Perlin noise."""
    
    xi = x.astype(int) & 255
    yi = y.astype(int) & 255

    xf = x - x.astype(int)
    yf = y - y.astype(int)

    u = fade(xf)
    v = fade(yf)

    aa = p[p[xi] + yi]
    ab = p[p[xi] + yi + 1]
    ba = p[p[xi + 1] + yi]
    bb = p[p[xi + 1] + yi + 1]

    x1 = lerp(
        gradient(aa, xf, yf),
        gradient(ba, xf-1, yf),
        u
    )

    x2 = lerp(
        gradient(ab, xf, yf-1),
        gradient(bb, xf-1, yf-1),
        u
    )

    return lerp(x1, x2, v)


# -----------------------------
# Multi-Octave (Fractal) Noise
# -----------------------------
def perlin_octaves(
    width,
    height,
    scale=6,
    octaves=6,
    persistence=0.5,
    lacunarity=2.0,
    base_frequency=0.2
):

    noise = np.zeros((height, width))

    amplitude = 1
    frequency = base_frequency
    max_amp = 0

    for octave in range(octaves):

        x = np.linspace(0, frequency, width, endpoint=False)
        y = np.linspace(0, frequency, height, endpoint=False)
        xv, yv = np.meshgrid(x, y)

        layer = perlin(xv * scale, yv * scale)

        # ---- NEW SLOPE-BASED DAMPING ----
        if octave > 0:
            slope = compute_slope(noise)
            slope = slope / (slope.max() + 1e-8)  # normalize to 0–1

            octave_weight = octave / (octaves - 1)
            strength = 2.5  # tweak this

            damping = (1 - slope) ** (strength * octave_weight)
            layer *= damping
        # --------------------------------

        noise += amplitude * layer

        max_amp += amplitude
        amplitude *= persistence
        frequency *= lacunarity
        print(f"octave: {octave}")

    noise /= max_amp
    noise = (noise - noise.min()) / (noise.max() - noise.min())

    return noise


def compute_slope(noise):
    dy, dx = np.gradient(noise)
    slope = np.sqrt(dx**2 + dy**2)
    return slope



# -----------------------------
# Visualization
# -----------------------------

def map_to_color(noise, water_level=0.4):
    h, w = noise.shape
    color = np.zeros((h, w, 3))

    water_mask = noise < water_level
    land_mask = ~water_mask

    # -----------------------------
    # WATER COLOURS (SUBTLE ZONES)
    # -----------------------------
    depth = noise / water_level

    # Deep ocean
    mask = water_mask & (depth < 0.25)
    color[mask] = [0.04, 0.10, 0.32]

    # Open ocean
    mask = water_mask & (depth >= 0.25) & (depth < 0.5)
    color[mask] = [0.05, 0.14, 0.38]

    # Shallow ocean
    mask = water_mask & (depth >= 0.5) & (depth < 0.75)
    color[mask] = [0.07, 0.18, 0.45]

    # Coastal water
    mask = water_mask & (depth >= 0.75)
    color[mask] = [0.10, 0.24, 0.52]

    # -----------------------------
    # LAND NORMALIZATION
    # -----------------------------
    land = np.zeros_like(noise)
    land[land_mask] = (
        noise[land_mask] - water_level
    ) / (1 - water_level)

    # Natural variation
    variation = (np.random.rand(h, w) - 0.5) * 0.05

    # -----------------------------
    # BEACH
    # -----------------------------
    mask = land_mask & (land < 0.06)
    color[mask] = [0.82, 0.78, 0.6]

    # DRY GRASS
    mask = land_mask & (land >= 0.06) & (land < 0.2)
    color[mask] = [0.65, 0.72, 0.35]

    # GRASSLAND
    mask = land_mask & (land >= 0.2) & (land < 0.45)
    color[mask] = [0.25, 0.6, 0.25]

    # FOREST
    mask = land_mask & (land >= 0.45) & (land < 0.7)
    color[mask] = [0.1, 0.45, 0.18]

    # ROCK
    mask = land_mask & (land >= 0.7) & (land < 0.86)
    color[mask] = [0.5, 0.5, 0.52]

    # HIGH MOUNTAIN
    mask = land_mask & (land >= 0.86) & (land < 0.92)
    color[mask] = [0.7, 0.7, 0.7]

    # SNOW
    mask = land_mask & (land >= 0.92)
    color[mask] = [1.0, 1.0, 1.0]

    # Apply subtle variation only to land
    for i in range(3):
        color[..., i] += variation * land_mask

    return np.clip(color, 0, 1)

noise = perlin_octaves(
    width=1000,
    height=1000,
    scale=20,
    octaves=20,
    persistence=0.5,
    lacunarity=2.0
)
noise = np.array(noise, dtype=np.float64)

img = map_to_color(noise, water_level=0.5)
plt.imshow(img)
plt.axis("off")
plt.savefig("perlin_noise.png", bbox_inches="tight")