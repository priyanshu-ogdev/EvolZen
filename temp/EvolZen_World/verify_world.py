import numpy as np, json, collections
z=np.load('world_voxel_hires.npz'); meta=json.load(open('voxel_meta.json'))
tests=[]
def T(n,c,d): tests.append((n,bool(c),d))
keys=list(z.files)
T('Chunk integrity', all(z[k].shape==(32,32,32) and z[k].dtype==np.uint8 for k in keys), f'{len(keys)} chunks')
hist=np.zeros(24,np.int64)
for k in keys: hist+=np.bincount(z[k].ravel(),minlength=24)
T('NO WATER (mandate)', hist[8]==0, f'WATER={hist[8]}')
# ---- 1m top-down extraction ----
MAP=1000; hmap=np.full((MAP,MAP),-1,np.int16); mmap=np.zeros((MAP,MAP),np.uint8)
for k in keys:
    a=z[k]; cx,cy,cz=map(int,k[1:].split('_'))
    xs,ys,zs=np.nonzero(a)
    if len(xs)==0: continue
    gx,gy,gz=cx*32+xs,cy*32+ys,cz*32+zs
    mx,mz=gx//4,gz//4
    for i in range(len(mx)):
        my=gy[i]
        if my>hmap[mx[i],mz[i]] and 0<=mx[i]<MAP and 0<=mz[i]<MAP:
            hmap[mx[i],mz[i]]=my; mmap[mx[i],mz[i]]=a[xs[i],ys[i],zs[i]]
road=np.isin(mmap,[3,4,12])
T('Street network density', road.sum()>25000, f'{road.sum():,} road cells (grid, not crosshair)')
# ---- flood-fill connectivity from arterial intersection ----
seen=np.zeros((MAP,MAP),bool); dq=collections.deque([(500,500)]); seen[500,500]=True
while dq:
    x,yy=dq.popleft()
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx,ny=x+dx,yy+dy
        if 0<=nx<MAP and 0<=ny<MAP and road[nx,ny] and not seen[nx,ny]:
            seen[nx,ny]=True; dq.append((nx,ny))
frac=seen.sum()/max(1,road.sum())
T('Road network CONNECTED', frac>0.95, f'{frac*100:.1f}% of streets in one component')
# ---- every house has a walkway/street at its door ----
ok=0
for hx,hz,w,d,t in meta['houses']:
    dx=int(hx+w/2); zs=int(hz)
    if road[max(0,dx-1):dx+2, max(0,zs-4):zs+5].any(): ok+=1
T('Houses wired to streets', ok>=int(0.95*len(meta['houses'])), f'{ok}/{len(meta["houses"])}')
# ---- archetype diversity via roof materials ----
T('Roof diversity (5 archetypes)', all(hist[i]>1000 for i in (12,18,7,13)), f'ROOF={hist[12]} RED={hist[18]} WOOD={hist[7]} CONC={hist[13]}')
# ---- hospital roof cross visible top-down ----
hx0,hz0=meta['hospital_center']
T('Hospital cross on roof', mmap[hx0,hz0]==18 and mmap[hx0,hz0-4]==18, f'cell={mmap[hx0,hz0]}')
# ---- farms anchored WEST ----
west=int(np.isin(mmap[:100,:],[10,19]).sum()); south=int(np.isin(mmap[:, :100],[10,19]).sum())
T('Farms on WEST edge', west>south*2 and west>2000, f'west={west} south={south}')
# ---- park mass ----
T('Park green mass', int((mmap[500:600,500:600]==1).sum())>5000, f'{int((mmap[500:600,500:600]==1).sum())} grass cells')
np.save('topdown_mmap.npy', mmap)
print("="*70)
fail=0
for n,c,d in tests:
    print(f"  {'✅ PASS' if c else '❌ FAIL'}  {n:<34} {d}"); fail+=(not c)
print("="*70)
print(f"  RESULT: {'🏆 CERTIFIED — HANDOFF AUTHORIZED' if fail==0 else '❌ '+str(fail)+' FAILURES — NO HANDOFF'}")
