import numpy as np, json
mmap = np.load('topdown_mmap.npy')
meta = json.load(open('voxel_meta.json'))
road=np.isin(mmap,[3,4,12])
for hx,hz,w,d,t in meta['houses']:
    if hx==160 and hz==14:
        print(f"House at 160,14 is type {t}. Roof material expected: {[12, 18, 12, 7, 13][t]}")
        dx=int(hx+w/2); zs=int(hz)
        print("Mmap around door:")
        print(mmap[max(0,dx-1):dx+2, max(0,zs-4):zs+5])
