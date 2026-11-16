import numpy as np, json, collections
z = np.load('world_voxel_hires.npz'); meta = json.load(open('voxel_meta.json'))
keys = list(z.files)
print(f"CHUNKS: {len(keys)}")

# 1) SOURCE material histogram (before any render remap)
hist = np.zeros(24, np.int64)
for k in keys: hist += np.bincount(z[k].ravel(), minlength=24)
N = ['AIR','GRASS','DIRT','PATH','WALK','BRICK','VINYL','WOOD','WATER','GLASS',
     'LEAF','TRUNK','ROOF','CONC','METAL','LAMP','FAB','WHITE','RED','FLOWER',
     'SAND','CAR','TIRE','TV']
for i,n in enumerate(N):
    if hist[i]: print(f"  {i:2d} {n:<6} {hist[i]:>10,}")
print(f"WATER(8)==0: {hist[8]==0}")

# 2) Top-surface map (data axes: mmap[X_east, Z_south])
MAP=1000; hmap=np.full((MAP,MAP),-1,np.int16); mmap=np.zeros((MAP,MAP),np.uint8)
for k in keys:
    a=z[k]; cx,cy,cz=map(int,k[1:].split('_'))
    xs,ys,zs=np.nonzero(a)
    if len(xs)==0: continue
    gx,gy,gz=cx*32+xs,cy*32+ys,cz*32+zs; mx,mz=gx//4,gz//4
    for i in range(len(mx)):
        if gy[i]>hmap[mx[i],mz[i]]: hmap[mx[i],mz[i]]=gy[i]; mmap[mx[i],mz[i]]=a[xs[i],ys[i],zs[i]]

# 3) TEAL CELLS: top-surface GLASS(9) cluster centroids
gx,gzz=np.nonzero(mmap==9)
cl=collections.Counter(((X//8)*8,(Z//8)*8) for X,Z in zip(gx,gzz))
print(f"TOP-GLASS cells: {len(gx)}; clusters(x,z,n): {sorted(cl.items(), key=lambda t:-t[1])[:12]}")

# 4) FARM ORIENTATION: crop cells (LEAF=10, FLOWER=19) per data axis band
crop=np.isin(mmap,[10,19])
print(f"CROP x<100(WEST): {int(crop[:100,:].sum())}  z<100(SOUTH): {int(crop[:,:100].sum())}")

# 5) CIVIC LEGEND: top material at registry coordinates
t=lambda x,zz:int(mmap[int(x),int(zz)])
print(f"hospital cross(450,550)={t(450,550)} field(455,555)={t(455,555)} | school(650,550)={t(650,550)} | fire(550,450)={t(550,450)} | office(450,450)={t(450,450)} | market(550,650)={t(550,650)}")
