import numpy as np
import matplotlib.pyplot as plt
import time

print("🗺️ Generating Top-Down Orthographic City Map...")
t0 = time.time()
z = np.load('world_voxel_hires.npz')

# 1km x 1km map at 1m resolution (1000x1000 pixels)
MAP_RES = 1000
height_map = np.full((MAP_RES, MAP_RES), -1, dtype=np.int16)
mat_map = np.zeros((MAP_RES, MAP_RES), dtype=np.uint8)

# 2D Color Palette (Optimized for top-down visibility. Water mapped to Grass as requested)
palette = {
    0: (0.15, 0.15, 0.15), # AIR / Background
    1: (0.35, 0.65, 0.25), # GRASS
    2: (0.45, 0.30, 0.15), # DIRT
    3: (0.50, 0.50, 0.50), # PATH (Roads)
    4: (0.40, 0.40, 0.40), # WALK
    5: (0.75, 0.30, 0.20), # BRICK
    6: (0.85, 0.80, 0.65), # VINYL
    7: (0.55, 0.35, 0.15), # WOOD
    8: (0.35, 0.65, 0.25), # WATER (Mapped to GRASS)
    9: (0.55, 0.90, 0.80), # GLASS = mint
    10: (0.15, 0.55, 0.15),# LEAF (Trees/Parks)
    11: (0.30, 0.15, 0.05),# TRUNK
    12: (0.40, 0.40, 0.45),# ROOF
    13: (0.65, 0.65, 0.65),# CONC
    14: (0.75, 0.75, 0.80),# METAL
    15: (1.00, 0.90, 0.50),# LAMP
    16: (0.80, 0.20, 0.20),# FAB
    17: (0.95, 0.95, 0.95),# WHITE (Hospital)
    18: (0.95, 0.15, 0.15),# RED (Hospital Cross)
    19: (0.90, 0.40, 0.80),# FLOWER
    20: (0.90, 0.85, 0.60),# SAND
    21: (0.20, 0.30, 0.70),# CAR
    22: (0.10, 0.10, 0.10),# TIRE
    23: (0.80, 0.70, 0.10) # TV/CROPS
}

print("⚡ Extracting surface topology (Raycasting Y-axis)...")
for key in z.files:
    chunk = z[key]
    cx, cy, cz = map(int, key[1:].split('_'))
    
    xs, ys, zs = np.nonzero(chunk)
    if len(xs) == 0: continue
    
    global_y = cy * 32 + ys
    global_x = cx * 32 + xs
    global_z = cz * 32 + zs
    mats = chunk[xs, ys, zs]
    
    # Downsample to 1m resolution (divide by 4)
    map_x = global_x // 4
    map_z = global_z // 4
    
    for i in range(len(map_x)):
        mx, mz, my, m = map_x[i], map_z[i], global_y[i], mats[i]
        if 0 <= mx < MAP_RES and 0 <= mz < MAP_RES:
            if my > height_map[mx, mz]:
                height_map[mx, mz] = my
                mat_map[mx, mz] = m

print("🎨 Rendering 2D Orthographic Map...")
img = np.zeros((MAP_RES, MAP_RES, 3), dtype=np.float32)
for mat_id, color in palette.items():
    mask = (mat_map == mat_id)
    img[mask] = color

fig, ax = plt.subplots(figsize=(12, 12), dpi=150)
ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=[0, 1000, 0, 1000])
ax.set_title('EvolZen 1x1km City Layout (Top-Down Surface Map)', color='white', fontsize=18, pad=20, fontweight='bold')
ax.set_xlabel('X (East) - 1000m', color='white', fontsize=12)
ax.set_ylabel('Z (South) - 1000m', color='white', fontsize=12)
ax.set_facecolor('black')
fig.patch.set_facecolor('black')
ax.tick_params(colors='white')

plt.tight_layout()
out_file = "world_topdown_map.png"
plt.savefig(out_file, dpi=150, facecolor='black')
print(f"🏆 Saved high-res 2D map: {out_file} ({time.time()-t0:.1f}s)")
print("Open this image. You will see the exact road grid, hospital, farms, and house footprints.")
