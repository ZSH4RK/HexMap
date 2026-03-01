# CLAUDE.md

## Overview

**HexMap** is a Python‑based hexagon grid project that appears to implement a hex grid system, terrain handling, and rendering utilities.  
The repository contains multiple modules for game/map logic and visualization. The code is currently in early stage with no published releases. :contentReference[oaicite:1]{index=1}

## Architecture

### 📁 Core Modules

- **`main.py`** — Entry point that ties map/grid logic and rendering together.  
- **`hex.py`** — Core hexagon grid logic (coordinates, neighbors, layout math).  
- **`grid_utils.py`** — Utility functions related to grid generation or manipulation.  
- **`terrain.py`** — Terrain definitions and possibly terrain assignment/logic.  
- **`rendering.py`** — Drawing/rendering the map (likely using a graphics library).  
- **`countries.py`** — Possibly stores country data or helpers related to named regions. :contentReference[oaicite:2]{index=2}

### 🧠 Design Notes

- The project is entirely **Python‑based** and contains no compiled binaries or external assets in the main tree. :contentReference[oaicite:3]{index=3}  
- There is no package definition (`setup.py`/`pyproject.toml`) — this suggests it’s run as a local script/game project. :contentReference[oaicite:4]{index=4}
- The repository currently does **not contain a description or documentation** beyond the source files. :contentReference[oaicite:5]{index=5}

## Important Commands

Use a terminal to run the main application:

```sh
# run the core map application
python main.py