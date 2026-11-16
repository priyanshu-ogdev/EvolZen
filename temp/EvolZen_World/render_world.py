import numpy as np
import matplotlib.pyplot as plt
import time

print("🏗️ Loading EvolZen Voxel World...")
t0 = time.time()
z = np.load('world_voxel_hires.npz')

# PBR Color Palette (R,G,B)
palette = {
    1: (0.2, 0.6, 0.2), 2: (0.4, 0.25, 0.1), 3: (0.5, 0.5, 0.5),
    4: (0.7, 0.2, 0.1), 5: (0.9, 0.85, 0.7), 6: (0.5, 0.3, 0.1),
    7: (0.1, 0.4, 0.8), 8: (0.6, 0.8, 0.9), 9: (0.1, 0.5, 0.1),
    10: (0.3, 0.15, 0.05), 11: (0.3, 0.3, 0.35), 12: (0.7, 0.7, 0.7),
    13: (0.8, 0.8, 0.85), 14: (1.0, 0.9, 0.5), 15: (0.6, 0.2, 0.2),
    16: (0.95, 0.95, 0.95), 17: (0.8, 0.1, 0.1), 18: (0.9, 0.4, 0.8),
    19: (0.9, 0.85, 0.6), 20: (0.1, 0.2, 0.6), 21: (0.1, 0.1, 0.1),
    22: (0.05, 0.05, 0.05), 23: (0.8, 0.7, 0.1)
}

all_x, all_y, all_z = [], [], []
all_c = []

print("⚡ Downsampling and extracting geometry (Optimized for M3 Air)...")
for key in z.files:
    chunk = z[key]
    cx, cy, cz = map(int, key[1:].split('_'))
    
    # DOWNSAMPLE: Take every 4th voxel in X/Z (1m res), every 2nd in Y (0.5m res)
    # This reduces 32x32x32 to 8x16x8 = 1024 voxels per chunk max.
    ds_chunk = chunk[::4, ::2, ::4]
    
    xs, ys, zs = np.nonzero(ds_chunk)
    if len(xs) == 0: continue
        
    mats = ds_chunk[xs, ys, zs]
    
    # Calculate global coordinates in meters
    gx = (cx * 32 + xs * 4) * 0.25
    gy = (cy * 32 + ys * 2) * 0.25
    gz = (cz * 32 + zs * 4) * 0.25
    
    all_x.extend(gx)
    all_y.extend(gy)
    all_z.extend(gz)
    
    # Map colors
    for m in mats:
        all_c.append(palette.get(int(m), (0.5, 0.5, 0.5)))

print(f"✅ Extracted {len(all_x):,} render points in {time.time()-t0:.1f}s")
print("🎨 Rendering 3D Preview (This may take 10-20 seconds)...")

# Create a high-res Dark Mode canvas
fig = plt.figure(figsize=(16, 12), facecolor='black')
ax = fig.add_subplot(111, projection='3d', facecolor='black')

# Scatter plot (much faster than voxels for large datasets)
ax.scatter(all_x, all_z, all_y, c=all_c, marker='s', s=15, alpha=1.0, edgecolors='none')

ax.set_xlabel('X (East)', color='white')
ax.set_ylabel('Z (South)', color='white')
ax.set_zlabel('Y (Up)', color='white')
ax.set_title('EvolZen 1x1km Parallel Universe (1m Resolution Preview)', color='white', fontsize=16)

ax.set_xlim(0, 1000)
ax.set_ylim(0, 1000)
ax.set_zlim(0, 40)

# Dark mode styling
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.tick_params(colors='white')

plt.tight_layout()
out_file = "evolzen_world_preview.png"
plt.savefig(out_file, dpi=200, facecolor='black')
print(f"🏆 Saved high-res render: {out_file}")
print("Open this image in your Mac Preview app to see your world!")
