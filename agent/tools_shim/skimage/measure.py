"""Marching tetrahedra stand-in for skimage.measure.marching_cubes (numpy only). Watertight by construction."""
import numpy as np
TETS = [(0,5,1,6),(0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6)]
OFF = np.array([(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)])
def marching_cubes(vol, level=0.0, spacing=(1,1,1), **kw):
    nx,ny,nz = vol.shape
    inside = vol < level
    c = np.zeros((nx-1,ny-1,nz-1), np.int8)
    for o in OFF: c += inside[o[0]:nx-1+o[0], o[1]:ny-1+o[1], o[2]:nz-1+o[2]]
    idx = np.argwhere((c>0)&(c<8))
    ids = np.arange(vol.size).reshape(vol.shape)
    flat = vol.ravel()
    cor = idx[:,None,:] + OFF[None]             # (n,8,3)
    cid = ids[cor[...,0],cor[...,1],cor[...,2]] # (n,8)
    cval = flat[cid]
    cpos = cor.astype(np.float64)
    tris = []   # arrays of (m,3) of edge keys as (ida,idb) pairs, plus orientation reference
    ek_a=[];ek_b=[]
    for t in TETS:
        ti = cid[:,t]; tv = cval[:,t]; tp = cpos[:,t]
        ins = tv < level
        n = ins.sum(1)
        for case in (1,2,3):
            sel = np.nonzero(n==case)[0]
            if not len(sel): continue
            I = ins[sel]; ID = ti[sel]; P = tp[sel]
            if case in (1,3):
                lone = I if case==1 else ~I
                a = np.argmax(lone,1)             # the odd corner
                others = np.stack([[j for j in range(4) if j!=k] for k in a])
                r = np.arange(len(sel))
                A = ID[r,a]; Bs = ID[r[:,None],others]  # (m,3)
                tri = [(A,Bs[:,k]) for k in range(3)]
                tri_edges = tri
                ina = (case==1)
                # orientation reference: odd corner vs others centroid
                pa = P[r,a]; po = P[r[:,None],others].mean(1)
                ref = (po-pa) if ina else (pa-po)   # points inside->outside
                tris.append((tri_edges,ref))
            else:
                ii = np.argsort(~I,1,kind='stable')  # inside first
                r = np.arange(len(sel))
                i0,i1,o0,o1 = [ii[:,k] for k in range(4)]
                g=lambda k: ID[r,k]
                # quad edges: (i0,o0),(i0,o1),(i1,o1),(i1,o0)
                e = [(g(i0),g(o0)),(g(i0),g(o1)),(g(i1),g(o1)),(g(i1),g(o0))]
                ref = P[r][np.arange(len(sel))[:,None],np.stack([o0,o1],1)].mean(1) - P[r[:,None],np.stack([i0,i1],1)].mean(1)
                tris.append(([e[0],e[1],e[2]],ref)); tris.append(([e[0],e[2],e[3]],ref))
    # collect
    A=[];B=[];REF=[]
    for edges,ref in tris:
        A.append(np.stack([x[0] for x in edges],1)); B.append(np.stack([x[1] for x in edges],1)); REF.append(ref)
    A=np.concatenate(A);B=np.concatenate(B);REF=np.concatenate(REF)
    lo=np.minimum(A,B);hi=np.maximum(A,B)
    key=lo.astype(np.int64)*vol.size+hi
    uk,inv=np.unique(key.ravel(),return_inverse=True)
    ulo=uk//vol.size; uhi=uk%vol.size
    def coords(i): return np.stack(np.unravel_index(i,vol.shape),1).astype(np.float64)
    va=flat[ulo].astype(np.float64); vb=flat[uhi].astype(np.float64)
    t=(level-va)/np.where(np.abs(vb-va)<1e-12,1e-12,vb-va)
    t=np.clip(t,0.0,1.0)
    V=coords(ulo)+(coords(uhi)-coords(ulo))*t[:,None]
    F=inv.reshape(-1,3)
    # orient
    p=V[F]; nrm=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
    flip=(nrm*REF).sum(1)<0
    F[flip]=F[flip][:,::-1]
    # drop degenerate (collapsed) faces
    ok=(F[:,0]!=F[:,1])&(F[:,1]!=F[:,2])&(F[:,0]!=F[:,2])
    F=F[ok]
    V=V*np.asarray(spacing,float)
    return V.astype(np.float32),F.astype(np.int64),None,None
