import numpy as np, json
mmap = np.load('topdown_mmap.npy')
meta = json.load(open('voxel_meta.json'))
road=np.isin(mmap,[3,4,12,13])
fails = 0
for hx,hz,w,d,t in meta['houses']:
    dx=int(hx+w/2); zs=int(hz)
    if not road[max(0,dx-1):dx+2, max(0,zs-4):zs+5].any():
        if hx != 55:
            print(f"Failed non-farm house at {hx},{hz}.")
            fails += 1
            if fails > 5: break
