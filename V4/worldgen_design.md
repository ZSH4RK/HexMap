# World Generation — Design Notes

## Countries

### Approach: Hybrid Voronoi + Watershed

The recommended approach combines two techniques to produce geographically grounded, realistic-looking countries.

**Step 1 — Watershed pre-processing**

Before placing any countries, partition the land into natural regions by tracing drainage basins. Every land tile flows downhill to a valley or coast, and all tiles that drain to the same outlet form one natural region. Ridgelines become the dividing lines between regions automatically, since water on either side flows away from them. These regions become the building blocks for countries — one capital per region, seated in the valley floor.

**Step 2 — Voronoi expansion with terrain cost**

From each capital, expand outward using a priority queue (the same pattern already used in `generate_plates`). Terrain affects the expansion cost:

| Terrain crossing | Cost |
|---|---|
| Flat plains | Low |
| River | Moderate |
| Highland | High |
| Mountain range | Very high |
| Water | Impassable |

This means borders naturally form on ridgelines and along rivers, which matches how real political borders have historically emerged. Countries in valleys are cheap to expand across; mountains act as hard limits on how far a country can grow in a given direction.

**Additional rules to consider**

- Enforce a minimum country size so narrow slivers don't form between mountain ranges.
- Capitals should be placed on flat, low-elevation land within their region — historically cities form on navigable terrain.
- Countries that hit the coast should have their border snap to the coastline rather than continuing into the sea.

---

## Rivers

### Approach: Gradient Descent with Sink Handling

Rivers are generated as a post-processing step, after all map images have been saved. This keeps river generation from disturbing the underlying heightmap that biomes and contours depend on.

### Order of Operations

1. Generate elevation and save all map images
2. Pre-process elevation to fill sinks (see below)
3. Run river descent with merging logic
4. Optionally carve shallow valleys along river paths
5. Paint rivers onto the combined map as a final layer

### Source Placement

Pick N random seed points above a threshold elevation (e.g. 750m normalised). Multiple seeds on the same mountain range will naturally merge downstream, producing the tributary structure that makes rivers look realistic.

### The Descent

At each step, move to the neighbour with the lowest elevation. Add a small noise perturbation to the elevation lookup so the river meanders slightly on shallow slopes rather than cutting a perfectly straight line downhill. Not enough to make it go uphill — just enough to make it wander between neighbours of similar elevation.

### Flat Terrain and the Nearest-Water Bias

Pure gradient descent breaks on flat areas — if neighbours have identical elevations the algorithm gets stuck or makes arbitrary choices. Rather than biasing toward the map centre (which assumes ocean is always at the edges), bias toward the **nearest water tile**.

Pre-compute a distance-to-water map once using multi-source BFS, flooding outward simultaneously from all water tiles. This gives every land tile a distance value cheaply. When the descent encounters neighbours of equal elevation, prefer the one with a lower distance-to-water value. This is more accurate than a centre bias because it works correctly around inland seas, irregular coastlines and lakes that form later.

### River Merging

When a descending path reaches a tile that already carries a river, it joins rather than continuing as a separate thread. This produces natural tributary structure — thin streams high up, widening progressively as they collect others on the way to the sea.

### Carving vs Painting

| | Painting | Carving |
|---|---|---|
| What it does | Marks and colours river tiles blue | Lowers elevation slightly along the path |
| Appearance | River sits on top of terrain | River sits in a valley below surrounding terrain |
| Complexity | Simple | Requires regenerating map images afterwards |
| Downstream effects | None | Influences biomes, contours, country borders |

Carving is more realistic but should be done after all other map outputs are saved, since it modifies the heightmap.

---

## Lakes

### Approach: Basin Flooding

Lakes are not placed manually — they emerge naturally wherever the terrain traps water, using a process called basin flooding.

### When a Lake Forms

When a river's descent finds no downhill neighbour and cannot continue, trigger the lake flooding algorithm instead of terminating the river.

### The Flooding Algorithm

1. Track the connected region of tiles at or below the current water level — this is the basin.
2. Continuously check all tiles on the basin boundary for the lowest exit point (the spillover point).
3. Raise the virtual water level tile by tile until it reaches the spillover elevation.
4. Everything within the basin below the spillover elevation becomes lake.
5. The river continues its descent from the spillover point.

This naturally produces crater lakes, valley lakes and glacial lakes depending on the shape of the surrounding terrain.

### Merging Basins

As the water level rises during flooding, the basin can absorb adjacent depressions before finding an exit. This means one stuck river can produce a chain of connected lakes at different elevations, each spilling into the next lowest one — analogous to how the Great Lakes work.

### Interaction with the Nearest-Water Bias

Lakes generated this way become new water sources. A large inland lake is now closer to many land tiles than the distant ocean. The nearest-water BFS should therefore be run **after** lake placement, or updated dynamically as lakes form, so that rivers spawning near a lake bias toward it rather than toward the coast.

---

## Suggested Implementation Order

1. **Elevation** — already done
2. **Biomes** — already done  
3. **Rivers** — gradient descent with nearest-water bias and merging
4. **Lakes** — basin flooding triggered by stuck rivers
5. **Update nearest-water map** — re-run BFS now that lakes exist
6. **Countries** — watershed partitioning then Voronoi expansion with terrain cost