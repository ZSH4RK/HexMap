import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import LinearSegmentedColormap
from scipy.ndimage import gaussian_filter

# ─────────────────────────────────────────
#  Permutation table  (4096 for low repeat)
# ─────────────────────────────────────────
_rng = np.random.default_rng(0)
_p_base = np.arange(4096, dtype=int)
_rng.shuffle(_p_base)
p = np.tile(_p_base, 2)          # global, mutated per noise layer


def reseed(seed):
    """Reshuffle the permutation table with a new seed."""
    global p
    rng = np.random.default_rng(seed)
    p_new = np.arange(4096, dtype=int)
    rng.shuffle(p_new)
    p[:] = np.tile(p_new, 2)


# ─────────────────────────────────────────
#  Perlin core
# ─────────────────────────────────────────

def fade(t):
    return 6*t**5 - 15*t**4 + 10*t**3


def lerp(a, b, t):
    return a + t * (b - a)


def gradient(h, x, y):
    vectors = np.array([
        [1,1],[-1,1],[1,-1],[-1,-1],
        [1,0],[-1,0],[0,1],[0,-1]
    ])
    g = vectors[h % 8]
    return g[..., 0]*x + g[..., 1]*y


def perlin(x, y):
    xi = x.astype(int) & 4095
    yi = y.astype(int) & 4095
    xf = x - x.astype(int)
    yf = y - y.astype(int)
    u  = fade(xf)
    v  = fade(yf)

    aa = p[p[xi]     + yi]
    ab = p[p[xi]     + yi + 1]
    ba = p[p[xi + 1] + yi]
    bb = p[p[xi + 1] + yi + 1]

    x1 = lerp(gradient(aa, xf,   yf),   gradient(ba, xf-1, yf),   u)
    x2 = lerp(gradient(ab, xf,   yf-1), gradient(bb, xf-1, yf-1), u)
    return lerp(x1, x2, v)


def compute_slope(noise):
    dy, dx = np.gradient(noise)
    return np.sqrt(dx**2 + dy**2)


def perlin_octaves(width, height, scale=6, octaves=6,
                   persistence=0.5, lacunarity=2.0, base_frequency=0.2):
    noise   = np.zeros((height, width))
    amp     = 1.0
    freq    = base_frequency
    max_amp = 0.0

    for octave in range(octaves):
        x  = np.linspace(0, freq, width,  endpoint=False)
        y  = np.linspace(0, freq, height, endpoint=False)
        xv, yv = np.meshgrid(x, y)
        layer = perlin(xv * scale, yv * scale)

        if octave > 0:
            slope  = compute_slope(noise)
            slope /= slope.max() + 1e-8
            weight  = octave / (octaves - 1)
            layer  *= (1 - slope) ** (2.5 * weight)

        noise   += amp * layer
        max_amp += amp
        amp     *= persistence
        freq    *= lacunarity

    noise /= max_amp
    noise  = (noise - noise.min()) / (noise.max() - noise.min())
    return noise


def make_noise_map(width, height, scale, octaves,
                   seed=None, persistence=0.5, lacunarity=2.0):
    reseed(seed if seed is not None else 0)
    return perlin_octaves(width, height, scale=scale, octaves=octaves,
                          persistence=persistence, lacunarity=lacunarity,
                          base_frequency=0.2)


# ─────────────────────────────────────────
#  Biome table & colours
# ─────────────────────────────────────────

# Rows = temperature bands 0(arctic)→4(tropical)
# Cols = moisture bands    0(arid)→4(wet)
BIOME_TABLE = [
    ["tundra",           "tundra",           "tundra",             "snow",             "snow"            ],
    ["tundra",           "shrubland",         "taiga",              "taiga",            "taiga"           ],
    ["desert",           "shrubland",         "grassland",          "temperate_forest", "temperate_forest"],
    ["desert",           "savanna",           "grassland",          "tropical_forest",  "wetland"         ],
    ["hot_desert",       "savanna",           "savanna",            "tropical_forest",  "rainforest"      ],
]

BIOME_COLOURS = {
    "tundra":            [0.76, 0.80, 0.78],
    "snow":              [0.97, 0.97, 1.00],
    "taiga":             [0.18, 0.42, 0.30],
    "shrubland":         [0.60, 0.65, 0.35],
    "desert":            [0.85, 0.78, 0.50],
    "hot_desert":        [0.90, 0.72, 0.35],
    "grassland":         [0.55, 0.73, 0.28],
    "savanna":           [0.75, 0.70, 0.25],
    "temperate_forest":  [0.13, 0.55, 0.20],
    "tropical_forest":   [0.05, 0.42, 0.12],
    "wetland":           [0.20, 0.50, 0.40],
    "rainforest":        [0.02, 0.32, 0.10],
}

TEMP_LABELS    = ["Arctic", "Cold", "Temperate", "Warm", "Tropical"]
MOISTURE_LABELS = ["Arid", "Semi-arid", "Moderate", "Humid", "Wet"]

WATER_LEVEL = 0.45


# ─────────────────────────────────────────
#  Water colour helper
# ─────────────────────────────────────────

def _apply_water(color, noise, water_mask):
    depth = noise / WATER_LEVEL
    color[water_mask & (depth < 0.25)]  = [0.04, 0.10, 0.32]
    color[water_mask & (depth >= 0.25) & (depth < 0.50)] = [0.05, 0.14, 0.38]
    color[water_mask & (depth >= 0.50) & (depth < 0.75)] = [0.07, 0.18, 0.45]
    color[water_mask & (depth >= 0.75)] = [0.10, 0.24, 0.52]


# ─────────────────────────────────────────
#  1.  ELEVATION MAP
# ─────────────────────────────────────────

def save_elevation_map(noise, filename="elevation.png", dpi=300):
    h, w   = noise.shape
    color  = np.zeros((h, w, 3))
    water_mask = noise < WATER_LEVEL
    land_mask  = ~water_mask

    _apply_water(color, noise, water_mask)

    # Normalise land height 0→1
    land_norm = np.zeros_like(noise)
    land_norm[land_mask] = (noise[land_mask] - WATER_LEVEL) / (1.0 - WATER_LEVEL)

    # Smooth OS-style elevation ramp
    LAND_STOPS = [
        (0.00, [0.82, 0.78, 0.60]),   # beach/lowland
        (0.05, [0.72, 0.80, 0.50]),   # coastal plain
        (0.18, [0.60, 0.75, 0.35]),   # lowland
        (0.35, [0.45, 0.65, 0.28]),   # upland
        (0.55, [0.32, 0.52, 0.22]),   # highland
        (0.70, [0.55, 0.50, 0.38]),   # moorland
        (0.82, [0.52, 0.47, 0.42]),   # rock
        (0.92, [0.70, 0.68, 0.68]),   # high rock
        (1.00, [1.00, 1.00, 1.00]),   # snow
    ]

    stops_t  = np.array([s[0] for s in LAND_STOPS])
    stops_c  = np.array([s[1] for s in LAND_STOPS])

    ys, xs = np.where(land_mask)
    vals   = land_norm[ys, xs]
    idx    = np.searchsorted(stops_t, vals, side='right').clip(1, len(stops_t)-1)
    lo, hi = stops_t[idx-1], stops_t[idx]
    t      = np.where(hi > lo, (vals - lo) / (hi - lo + 1e-9), 0.0)
    c_lo   = stops_c[idx-1]
    c_hi   = stops_c[idx]
    color[ys, xs] = c_lo + t[:, None] * (c_hi - c_lo)

    # Subtle variation
    variation = (np.random.default_rng(7).random((h, w)) - 0.5) * 0.03
    for i in range(3):
        color[..., i] += variation * land_mask

    fig, ax = plt.subplots(figsize=(12, 12), dpi=dpi)
    ax.imshow(np.clip(color, 0, 1), origin='upper', interpolation='bilinear')
    ax.axis('off')
    ax.set_title("Elevation", fontsize=14, fontweight='bold', pad=10)

    # Colorbar legend
    cmap_land = LinearSegmentedColormap.from_list(
        "land", [(s[0], s[1]) for s in LAND_STOPS])
    sm = plt.cm.ScalarMappable(cmap=cmap_land,
                               norm=mcolors.Normalize(vmin=0, vmax=1))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, orientation='vertical')
    cbar.set_label("Land elevation (normalised)", fontsize=9)
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_ticklabels(['Coast', 'Lowland', 'Highland', 'Mountain', 'Peak'])

    fig.savefig(filename, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print(f"Saved {filename}")


# ─────────────────────────────────────────
#  2.  BIOME MAP
# ─────────────────────────────────────────

def _biome_color_array(noise, moisture, temperature):
    h, w        = noise.shape
    color       = np.zeros((h, w, 3))
    water_mask  = noise < WATER_LEVEL
    land_mask   = ~water_mask

    _apply_water(color, noise, water_mask)

    land_norm = np.zeros_like(noise)
    land_norm[land_mask] = (noise[land_mask] - WATER_LEVEL) / (1.0 - WATER_LEVEL)

    # Beach strip
    beach_mask = land_mask & (land_norm < 0.04)
    color[beach_mask] = [0.82, 0.78, 0.60]

    biome_mask = land_mask & ~beach_mask
    t_band = np.clip((temperature * 5).astype(int), 0, 4)
    m_band = np.clip((moisture    * 5).astype(int), 0, 4)

    ys, xs = np.where(biome_mask)
    biome_colors = np.array([
        BIOME_COLOURS[BIOME_TABLE[t_band[y, x]][m_band[y, x]]]
        for y, x in zip(ys, xs)
    ])
    color[ys, xs] = biome_colors

    variation = (np.random.default_rng(3).random((h, w)) - 0.5) * 0.04
    for i in range(3):
        color[..., i] += variation * land_mask

    return np.clip(color, 0, 1)


def save_biome_map(noise, moisture, temperature,
                   filename="biomes.png", dpi=300):
    color = _biome_color_array(noise, moisture, temperature)
    fig, ax = plt.subplots(figsize=(12, 12), dpi=dpi)
    ax.imshow(color, origin='upper', interpolation='bilinear')
    ax.axis('off')
    ax.set_title("Biomes", fontsize=14, fontweight='bold', pad=10)
    fig.savefig(filename, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print(f"Saved {filename}")


# ─────────────────────────────────────────
#  3.  COMBINED: biomes + OS-style contours
# ─────────────────────────────────────────

def save_combined_map(noise, moisture, temperature,
                      filename="combined.png",
                      dpi=300,
                      contour_levels=20,
                      contour_alpha=0.45):
    """
    Biome colours as base, overlaid with thin contour lines like an OS map.
    Major contours every 5th line are darker/thicker.
    """
    h, w = noise.shape

    # Base biome image
    biome_color = _biome_color_array(noise, moisture, temperature)

    fig, ax = plt.subplots(figsize=(14, 14), dpi=dpi)
    ax.imshow(biome_color, origin='upper', extent=[0, w, h, 0],
              interpolation='bilinear', zorder=0)

    # ── Contour lines ──────────────────────────────────────────────
    # Only contour the land; mask water to NaN so lines don't appear there
    land_noise = np.where(noise >= WATER_LEVEL, noise, np.nan)

    # Smooth slightly so contours are cleaner
    land_smooth = gaussian_filter(land_noise, sigma=3)
    land_smooth = np.where(noise >= WATER_LEVEL, land_smooth, np.nan)

    # x/y grids matching imshow extent
    X = np.arange(w)
    Y = np.arange(h)

    # Remap noise to 0–1000m elevation for display
    # noise == WATER_LEVEL → 0m,  noise == 1.0 → 1000m
    elev = (land_smooth - WATER_LEVEL) / (1.0 - WATER_LEVEL) * 1000
    elev = np.where(noise >= WATER_LEVEL, elev, np.nan)

    # Contour levels in metres — minor every 50m, major every 250m
    minor_levels = np.arange(0, 1001, 50)
    major_levels = np.arange(0, 1001, 250)

    cs_minor = ax.contour(X, Y, elev,
                          levels=minor_levels,
                          colors=['#2d1a00'],
                          linewidths=0.35,
                          alpha=contour_alpha,
                          zorder=1)

    cs_major = ax.contour(X, Y, elev,
                          levels=major_levels,
                          colors=['#1a0e00'],
                          linewidths=0.9,
                          alpha=contour_alpha + 0.2,
                          zorder=2)

    ax.clabel(cs_major, inline=True, fontsize=5,
              fmt=lambda v: f"{v:.0f}m", colors='#1a0e00', zorder=3)

    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title("Biomes with Elevation Contours", fontsize=14,
                 fontweight='bold', pad=10)

    # ── Legend: biome swatches ──────────────────────────────────────
    biome_names = list(BIOME_COLOURS.keys())
    legend_patches = [
        plt.Rectangle((0, 0), 1, 1,
                       facecolor=BIOME_COLOURS[b],
                       edgecolor='#333', linewidth=0.5,
                       label=b.replace('_', ' ').title())
        for b in biome_names
    ]
    ax.legend(handles=legend_patches,
              loc='lower left', fontsize=6,
              ncol=2, framealpha=0.85,
              title="Biomes", title_fontsize=7)

    fig.savefig(filename, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print(f"Saved {filename}")


# ─────────────────────────────────────────
#  4.  BIOME LEGEND (swatch grid)
# ─────────────────────────────────────────

def save_biome_legend(filename="biome_legend.png", cell_px=100, dpi=150):
    rows = len(BIOME_TABLE)
    cols = len(BIOME_TABLE[0])
    img  = np.ones((rows * cell_px, cols * cell_px, 3))

    for t in range(rows):
        for m in range(cols):
            biome = BIOME_TABLE[t][m]
            c     = BIOME_COLOURS[biome]
            y0, y1 = t * cell_px, (t + 1) * cell_px
            x0, x1 = m * cell_px, (m + 1) * cell_px
            img[y0:y1, x0:x1] = c

    fig, ax = plt.subplots(figsize=(cols * 1.6, rows * 1.6), dpi=dpi)
    ax.imshow(img, origin='upper', aspect='auto')

    # Grid lines
    for i in range(cols + 1):
        ax.axvline(i * cell_px - 0.5, color='white', linewidth=1.2)
    for i in range(rows + 1):
        ax.axhline(i * cell_px - 0.5, color='white', linewidth=1.2)

    # Cell labels
    for t in range(rows):
        for m in range(cols):
            biome = BIOME_TABLE[t][m]
            cx = m * cell_px + cell_px // 2
            cy = t * cell_px + cell_px // 2
            bc = np.array(BIOME_COLOURS[biome])
            text_col = 'white' if bc.mean() < 0.5 else '#111'
            ax.text(cx, cy, biome.replace('_', '\n').title(),
                    ha='center', va='center', fontsize=7,
                    color=text_col, fontweight='bold')

    ax.set_xticks([m * cell_px + cell_px // 2 for m in range(cols)])
    ax.set_xticklabels(MOISTURE_LABELS, fontsize=10, fontweight='bold')
    ax.set_yticks([t * cell_px + cell_px // 2 for t in range(rows)])
    ax.set_yticklabels(TEMP_LABELS,    fontsize=10, fontweight='bold')
    ax.xaxis.set_label_position('top')
    ax.xaxis.tick_top()

    ax.set_xlabel("← Moisture →", fontsize=11, fontweight='bold', labelpad=8)
    ax.set_ylabel("← Temperature →", fontsize=11, fontweight='bold', labelpad=8)
    ax.set_title("Whittaker Biome Diagram", fontsize=13,
                 fontweight='bold', pad=28)

    fig.savefig(filename, bbox_inches='tight', dpi=dpi)
    plt.close(fig)
    print(f"Saved {filename}")


# ─────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────

if __name__ == "__main__":
    W, H = 1500, 1500   # reduce for faster dev; 5000x5000 for final

    # Random base seed so every run produces a different world
    base_seed = np.random.randint(0, 999999)
    print(f"World seed: {base_seed}  (set base_seed manually to reproduce a map)")

    print("Generating elevation noise...")
    reseed(base_seed)
    noise = perlin_octaves(W, H, scale=20, octaves=12,
                           persistence=0.5, lacunarity=2.0)
    noise = gaussian_filter(noise, sigma=1.0)

    # Normalise full range 0→1, then remap so max land = 1.0
    noise = (noise - noise.min()) / (noise.max() - noise.min())
    # Stretch land portion: water stays 0→WATER_LEVEL, land becomes WATER_LEVEL→1
    land_mask_raw = noise >= WATER_LEVEL
    land_max = noise[land_mask_raw].max()
    if land_max > WATER_LEVEL:
        noise[land_mask_raw] = WATER_LEVEL + (
            (noise[land_mask_raw] - WATER_LEVEL) / (land_max - WATER_LEVEL)
        ) * (1.0 - WATER_LEVEL)

    print("Generating moisture noise...")
    moisture = make_noise_map(W, H, scale=15, octaves=8, seed=base_seed + 1)

    print("Generating temperature noise...")
    temperature_raw = make_noise_map(W, H, scale=12, octaves=6, seed=base_seed + 2)

    # Mountains are colder
    altitude_penalty = np.clip((noise - WATER_LEVEL) * 2, 0, 1)
    temperature = np.clip(temperature_raw + 0.2 - altitude_penalty * 0.4, 0, 1)
    #                                  ^^^
    #                     push this up (warmer) or down (cooler), range roughly -0.5 to +0.5

    # Optional: latitude gradient (cold poles, warm equator)
    latitude_gradient = np.abs(np.linspace(-1, 1, H))[:, None] * 0.3
    temperature = np.clip(temperature - latitude_gradient, 0, 1)

    print("Saving elevation map...")
    save_elevation_map(noise, "elevation.png", dpi=200)

    print("Saving biome map...")
    save_biome_map(noise, moisture, temperature, "biomes.png", dpi=200)

    print("Saving combined map (biomes + contours)...")
    save_combined_map(noise, moisture, temperature, "combined.png",
                      dpi=200, contour_levels=20, contour_alpha=0.45)

    print("Saving biome legend...")
    save_biome_legend("biome_legend.png")

    print("\nDone. Files written:")
    print("  elevation.png  — terrain height ramp")
    print("  biomes.png     — biome colours")
    print("  combined.png   — biomes + OS-style contour lines")
    print("  biome_legend.png — Whittaker diagram swatch grid")