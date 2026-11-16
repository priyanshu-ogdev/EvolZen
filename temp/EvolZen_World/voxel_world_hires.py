import numpy as np, json, time

V=0.25; C=32
WX,WY,WZ=4000,160,4000

class M:
    AIR,GRASS,DIRT,PATH,WALK,BRICK,VINYL,WOOD,WATER,GLASS,LEAF,TRUNK,\
    ROOF,CONC,METAL,LAMP,FAB,WHITE,RED,FLOWER,SAND,CAR,TIRE,TV = range(24)

chunks={}; HOUSE_COUNTS={i:0 for i in range(5)}; HOUSE_REG=[]; FARMS=0; GREENHOUSES=0

def _fill_v(ix0,iy0,iz0,ix1,iy1,iz1,mat):
    ix0=max(0,ix0); iy0=max(0,iy0); iz0=max(0,iz0)
    ix1=min(WX,ix1); iy1=min(WY,iy1); iz1=min(WZ,iz1)
    if ix1<=ix0 or iy1<=iy0 or iz1<=iz0: return
    for cx in range(ix0//C,(ix1-1)//C+1):
        lx0,lx1=max(ix0,cx*C),min(ix1,(cx+1)*C)
        for cy in range(iy0//C,(iy1-1)//C+1):
            ly0,ly1=max(iy0,cy*C),min(iy1,(cy+1)*C)
            for cz in range(iz0//C,(iz1-1)//C+1):
                lz0,lz1=max(iz0,cz*C),min(iz1,(cz+1)*C)
                k=(cx,cy,cz); a=chunks.get(k)
                if a is None: a=np.zeros((C,C,C),np.uint8); chunks[k]=a
                a[lx0-cx*C:lx1-cx*C,ly0-cy*C:ly1-cy*C,lz0-cz*C:lz1-cz*C]=mat

def box(x0,y0,z0,x1,y1,z1,mat):
    _fill_v(int(x0//V),int(y0//V),int(z0//V),-int(-x1//V),-int(-y1//V),-int(-z1//V),mat)

def sbox(x0,y0,z0,x1,y1,z1,mat):
    box(min(x0,x1),y0,min(z0,z1),max(x0,x1),y1,max(z0,z1),mat)

def sphere(cx,cy,cz,r,mat):
    ix0,iy0,iz0=int((cx-r)//V),int((cy-r)//V),int((cz-r)//V)
    ix1,iy1,iz1=int((cx+r)//V)+1,int((cy+r)//V)+1,int((cz+r)//V)+1
    for cxx in range(max(0,ix0)//C,min(WX,ix1)//C+1):
        for cyy in range(max(0,iy0)//C,min(WY,iy1)//C+1):
            for czz in range(max(0,iz0)//C,min(WZ,iz1)//C+1):
                lx0,lx1=max(ix0,cxx*C),min(ix1,(cxx+1)*C)
                ly0,ly1=max(iy0,cyy*C),min(iy1,(cyy+1)*C)
                lz0,lz1=max(iz0,czz*C),min(iz1,(czz+1)*C)
                if lx1<=lx0 or ly1<=ly0 or lz1<=lz0: continue
                gx=np.arange(lx0,lx1)[:,None,None]*V+V/2
                gy=np.arange(ly0,ly1)[:,None]*V+V/2
                gz=np.arange(lz0,lz1)[None,None,:]*V+V/2
                mask=(gx-cx)**2+(gy-cy)**2+(gz-cz)**2<=r*r
                k=(cxx,cyy,czz); a=chunks.get(k)
                if a is None: a=np.zeros((C,C,C),np.uint8); chunks[k]=a
                a[lx0-cxx*C:lx1-cxx*C,ly0-cyy*C:ly1-cyy*C,lz0-czz*C:lz1-czz*C][mask]=mat

def gable_roof(x,z,w,d,y0,mat,step=0.5,over=0.5):
    s=-over
    while (w-2*s)>1.0 and (d-2*s)>1.0 and (y0+s+over)<38:
        box(x+s,y0+s+over,z+s,x+w-s,y0+s+over+step,z+d-s,mat); s+=step

def flat_roof(x,z,w,d,y0,mat):
    box(x-0.25,y0,z-0.25,x+w+0.25,y0+0.25,z+d+0.25,mat)
    box(x-0.25,y0+0.25,z-0.25,x+w+0.25,y0+1.0,z,mat)
    box(x-0.25,y0+0.25,z+d,x+w+0.25,y0+1.0,z+d+0.25,mat)
    box(x-0.25,y0+0.25,z,x,y0+1.0,z+d,mat)
    box(x+w,y0+0.25,z,x+w+0.25,y0+1.0,z+d,mat)

def windows(x,z,w,d,floors,shutter=None):
    for f in range(floors):
        wy=1.2+f*3.0
        for wx0 in np.arange(1.5,max(2.0,w-2.0),3.0):
            box(x+wx0,wy,z-0.01,x+wx0+1.5,wy+1.25,z+0.51,M.AIR)
            box(x+wx0+0.25,wy+0.25,z+0.1,x+wx0+1.25,wy+1.0,z+0.4,M.GLASS)
            box(x+wx0,wy,z+d-0.51,x+wx0+1.5,wy+1.25,z+d+0.01,M.AIR)
            box(x+wx0+0.25,wy+0.25,z+d-0.4,x+wx0+1.25,wy+1.0,z+d-0.1,M.GLASS)
            if shutter:
                box(x+wx0-0.25,wy,z+0.1,x+wx0,wy+1.25,z+0.35,shutter)
                box(x+wx0+1.5,wy,z+0.1,x+wx0+1.75,wy+1.25,z+0.35,shutter)

def furnish(x,z,w,d,fl):
    y=0.25
    box(x+1,y,z+1,x+1.8,2.0,z+1.8,M.WHITE)
    box(x+w-2,y,z+1,x+w-1.2,1.1,z+1.8,M.METAL)
    box(x+w/2-1,y,z+4,x+w/2+1,1.0,z+5,M.WOOD)
    box(x+w/2-1.6,y,z+4.2,x+w/2-1.1,0.7,z+4.8,M.WOOD)
    box(x+w/2+1.1,y,z+4.2,x+w/2+1.6,0.7,z+4.8,M.WOOD)
    box(x+1,y,z+d-3,x+3.5,1.0,z+d-2,M.FAB); box(x+1,1.0,z+d-2.3,x+3.5,1.6,z+d-2,M.FAB)
    box(x+w-3,y,z+d-2,x+w-2,0.8,z+d-1,M.WOOD); box(x+w-2.9,0.8,z+d-1.9,x+w-2.1,1.5,z+d-1.1,M.TV)
    yb=3.25 if fl==2 else 0.25
    box(x+w-4,yb,z+2,x+w-1.5,yb+0.5,z+5,M.WOOD)
    box(x+w-4,yb+0.5,z+2,x+w-1.5,yb+0.85,z+5,M.FAB)
    box(x+w-4,yb+0.85,z+2,x+w-1.5,yb+1.1,z+2.7,M.WHITE)
    box(x+1,yb,z+d-3,x+2,yb+2.0,z+d-1,M.WOOD)

# House archetypes: (w,d,floors,wall,ROOF-MATERIAL,roof_step) — roof color encodes type top-down
SPECS={0:(14,10,1,M.VINYL,M.ROOF,1.0), 1:(12,14,2,M.BRICK,M.RED,0.5),
       2:(16,18,2,M.VINYL,M.ROOF,0.5), 3:(8,10,1,M.WOOD,M.WOOD,0.25),
       4:(12,14,2,M.WHITE,M.CONC,0.5)}
def house(x,z,rng,force=None):
    t=force if force is not None else int(rng.integers(0,5))
    w,d,fl,wall,roofm,step=SPECS[t]; h=fl*3.0
    box(x,0,z,x+w,0.25,z+d,M.CONC)
    box(x,0.25,z,x+0.5,h,z+d,wall); box(x+w-0.5,0.25,z,x+w,h,z+d,wall)
    box(x,0.25,z,x+w,h,z+0.5,wall); box(x,0.25,z+d-0.5,x+w,h,z+d,wall)
    if t==4: box(x+1,0.25,z+0.1,x+w-1,2.8,z+0.4,M.GLASS)
    if fl==2: box(x,3.0,z,x+w,3.25,z+d,M.WOOD)
    box(x+w/2-0.5,0.25,z-0.01,x+w/2+0.5,2.3,z+0.51,M.AIR)
    box(x+w/2-0.4,0.25,z+0.1,x+w/2+0.4,2.2,z+0.35,M.WOOD)
    box(x+w/2+0.3,1.0,z+0.05,x+w/2+0.45,1.15,z+0.1,M.METAL)
    windows(x,z,w,d,fl,M.WOOD if t==1 else None)
    if t==4: flat_roof(x,z,w,d,h,wall)
    else: gable_roof(x,z,w,d,h,roofm,step,0.5)
    if t==2:
        box(x+w,0.25,z+4,x+w+6,3.0,z+12,wall)
        gable_roof(x+w,z+4,6,8,3.0,roofm,0.5,0.25)
    if t in (1,2): box(x+w-2,h,z+d-2,x+w-1,h+2.5,z+d-1,M.BRICK)
    if fl==2:
        for i in range(12):
            box(x+0.6,3.25+i*0.25,z+1+i*0.25,x+1.6,3.5+i*0.25,z+1.5+i*0.25,M.WOOD)
    furnish(x,z,w,d,fl)
    HOUSE_COUNTS[t]+=1; HOUSE_REG.append([round(x,1),round(z,1),w,d,t])
    return t

def tree(x,z,rng):
    th=rng.uniform(2,3.5)
    box(x,0,z,x+0.5,th,z+0.5,M.TRUNK)
    sphere(x+0.25,th+1.0,z+0.25,rng.uniform(1.4,2.0),M.LEAF)

def lamp(x,z):
    box(x,0,z,x+0.25,4,z+0.25,M.METAL); box(x-0.25,4,z-0.25,x+0.5,4.5,z+0.5,M.LAMP)

def greenhouse(x,z):
    global GREENHOUSES; GREENHOUSES+=1
    w,d,hh=6,8,3
    box(x,0,z,x+w,0.25,z+d,M.CONC)
    box(x,0.25,z,x+0.25,hh,z+d,M.GLASS); box(x+w-0.25,0.25,z,x+w,hh,z+d,M.GLASS)
    box(x,0.25,z,x+w,hh,z+0.25,M.GLASS); box(x,0.25,z+d-0.25,x+w,hh,z+d,M.GLASS)
    box(x+2,0.25,z-0.01,x+4,2.0,z+0.25,M.AIR)
    gable_roof(x,z,w,d,hh,M.GLASS,0.5,0.25)
    for i in range(3):
        box(x+1+i*1.75,0.25,z+2,x+1.5+i*1.75,0.7,z+d-2,M.FLOWER)

def civic(x,z,w,d,floors,mat,kind):
    h=floors*3.5
    box(x,0,z,x+w,0.25,z+d,M.CONC)
    box(x,0.25,z,x+0.5,h,z+d,mat); box(x+w-0.5,0.25,z,x+w,h,z+d,mat)
    box(x,0.25,z,x+w,h,z+0.5,mat); box(x,0.25,z+d-0.5,x+w,h,z+d,mat)
    for f in range(floors):
        box(x,0.25+f*3.5,z,x+w,0.5+f*3.5,z+d,M.CONC)
        for wx0 in np.arange(2,w-2,3):
            box(x+wx0,1.2+f*3.5,z-0.01,x+wx0+1.75,2.7+f*3.5,z+0.51,M.AIR)
            box(x+wx0+0.25,1.45+f*3.5,z+0.1,x+wx0+1.5,2.45+f*3.5,z+0.4,M.GLASS)
    box(x+w/2-1.5,0.25,z-0.01,x+w/2+1.5,2.5,z+0.51,M.AIR)
    flat_roof(x,z,w,d,h,mat)

def hospital(cx,cz):
    x,z,w,d,floors=cx-40,cz-30,80,60,3; h=floors*3.5
    civic(x,z,w,d,floors,M.WHITE,"hospital")
    # RED CROSS PAINTED ON THE ROOF — visible in orthographic top-down
    box(cx-1.5,h+0.26,cz-6,cx+1.5,h+0.52,cz+6,M.RED)
    box(cx-6,h+0.26,cz-1.5,cx+6,h+0.52,cz+1.5,M.RED)

def market(cx,cz):
    for i in range(4):
        sx=cx-30+i*16
        box(sx,0,cz-5,sx+0.25,2,cz-4.75,M.WOOD); box(sx+3,0,cz-5,sx+3.25,2,cz-4.75,M.WOOD)
        for st in range(6):
            box(sx-0.5+st*0.75,2,cz-5.5,sx-0.5+st*0.75+0.75,2.25,cz-4,M.RED if st%2 else M.WHITE)
        box(sx+0.5,0.75,cz-3,sx+2.75,1,cz-1,M.WOOD)
    box(cx-1.5,2,cz-1.5,cx+1.5,2.5,cz+1.5,M.RED)
    box(cx-1.5,2,cz-1.5,cx-1,2.5,cz-1,M.WHITE)

def park(bx0,bz0,rng):
    box(bx0+2,0,bz0+2,bx0+98,0.25,bz0+98,M.GRASS)
    box(bx0+48,0,bz0+2,bx0+52,0.5,bz0+98,M.WALK)
    box(bx0+2,0,bz0+48,bx0+98,0.5,bz0+52,M.WALK)
    for i in range(40):
        tree(bx0+6+int(rng.integers(0,88)),bz0+6+int(rng.integers(0,88)),rng)
    for i in range(4):
        box(bx0+20+i*16,0.25,bz0+20,bx0+26+i*16,0.6,bz0+30,M.FLOWER if i%2 else M.LEAF)
    greenhouse(bx0+70,bz0+70)
    box(bx0+45,0.5,bz0+45,bx0+55,3,bz0+55,M.WOOD)
    box(bx0+44,3,bz0+44,bx0+56,3.5,bz0+56,M.ROOF)

def farm(bx0,bz0,rng):
    global FARMS; FARMS+=1
    for i in range(8):   # vertical crop rows (WEST edge orientation)
        rx=bx0+15+i*3
        box(rx,0,bz0+15,rx+1,0.3,bz0+85,M.DIRT)
        box(rx+0.25,0.3,bz0+15,rx+0.75,0.8,bz0+85,M.LEAF if i%2 else M.FLOWER)
    box(bx0+13,0.8,bz0+13,bx0+13.25,1.0,bz0+87,M.WOOD)
    box(bx0+40,0.8,bz0+13,bx0+40.25,1.0,bz0+87,M.WOOD)
    if bz0==400:
        box(bx0+55,0,bz0+20,bx0+73,5,bz0+32,M.RED)
        gable_roof(bx0+55,bz0+20,18,12,5,M.WOOD,0.5,0.5)
        box(bx0+78,0,bz0+22,bx0+82,10,bz0+26,M.METAL)
    else:
        greenhouse(bx0+60,bz0+60)
        house(bx0+55,bz0+20,rng,force=1)
        sbox(bx0+61-0.5,0,bz0+20, bx0+61+0.5,0.3,bz0+2,M.WALK)

def suburb_block(bx0,bz0,rng):
    box(bx0+48,0,bz0+2,bx0+52,0.25,bz0+98,M.PATH)   # residential lanes
    box(bx0+2,0,bz0+48,bx0+98,0.25,bz0+52,M.PATH)
    for (hx,hz) in [(bx0+14,bz0+14),(bx0+60,bz0+14),(bx0+14,bz0+60),(bx0+60,bz0+60)]:
        w,d,_,_,_,_=SPECS[int(rng.integers(0,5))] if False else (0,0,0,0,0,0)
        t=house(hx,hz,rng)
        sw,_,_,_,_,_=SPECS[t]
        target_z = bz0+2 if hz == bz0+14 else bz0+52
        sbox(hx+sw/2-0.5,0,hz, hx+sw/2+0.5,0.3,target_z,M.WALK)  # walkway goes North to nearest street

def build_roads():
    box(496,0,0,504,0.25,1000,M.PATH); box(0,0,496,1000,0.25,504,M.PATH)
    box(494,0,0,496,0.5,1000,M.WALK); box(504,0,0,506,0.5,1000,M.WALK)
    box(0,0,494,1000,0.5,496,M.WALK); box(0,0,504,1000,0.5,506,M.WALK)
    for b in range(100,1000,100):
        if abs(b-500)>10:
            box(b-2,0,0,b+2,0.25,1000,M.PATH); box(0,0,b-2,1000,0.25,b+2,M.PATH)
    for p in range(0,1000,20):
        lamp(493.5,p); lamp(506,p); lamp(p,493.5); lamp(p,506)

def build_city():
    rng=np.random.default_rng(42)
    build_roads()
    for bx in range(10):
        for bz in range(10):
            bx0,bz0=bx*100,bz*100; cx,cz=bx0+50,bz0+50
            dist=np.hypot(cx-500,cz-500)
            if bx==0: farm(bx0,bz0,rng)
            elif (bx,bz)==(5,5): park(bx0,bz0,rng)
            elif (bx,bz)==(4,5): hospital(cx,cz)
            elif (bx,bz)==(6,5): civic(cx-30,cz-20,60,40,2,M.BRICK,"school")
            elif (bx,bz)==(5,4): civic(cx-20,cz-15,40,30,1,M.RED,"fire")
            elif (bx,bz)==(5,6): market(cx,cz)
            elif dist<150: civic(cx-20,cz-20,40,40,4,M.VINYL,"office")
            else: suburb_block(bx0,bz0,rng)
    for p in range(10,1000,25):
        tree(490+rng.uniform(-1,1),p+rng.uniform(-2,2),rng)
        tree(508+rng.uniform(-1,1),p+rng.uniform(-2,2),rng)

if __name__=="__main__":
    t0=time.time()
    build_city()
    solid=sum(int(np.count_nonzero(a)) for a in chunks.values())
    hist=np.zeros(24,dtype=np.int64)
    for a in chunks.values(): hist+=np.bincount(a.ravel(),minlength=24)
    print(f"Chunks:{len(chunks):,} Solid:{solid:,} ({time.time()-t0:.1f}s)")
    print(f"Houses:{HOUSE_COUNTS} Farms:{FARMS} Greenhouses:{GREENHOUSES}")
    print(f"WATER voxels: {hist[8]}  (MUST BE 0)")
    np.savez_compressed("world_voxel_hires.npz", **{f"c{c[0]}_{c[1]}_{c[2]}":a for c,a in chunks.items()})
    json.dump({"voxel":V,"chunk":C,"house_counts":HOUSE_COUNTS,"farms":FARMS,
               "greenhouses":GREENHOUSES,"houses":HOUSE_REG,"hospital_center":[450,550]},
              open("voxel_meta.json","w"))
    print("Saved.")
